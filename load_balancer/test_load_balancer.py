from load_balancer.load_balancer import LoadBalancer

# -------------------------------
# Mock DB engines for testing
# -------------------------------
class MockEngine:
    def __init__(self, name):
        self.name = name

    def execute(self, query):
        print(f"[{self.name}] Executing: {query}")

# -------------------------------
# Setup LoadBalancer
# -------------------------------
lb = LoadBalancer()

# Add nodes with weights
lb.add_node("db1", MockEngine("db1"), weight=3)
lb.add_node("db2", MockEngine("db2"), weight=1)
lb.add_node("db3", MockEngine("db3"), weight=1)
lb.add_node("db4", MockEngine("db4"), weight=2)

print("\n--- Testing SELECT queries (weighted round-robin) ---")
# Send multiple SELECT queries to test weighted round-robin
for i in range(16):
    engine = lb.route_select("SELECT * FROM users")

print("\n--- Testing DML queries (INSERT) ---")
# Send an INSERT query - should go to all enabled nodes
dml_engines = lb.route_dml("INSERT INTO users VALUES (1, 'Alice')")
for eng in dml_engines:
    eng.execute("INSERT INTO users VALUES (1, 'Alice')")


print("\n--- Disabling db1 ---")
lb.disable_node("db1")
for i in range(8):
    engine = lb.route_select("SELECT * FROM users")

dml_engines = lb.route_dml("INSERT INTO users VALUES (1, 'Alice')")
for eng in dml_engines:
    eng.execute("INSERT INTO users VALUES (1, 'Alice')")

print("\n--- Enabling db1 ---")
lb.enable_node("db1")
for i in range(8):
    engine = lb.route_select("SELECT * FROM users")

dml_engines = lb.route_dml("INSERT INTO users VALUES (1, 'Alice')")
for eng in dml_engines:
    eng.execute("INSERT INTO users VALUES (1, 'Alice')")