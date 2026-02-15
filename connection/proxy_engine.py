from typing import Any, Dict, List
from sqlalchemy.sql import ClauseElement
from sqlalchemy.engine import Engine
from load_balancer.load_balancer import LoadBalancer, NoAvailableNodesError
from interceptor.query_parser import SQLTypeParser
from sqlalchemy.exc import OperationalError

import time


class SimpleResult:
    """
    Minimal result-like object that provides:
    - fetchall() -> list[dict]
    - first()
    - iterable
    This is compatible with how demo endpoints read results.
    """
    def __init__(self, rows: List[Dict[str, Any]], meta: Dict[str, Any] | None = None):
        self._rows = rows or []
        self.meta = meta or {}

    def fetchall(self):
        return self._rows

    def first(self):
        return self._rows[0] if self._rows else None

    def __iter__(self):
        return iter(self._rows)

    def to_list(self):
        return self._rows


class ProxyTxConnection:
    """
    Proxy object returned by FrontendProxyEngine.begin().__enter__().
    It executes statements inside transactions on all provided real backend connections.
    """
    def __init__(self, real_conns: List[Any], command_logs: dict, parser: SQLTypeParser):
        # real_conns is a list of tuples (Connection, node_name)
        self._conns = real_conns
        self._command_logs = command_logs
        self._parser = parser

    def execute(self, clauseelement: ClauseElement, *multiparams, **params):
        command = params.pop("_command_obj", None)

        first_rows = None
        for i, (conn, node_name) in enumerate(self._conns):
            try:
                res = conn.execute(clauseelement, *multiparams, **params)
            except OperationalError as e:
                if node_name and node_name in self._command_logs:
                    print(f"[ProxyTxConnection] OperationalError on {node_name}, storing command")
                    try:
                        if command is not None:
                            self._command_logs[node_name].add(command)
                    except Exception:
                        pass
                else:
                    print(f"[ProxyTxConnection] Error executing on connection {i}: {str(e)}")
                res = None
            except Exception as e:
                print(f"[ProxyTxConnection] Error executing on connection {i}: {str(e)}")
                res = None
            # try to fetch rows if any
            try:
                # prefer mappings() to get consistent dict-like rows
                try:
                    rows = [dict(r) for r in res.mappings().all()]
                except Exception:
                    fetched = res.fetchall()
                    rows = [dict(r) for r in fetched]
            except Exception:
                rows = []
            if i == 0:
                first_rows = rows
        return SimpleResult(first_rows or [])

    def close(self):
        for conn, _ in self._conns:
            try:
                conn.close()
            except Exception:
                pass


class ProxyTransaction:
    """
    Context manager for transactional broadcast: opens a transaction on each backend engine,
    and commits/rolls back them together.
    """
    def __init__(self, engines: List[Engine], lb: LoadBalancer, command_logs: dict, parser: SQLTypeParser):
        self._engines = engines
        self._lb = lb
        self._command_logs = command_logs
        self._parser = parser
        self._pairs = []  # list of tuples (conn, trans, node_name)

    def __enter__(self):
        self._pairs = []
        for engine in self._engines:
            conn = engine.connect()
            trans = conn.begin()
            # try to resolve node name for this engine
            node = next((n for n in self._lb._nodes.values() if n.engine == engine), None)
            node_name = node.name if node is not None else None
            self._pairs.append((conn, trans, node_name))
        # return ProxyTxConnection that will execute against all opened connections
        return ProxyTxConnection([(c, name) for c, t, name in self._pairs], self._command_logs, self._parser)

    def __exit__(self, exc_type, exc, tb):
        if exc_type is None:
            # commit all
            for conn, trans, _ in self._pairs:
                try:
                    trans.commit()
                except Exception:
                    try:
                        trans.rollback()
                    except Exception:
                        pass
                finally:
                    try:
                        conn.close()
                    except Exception:
                        pass
        else:
            # rollback all
            for conn, trans, _ in self._pairs:
                try:
                    trans.rollback()
                except Exception:
                    pass
                finally:
                    try:
                        conn.close()
                    except Exception:
                        pass
        return False  # do not suppress exceptions


class ProxyConnection:
    """
    Lightweight connection-like object returned by FrontendProxyEngine.connect().
    Handling:
      - SELECT -> route_select -> execute on single backend -> return SimpleResult(rows)
      - DML -> route_dml -> execute on each enabled backend (in separate transactions via begin() if needed)
      - other -> attempt to run on first enabled node
    """
    def __init__(self, lb: LoadBalancer, parser: SQLTypeParser, command_logs: dict):
        self._lb = lb
        self._parser = parser
        self._command_logs = command_logs

    def execute(self, clauseelement: ClauseElement, *multiparams, **params):
        sql = str(clauseelement)
        qtype = self._parser.get_type(sql)

        if qtype == "SELECT":
            target_engine = self._lb.route_select(sql)
            start = time.perf_counter()
            try:
                with target_engine.connect() as conn:
                    try:
                        res = conn.execute(clauseelement, *multiparams, **params)
                    except Exception as first_exc:
                        # Attempt to run SELECT on other enabled nodes in case chosen node failed
                        nodes = list(self._lb._nodes.values())
                        tried = set()
                        # find the node corresponding to target_engine and mark tried
                        for n in nodes:
                            if n.engine == target_engine:
                                tried.add(n.name)
                                break

                        res = None
                        for n in nodes:
                            if n.name in tried or not n.enabled:
                                continue
                            try:
                                with n.engine.connect() as alt_conn:
                                    res = alt_conn.execute(clauseelement, *multiparams, **params)
                                    target_engine = n.engine
                                    print(f"[ProxyConnection] Retried SELECT on {n.name}")
                                    break
                            except Exception:
                                continue
                        if res is None:
                            # re-raise original exception if all retries failed
                            raise first_exc
                    try:
                        rows = [dict(r) for r in res.mappings().all()]
                    except Exception:
                        try:
                            rows = [dict(r) for r in res.fetchall()]
                        except Exception:
                            rows = []
                elapsed = time.perf_counter() - start
                node = next((n for n in self._lb._nodes.values() if n.engine == target_engine), None)
                if node:
                    node.record_execution(elapsed)
                # attach minimal metadata: only the node name that served the SELECT
                try:
                    meta = node.name if node is not None else None
                except Exception:
                    meta = getattr(node, 'name', None)
                return SimpleResult(rows, meta=meta)
            except OperationalError:
                raise NoAvailableNodesError("RETRY")
            
        if qtype == "DML":
            enabled_engines = self._lb.route_dml(sql)
            disabled_nodes = self._lb.get_disabled_nodes()
            # extract optional command object passed by caller (API)
            command = params.pop("_command_obj", None)

            first_rows = None

            # wykonanie na zdrowych 
            for i, engine in enumerate(enabled_engines):
                with engine.begin() as conn:
                    res = conn.execute(clauseelement, *multiparams, **params)
                    if i == 0:
                        try:
                            first_rows = [dict(r) for r in res.mappings().all()]
                        except Exception:
                            first_rows = []

            for node in disabled_nodes:
                if command is not None:
                    print(f"[CommandLog] {node.name} DOWN → storing command")
                    try:
                        self._command_logs[node.name].add(command)
                    except Exception:
                        pass

            return SimpleResult(first_rows or [])

        # fallback: run on first enabled engine
        enabled = self._lb.route_dml(sql)
        if enabled:
            with enabled[0].connect() as conn:
                res = conn.execute(clauseelement, *multiparams, **params)
                try:
                    rows = [dict(r) for r in res.mappings().all()]
                except Exception:
                    try:
                        rows = [dict(r) for r in res.fetchall()]
                    except Exception:
                        rows = []
            return SimpleResult(rows)

        return SimpleResult([])

    # allow `with frontend_engine.connect() as conn: ...`
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class FrontendProxyEngine:
    """
    Engine-like proxy object used by the application as the "frontend engine".
    It exposes minimal engine API: connect() and begin().
    Internally routes queries using the provided LoadBalancer.
    """
    def __init__(self, load_balancer: LoadBalancer, command_logs: dict):
        self.lb = load_balancer
        self.parser = SQLTypeParser()
        self.command_logs = command_logs

    def connect(self):
        return ProxyConnection(self.lb, self.parser, self.command_logs)

    def begin(self):
        # get engines for broadcast (all enabled nodes)
        engines = self.lb.route_dml("BEGIN")
        return ProxyTransaction(engines, self.lb, self.command_logs, self.parser)
