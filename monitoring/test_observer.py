# to run type into VSC terminal: python -m monitoring.test_observer

from sqlalchemy import create_engine, text
from monitoring.observer import Observer
from monitoring.health_checker import HealthChecker
import urllib


class PrintObserver(Observer):
    def update(self, event: dict):
        print(f"[Observer] Database {event['db']} changed to {event['status']}")

params = urllib.parse.quote_plus(
    "DRIVER={ODBC Driver 17 for SQL Server};"
    "SERVER=your_server,your_port;"
    "DATABASE=master;"
    "Trusted_Connection=yes;"
)

real_engine = create_engine(f"mssql+pyodbc:///?odbc_connect={params}")

fake_engine = create_engine(
    "mysql+pymysql://root:password@localhost:9999/notexisting"
)

engines = {
    "local_mysql":real_engine,
    "broken_mysql":fake_engine
}
checker = HealthChecker(engines)
checker.add_observer(PrintObserver())
checker.run_check()
