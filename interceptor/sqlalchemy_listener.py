import threading
from sqlalchemy import event
from sqlalchemy.engine import Engine

from load_balancer.load_balancer import LoadBalancer
from interceptor.query_parser import SQLTypeParser

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
    event.listen(engine, "before_execute", self.before_execute)
    event.listen(engine, "before_cursor_execute", self.before_cursor_execute)
    print("[SQLAlchemyListener] Registered SQL load balancer interceptors.")


def before_execute(self, conn, clauseelement, multiparams, params, ):
    """
    Podstawowy hook — decyduje do jakiego węzła kierować zapytanie.
    """

    if getattr(self._local, "in_callback", False):
        return clauseelement, multiparams, params

    sql = str(clauseelement)
    qtype = self.parser.get_type(sql)

    # SELECT — jeden wybrany węzeł
    if qtype == "SELECT":
        engine = self.lb.route_select(sql)
        print(f"[SQLAlchemyListener] Forwarding SELECT to {engine}")

        self._local.in_callback = True
        try:
            return engine.execute(clauseelement, multiparams, params)
        finally:
            self._local.in_callback = False

    # DML — wykonaj na każdym engine
    if qtype == "DML":
        engines = self.lb.route_dml(sql)
        print("[SQLAlchemyListener] Broadcasting DML to all nodes")

        self._local.in_callback = True
        try:
            for engine in engines:
                engine.execute(clauseelement, multiparams, params)
            return None  # nie wykonujemy na głównym engine
        finally:
            self._local.in_callback = False

    # Inne — tutaj pewnie będzie zmiana tego, ale narazie tak zostawie
    return clauseelement, multiparams, params


def before_cursor_execute(self, conn, cursor, statement, parameters, context, executemany, ):
    print(f"[SQLAlchemyListener] Executing SQL: {statement}")
    return statement, parameters
