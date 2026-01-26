class MockEngine:
    def __init__(self, name):
        self.name = name
        self.executed = []

    def execute(self, sql):
        self.executed.append(sql)