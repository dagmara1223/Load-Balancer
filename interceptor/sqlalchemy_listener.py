import threading
from sqlalchemy import event
from sqlalchemy.engine import Engine

from load_balancer.load_balancer import LoadBalancer
from interceptor.query_parser import SQLTypeParser

import time

class SQLAlchemyLoadBalancerListener:
    """
    Listener przechwytujący wszystkie zapytania SQLAlchemy i przekierowujący je
    do odpowiednich węzłów LoadBalancera.
    """
    def __init__(self):
        self.lb = LoadBalancer()
        self.parser = SQLTypeParser()

        # flaga używana do unikania rekurencji eventów SQLAlchemy
        self._local = threading.local()
        self._local.in_callback = False

    def register(self, engine: Engine):
        # retval=True allows the listener to return modified statement/params
        event.listen(engine, "before_execute", self.before_execute, retval=True)
        event.listen(engine, "before_cursor_execute", self.before_cursor_execute)
        print("[SQLAlchemyListener] Registered SQL load balancer interceptors.")

    def _execute_on_engine(self, engine: Engine, clauseelement, multiparams, params):
        start = time.perf_counter()
        try:
            with engine.begin() as conn:
                if multiparams:
                    result = conn.execute(clauseelement, *multiparams)
                else:
                    result = conn.execute(clauseelement, params)
            return result
        finally:
            node = next((n for n in self.lb._nodes.values() if n.engine == engine), None)
            if node:
                elapsed = time.perf_counter() - start
                node.record_execution(elapsed)
                print(f"[NodeInfo] {node.name} executed query in {elapsed:.4f}s")


    def before_execute(self, conn, clauseelement, multiparams, params, ):
        """
        Podstawowy hook — decyduje do jakiego węzła kierować zapytanie.
        Zwraca (clauseelement, multiparams, params) do kontynuacji wykonania na
        oryginalnym engine; dodatkowo wykonuje kopie zapytań na węzłach docelowych.
        """

        if getattr(self._local, "in_callback", False):
            return clauseelement, multiparams, params

        sql = str(clauseelement)
        qtype = self.parser.get_type(sql)

        # SELECT — jeden wybrany węzeł (wykonujemy WYŁĄCZNIE na wybranym backendzie)
        if qtype == "SELECT":
            target_engine = self.lb.route_select(sql)
            print(f"[SQLAlchemyListener] Forwarding SELECT to {target_engine} (proxy-only)")

            self._local.in_callback = True
            try:
                # wykonaj zapytanie na wybranym engine i zwróć jego rezultat,
                # co zapobiegnie wykonaniu zapytania na frontendowym engine
                result = self._execute_on_engine(target_engine, clauseelement, multiparams, params)
                return result
            finally:
                self._local.in_callback = False

        # DML — wykonaj na każdym engine (broadcast), a następnie pozwól głównemu wykonać
        if qtype == "DML":
            engines = self.lb.route_dml(sql)
            print("[SQLAlchemyListener] Broadcasting DML to all nodes (proxy-only)")

            first_result = None
            self._local.in_callback = True
            try:
                for i, engine in enumerate(engines):
                    r = self._execute_on_engine(engine, clauseelement, multiparams, params)
                    if i == 0:
                        first_result = r
            finally:
                self._local.in_callback = False

            # zwróć rezultat pierwszego wykonania jako reprezentatywny wynik
            return first_result

        # Inne — nie modyfikujemy
        return clauseelement, multiparams, params

    def before_cursor_execute(self, conn, cursor, statement, parameters, context, executemany, ):
        print(f"[SQLAlchemyListener] Executing SQL: {statement}")
        return statement, parameters
