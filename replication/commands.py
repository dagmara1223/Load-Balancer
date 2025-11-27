'''
Commands that will be stored like: IUD
'''
from replication.command import Command
from sqlalchemy import text
from sqlalchemy import create_engine

class Insert(Command):
    def __init__(self, table, values: dict):
        self.table = table
        self.values = values

    def serialize(self):
        return {
            "type": "insert",
            "table": self.table,
            "values": self.values
        }

    @staticmethod
    def deserialize(data):
        return Insert(data["table"], data["values"])

    def execute(self, engine):
        if engine is None:
            print("(TEST MODE) Would execute INSERT:")
            print("TABLE:", self.table)
            print("VALUES:", self.values)
            return

        keys = ', '.join(self.values.keys())
        placeholders = ", ".join([f":{k}" for k in self.values.keys()])

        query = text(f"INSERT INTO {self.table} ({keys}) VALUES ({placeholders})")

        with engine.begin() as conn:
            conn.execute(query, self.values)

        print("Executing INSERT:")
        print("TABLE:", self.table)
        print("VALUES:", self.values)

class Update(Command):
    def __init__(self, table, set_values:dict, where: dict):
        self.table = table
        self.set_values = set_values
        self.where = where

    def execute(self, engine):
        set_part = ", ".join([f"{i}=:{i}" for i in self.set_values])
        where_part = " AND ".join([f"{i}=:{i}" for i in self.where])

        query = text(f"UPDATE {self.table} SET {set_part} WHERE {where_part}")
        params = {**self.set_values, **self.where}

        with engine.begin() as conn:
            conn.execute(query, params)
        
    def serialize(self):
        return {
            "type": "update",
            "table": self.table,
            "set": self.set_values,
            "where": self.where
        }

    @staticmethod
    def deserialize(data):
        return Update(data["table"], data["set"], data["where"])
    
class Delete(Command):
    def __init__(self, table, where:dict):
        self.table = table 
        self.where = where 
    
    def execute(self, engine):
        where_part = " AND ".join([f"{i}=:{i}" for i in self.where])
        query = text(f"DELETE FROM {self.table} WHERE {where_part}")
    
        with engine.begin() as conn:
            conn.execute(query, self.where)

    def serialize(self):
              return {
            "type": "delete",
            "table": self.table,
            "where": self.where
        }
    @staticmethod
    def deserialize(data):
        return Delete(data["table"], data["where"])


if __name__ == "__main__":
    engine = create_engine("sqlite:///:memory:")

    with engine.begin() as conn:
        conn.execute(text("CREATE TABLE users (id INT, name TEXT)"))

    insert_cmd = Insert("users", {"id": 5, "name": "anna"})
    insert_cmd.execute(engine)

    #anna -> JOANNA
    update_cmd = Update(
        table="users",
        set_values={"name": "JOANNA"},
        where={"id": 5}
    )
    update_cmd.execute(engine)

    delete_cmd = Delete(
        table="users",
        where={"id": 5}
    )
    delete_cmd.execute(engine)

    with engine.connect() as conn:
        rows = conn.execute(text("SELECT * FROM users")).fetchall()
        print("FINAL ROWS:", rows)


