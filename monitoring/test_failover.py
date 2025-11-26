from monitoring.failover_manager import FailoverManager
from monitoring.health_checker import HealthChecker
from monitoring.observer import Observer
from sqlalchemy import create_engine

# Fake load balancer for testing
class FakeLoadBalancer:
    def disable_node(self, name):
        print(f"[FakeLB] Node {name} DISABLED")

    def enable_node(self, name):
        print(f"[FakeLB] Node {name} ENABLED")

# Test observer (Failover)
lb = FakeLoadBalancer()
failover = FailoverManager(lb)

from sqlalchemy import create_engine

broken = create_engine("mysql+pymysql://root:password@localhost:9999/nope")

working = create_engine("sqlite:///:memory:")

engines = {
    "db_up": working,
    "db_down": broken
}

checker = HealthChecker(engines)
checker.add_observer(failover)

checker.run_check()
