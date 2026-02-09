from typing import Any, Dict, List
from sqlalchemy.sql import ClauseElement
from sqlalchemy.engine import Engine
from load_balancer.load_balancer import LoadBalancer
from interceptor.query_parser import SQLTypeParser

class SimpleResult:
    """
    Minimal result-like object that provides:
    - fetchall() -> list[dict]
    - first()
    - iterable
    This is compatible with how demo endpoints read results.
    """
    def __init__(self, rows: List[Dict[str, Any]]):
        self._rows = rows or []

    def fetchall(self):
        return self._rows

    def first(self):
        return self._rows[0] if self._rows else None

    def __iter__(self):
        return iter(self._rows)


class ProxyTxConnection:
    """
    Proxy object returned by FrontendProxyEngine.begin().__enter__().
    It executes statements inside transactions on all provided real backend connections.
    """
    def __init__(self, real_conns: List[Any]):
        # real_conns is a list of sqlalchemy Connection objects (already in transaction)
        self._conns = real_conns

    def execute(self, clauseelement: ClauseElement, *multiparams, **params):
        first_rows = None
        for i, conn in enumerate(self._conns):
            res = conn.execute(clauseelement, *multiparams, **params)
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
        for conn in self._conns:
            try:
                conn.close()
            except Exception:
                pass


class ProxyTransaction:
    """
    Context manager for transactional broadcast: opens a transaction on each backend engine,
    and commits/rolls back them together.
    """
    def __init__(self, engines: List[Engine]):
        self._engines = engines
        self._pairs = []  # list of tuples (conn, trans)

    def __enter__(self):
        self._pairs = []
        for engine in self._engines:
            conn = engine.connect()
            trans = conn.begin()
            self._pairs.append((conn, trans))
        # return ProxyTxConnection that will execute against all opened connections
        return ProxyTxConnection([c for c, t in self._pairs])

    def __exit__(self, exc_type, exc, tb):
        if exc_type is None:
            # commit all
            for conn, trans in self._pairs:
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
            for conn, trans in self._pairs:
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
            with target_engine.connect() as conn:
                res = conn.execute(clauseelement, *multiparams, **params)
                try:
                    rows = [dict(r) for r in res.mappings().all()]
                except Exception:
                    try:
                        rows = [dict(r) for r in res.fetchall()]
                    except Exception:
                        rows = []
            return SimpleResult(rows)

        if qtype == "DML":
            enabled_engines = self._lb.route_dml(sql)
            disabled_nodes = self._lb.get_disabled_nodes()
            command = self._parser.to_command(sql, params)

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
                print(f"[CommandLog] {node.name} DOWN → storing command")
                self._command_logs[node.name].add(command)

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
        return ProxyConnection(self.lb, self.parser)

    def begin(self):
        # get engines for broadcast (all enabled nodes)
        engines = self.lb.route_dml("BEGIN")
        return ProxyTransaction(engines)
