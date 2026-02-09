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

            # Debug: print types / contents to help diagnose missing replay()
            try:
                print(f"[RecoveryManager][DEBUG] command_logs keys: {list(self.command_logs.keys())}")
                print(f"[RecoveryManager][DEBUG] log for {db}: type={type(log)}, repr={repr(log)}")
                has_replay = hasattr(log, "replay") and callable(getattr(log, "replay", None))
                print(f"[RecoveryManager][DEBUG] has_replay={has_replay}")
                if hasattr(log, "commands"):
                    try:
                        print(f"[RecoveryManager][DEBUG] stored commands count: {len(getattr(log, 'commands'))}")
                    except Exception:
                        print(f"[RecoveryManager][DEBUG] could not read log.commands")
            except Exception as _:
                # best-effort debug printing
                pass

            # If `log` is already a CommandLog instance, call its replay.
            # Otherwise try sensible fallbacks: if it's a path (str) create
            # a CommandLog from that file; if it's a serialized list/dict,
            # deserialize into a temporary CommandLog and replay.
            try:
                # lazy import to avoid circular imports in some contexts
                from replication.command_log import CommandLog

                if hasattr(log, "replay") and callable(getattr(log, "replay")):
                    log.replay(engine)
                elif isinstance(log, str):
                    # treat as path
                    tmp = CommandLog(log)
                    tmp.replay(engine)
                elif isinstance(log, (list, dict)):
                    tmp = CommandLog()
                    # if dict, assume it's a serialized list under some key or single command
                    if isinstance(log, dict) and "commands" in log:
                        data_list = log["commands"]
                    elif isinstance(log, dict):
                        # single command dict -> wrap
                        data_list = [log]
                    else:
                        data_list = log

                    tmp.commands = [tmp.deserialize(cmd) for cmd in data_list]
                    tmp.replay(engine)
                else:
                    print(f"[RecoveryManager] Unsupported command_log type: {type(log)}")
            except Exception as e:
                import traceback
                print(f"[RecoveryManager] Recovery failed for {db}: {e}")
                traceback.print_exc()
                return

            print(f"[Recovery Manager] Recovery finished for {db}")

            # optionally enable node in load balancer
            if self.load_balancer:
                self.load_balancer.enable_node(db)