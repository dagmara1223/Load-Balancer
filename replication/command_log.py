# operations that we have to store since they haven't been executed yet 

import json 
from replication.commands import Insert, Update, Delete 

class CommandLog:
    """
    Stores operations that must be replayed on a database when it comes back UP.
    """
    def __init__(self, path="command_log.json"):
        self.path = path
        self.commands = []

        #loading existing log if file exists
        try:
            with open(self.path, "r") as file:
                data = json.load(file)
                self.commands = [self.deserialize(cmd) for cmd in data]
        except FileNotFoundError:
            self.commands = []
    
    def add(self, command):
        self.commands.append(command)
        self.save()

    def save(self):
        with open(self.path, "w") as file:
            json.dump([cmd.serialize() for cmd in self.commands], file, indent=4)

    def replay(self, engine):
        print("[CommandLog] Replaying operations...")
        for cmd in self.commands:
            cmd.execute(engine)
        
        print("[CommandLog] Replay complete. Clearing log.")
        self.commands = []
        self.save()

    def deserialize(self, data):
        if data["type"] == "insert":
            return Insert.deserialize(data)
        if data["type"] == "update":
            return Update.deserialize(data)
        if data["type"] == "delete":
            return Delete.deserialize(data)
        raise ValueError("Unknown command type")
    
if __name__ == "__main__":
    from sqlalchemy import create_engine, text

    log = CommandLog("test_log.json")

    log.add(Insert("users", {"id": 1, "name": "Alice"}))
    log.add(Update("users", {"name": "ALICJA"}, {"id": 1}))
    log.add(Delete("users", {"id": 1}))

    print("Saved commands:", log.commands)

    engine = create_engine("sqlite:///:memory:")

    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE users (id INT, name TEXT)"))

    log.replay(engine)

    with engine.connect() as conn:
        rows = conn.execute(text("SELECT * FROM users")).fetchall()
        print("ROWS AFTER REPLAY:", rows)
