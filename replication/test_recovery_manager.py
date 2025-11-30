from sqlalchemy import create_engine, text
from replication.commands import Insert, Update, Delete
from replication.command_log import CommandLog
from replication.recovery_manager import RecoveryManager

# 1.creating test engine
engine = create_engine("sqlite:///:memory:")

with engine.begin() as conn:
    conn.execute(text("CREATE TABLE users (id INT, name TEXT)"))

# 2.preparing CommandLog with pending operations
log = CommandLog("test_recovery.json")

log.add(Insert("users", {"id": 1, "name": "Anna"}))
log.add(Update("users", {"name": "ANNA_UPDATED"}, {"id": 1}))
log.add(Delete("users", {"id": 1}))

# 3. attaching log to dictionary since RecoveryManager expects a dict
command_logs = {"db1": log}
engines = {"db1": engine}

# 4. creating recovery manager 
recovery = RecoveryManager(engines, command_logs)
event = {"db": "db1", "status": "UP"}
recovery.update(event)

# 5.checking for final database output 
with engine.connect() as conn:
    rows = conn.execute(text("SELECT * FROM users")).fetchall()
    print("FINAL ROWS:", rows)