### **Singleton Pattern**

The Singleton Pattern is a **creational design pattern** that ensures a class has **only one instance** and provides a **global point of access** to it.
Instead of creating multiple instances, the system ensures that **every module uses the same object** whenever it needs to interact with that class.

**Why Singleton is needed in our project**
In our load-balanced database system, the **LoadBalancer** is the **central component** responsible for routing queries to database nodes.
Having multiple instances could lead to **inconsistent routing decisions, duplicate state, or conflicting node status**.
By using the Singleton Pattern, we guarantee that:

1. Only **one LoadBalancer instance** exists in the entire system.
2. All components (SQL interceptors, RecoveryManager, FailoverManager) interact with the **same centralized LoadBalancer**.
3. Node states, round-robin iterators, and routing logic are **always consistent across modules**.

**How Singleton works in our system**
Step 1 – Any component requests a LoadBalancer instance:

```python
lb = LoadBalancer()
```

Step 2 – The class checks if an instance already exists:

* If yes → returns the existing instance
* If no → creates a new instance and returns it

Step 3 – All subsequent calls return the **same LoadBalancer object**, ensuring shared state for:

* Enabled/disabled nodes
* Weighted round-robin selection
* Routing SELECT and DML queries

**Benefits summarized**

* guarantees a **single source of truth** for query routing
* ensures **consistent node management** across the system
* simplifies **integration with RecoveryManager and HealthChecker**
* prevents accidental creation of multiple LoadBalancers
* improves **stability, reliability, and maintainability**








### **LoadBalancer**

#### 1. Purpose

The **LoadBalancer** is the **core component of the system** responsible for routing SQL queries to the appropriate database nodes.
It ensures that **SELECT queries are sent to one node** (using round-robin or weighted round-robin) and **INSERT/UPDATE/DELETE queries are sent to all enabled nodes**.
The LoadBalancer also manages **node availability**, allowing nodes to be **enabled or disabled** dynamically.
It is implemented as a **Singleton**, guaranteeing that **all components use the same central LoadBalancer instance**.

---

#### 2. How it fits into the system

The LoadBalancer interacts with:

* **SQL interceptor** – receives queries intercepted from SQLAlchemy and decides which nodes will execute them.
* **HealthChecker & RecoveryManager** – node status updates trigger `enable_node` or `disable_node` in the LoadBalancer.
* **CommandLog / Command Pattern** – works with replayed operations to ensure that previously failed DML commands are routed correctly after a node recovery.

The typical workflow is:

1. SQL query is intercepted
2. LoadBalancer routes it according to query type and node status
3. SELECT queries - one node, round-robin
4. DML queries - all enabled nodes
5. Node failures or recoveries update the routing dynamically

---

#### 3. How LoadBalancer works

**1 – Node registration**

* Each database node is registered with `add_node(name, engine, weight)`.
* Each node has an `enabled` flag and a `weight` for weighted round-robin.

**2 – Routing SELECT queries**

* When a SELECT query arrives, the LoadBalancer uses a **weighted round-robin iterator** to pick **one enabled node**.

**3 – Routing DML queries**

* When an INSERT/UPDATE/DELETE query arrives, it is **sent to all enabled nodes** simultaneously.

**4 – Node management**

* `disable_node(name)` marks a node as unavailable (e.g., HealthChecker detects DOWN).
* `enable_node(name)` marks a node as active (e.g., RecoveryManager finishes replay).
* The round-robin iterator is updated automatically whenever node availability changes.

**5 – Weighted round-robin**

* Each node’s weight determines how often it receives SELECT queries.
* Example: `db1: weight=3`, `db2: weight=1` → SELECTs are routed roughly 3:1 to db1 vs db2.

---

#### 4. LoadBalancer Sequence Example

1. Nodes db1, db2, db3 are added to the LoadBalancer with weights 3, 1, 1.
2. Application issues a SELECT query - LoadBalancer routes to db1 (first in round-robin weighted).
3. Application issues an INSERT - LoadBalancer sends to all enabled nodes.
4. HealthChecker detects db2 is DOWN - LoadBalancer disables db2.
5. RecoveryManager finishes replay - calls `enable_node(db2)` - LoadBalancer updates round-robin.
6. Subsequent queries are routed to all currently enabled nodes according to weights.
