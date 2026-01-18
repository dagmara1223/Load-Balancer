import re

class SQLTypeParser:

    DML_COMMANDS = ("insert", "update", "delete")
    DDL_COMMANDS = ("create", "alter", "drop", "rename")
    TX_COMMANDS = ("begin", "commit", "rollback")
    ADMIN_COMMANDS = ("set", "use", "pragma")
    PROC_COMMANDS = ("call", "exec")
    
    def _clean_sql(self, sql: str) -> str:
        """
        Usuwa komentarze SQL i zbędne białe znaki.
        """
        sql = re.sub(r'--.*?$', '', sql, flags=re.MULTILINE)
        sql = re.sub(r'/\*.*?\*/', '', sql, flags=re.DOTALL)
        return sql.strip().lower()

    def get_type(self, sql: str) -> str:
        """
        Zwraca typ zapytania SQL jako string:
        SELECT / DML / DDL / TX / ADMIN / PROCEDURE / MULTI / OTHER
        """
        if not sql or not isinstance(sql, str):
            return "OTHER"

        clean = self._clean_sql(sql)

        if ";" in clean.strip().strip(";"):
            return "MULTI"

        first = clean.split()[0]
        if first == "select":
            return "SELECT"
        if first in self.DML_COMMANDS:
            return "DML"
        if first == "insert" and "on conflict" in clean:
            return "UPSERT"
        if first == "merge":
            return "MERGE"
        if first == "truncate":
            return "DDL"
        if first in self.DDL_COMMANDS:
            return "DDL"
        if first in self.TX_COMMANDS:
            return "TX"
        if first in self.PROC_COMMANDS:
            return "PROCEDURE"
        if first in self.ADMIN_COMMANDS:
            return "ADMIN"

        return "OTHER"

