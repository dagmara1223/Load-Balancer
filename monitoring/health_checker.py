'''
Health Checker is a subject that analyzes the state of our databases - whether their state
is up / down. It pings every database using SELECT 1 and checks if database answered.
If so - the database is up, if not - database is down. Then our new state is being compared
with the old one and if there is a difference, notification is sent to all observers.
Observers react : FailoverManager shuts down the database, RecoveryManager starts creating logs
and LogManager states that the database is still down.
'''

from sqlalchemy.exc import SQLAlchemyError
from .subject import Subject

class HealthChecker(Subject):
    def __init__(self, engines:dict):
        """
        engines = {
            "db1":"engine1",
            "db2":"engine2",
            ...
        }
        """
        super().__init__()
        self.engines = engines
        self.last_status = {name:"UNKNOWN" for name in engines}
    
    def ping(self, engine):
        try:
            with engine.connect() as conn:
                conn.execute("SELECT 1")
            return True
        except SQLAlchemyError:
            return False 
    
    def run_check(self):
        """
        designed to be called every X seconds
        """
        for name, engine in self.engines.items():
            is_up = self.ping(engine)
            if is_up:
                new_status = "UP"
            else:
                new_status = "DOWN"

            if new_status != self.last_status[name]:
                event = {
                    "db":name,
                    "status":new_status
                }
                self.notify(event)
            self.last_status[name] = new_status