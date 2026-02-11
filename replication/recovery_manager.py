'''
RecoveryManager is an Observer that reacts when a database node comes back UP.
Its responsibility is to replay all operations stored in the CommandLog for that
database (Insert, Update, Delete commands). After replaying logs, the database
is synchronized and ready to be enabled back into the LoadBalancer.
'''

from monitoring.observer import Observer


class RecoveryManager(Observer):
    def __init__(self, engines: dict, command_logs: dict, load_balancer=None):
        """
        engines = { "db1": engine_obj, "db2": engine_obj }
        command_logs = { "db1": CommandLog(), "db2": CommandLog() }
        load_balancer is optional (FailoverManager handles DOWN/UP)
        """
        self.engines = engines
        self.command_logs = command_logs
        self.load_balancer = load_balancer

    def update(self, event: dict):
        db = event['db']
        status = event['status']

        if status == "UP":
            print(f"[Recovery Manager] {db} is UP. Starting recovery.")
            log = self.command_logs.get(db)
            engine = self.engines.get(db)

            if log is None:
                print(f"[RecoveryManager] no log found for {db}")
                return
            if engine is None:
                print(F"[RecoveryManager] no engine found for {db}")
                return

            try:
                log.replay(engine)

            except Exception as e:
                import traceback
                print(f"[RecoveryManager] Recovery failed for {db}: {e}")
                traceback.print_exc()
                return

            print(f"[Recovery Manager] Recovery finished for {db}")

            # optionally enable node in load balancer
            if self.load_balancer:
                self.load_balancer.enable_node(db)