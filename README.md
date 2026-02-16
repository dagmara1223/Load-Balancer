# Load-Balancer 
A middleware load balancer for distributed database systems, providing transparent query routing, failover handling, and recovery mechanisms. <br>
The system acts as a single database entry point for applications while managing multiple physical database nodes internally. <br>

## 🔦 Features <br>
- **Load Balancing for database queries** <br>
Read / Write Query detection <br>
Smart routing of SELECT vs INSERT/UPDATE/DELETE <br>
- **Multiple selection strategies** <br>
Round Robin, Weighted Round Robin, Least Response Time <br>
- **Health Monitoring** <br>
Continuous database node checks - time lapse: 5s <br>
Automatic exclusion of unavailable nodes ( in DOWN state ) <br>
- **Failover & recovery** <br>
Automatic failover when a node goes DOWN <br>
Command replay when a node comes back UP <br>
- **Command Logging** <br>
Persistent logging of modifying operations <br>
Replay for consistency after recovery <br>
- **Dockerized Environment** <br>
Easy deployment and reproducible setup <br>
- **Simple demo frontend + API** <br>
Uvicorn-based FastAPI server <br> 
HTTP access on port 8000 <br>

## 🏦 Architecture Overview <br>
The system is structured into three layers: <br>
**1. Presentation Layer** : Demo App (FastAPI + Uvicorn), Issues SQL queries via API <br> 
**2. Business Layer** : Core middleware logic - SQL interception, Load balancing, Monitoring, Failover & recovery, Command logging <br>
**3. Data Layer** : Multiple database nodes, SQLAlchemy engines, Command logs <br>

## 🗾 Diagrams & Documentation <br>
You can see full documentation in: <br>
```
https://github.com/dagmara1223/Load-Balancer/blob/main/dp_documentation_after_docker.pdf
```

### Logical Architecture <br> 

<img width="1000" height="913" alt="image" src="https://github.com/user-attachments/assets/71493fef-e8d5-4796-8b7b-2b9108735cb3" /> <br>

### Physical Architecture <br>

<img width="1000" height="953" alt="image" src="https://github.com/user-attachments/assets/31c567c9-ae7e-44ed-ba58-a0a291febe25" /> <br>

### Component Diagram <br> 

<img width="1118" height="969" alt="image" src="https://github.com/user-attachments/assets/f12e085a-012b-4e7d-919a-7348e21b1bf4" /> <br>

### Class Diagram <br> 

<img width="1432" height="990" alt="image" src="https://github.com/user-attachments/assets/5d14de69-2bf8-4b8c-aa48-661fd8deca58" /> <br>

### Frontend Application <br>
<img width="800" height="911" alt="image" src="https://github.com/user-attachments/assets/b53ef21e-4423-40f4-87c7-c3ef24ce0543" /> <br> 

A lightweight demo frontend that allows users to interact with the load balancer API. It provides simple controls to: 
- view active database nodes,
- choose a load balancing strategy,
- execute basic SQL operations (SELECT, INSERT, UPDATE, DELETE),
- and display API responses and logs in real time.
<br> 
The frontend serves as a testing and visualization layer for demonstrating routing, failover, and query handling behavior of the load balancer.

## 🎨 Design Patterns Used <br> 
- **Observer** <br>
Used for monitoring database node availability. <br>
**Subject**: HealthChecker <br>
**Observers**: FailoverManager, RecoveryManager <br>
<br>
Enables automatic reactions to DB state changes (UP/DOWN).

- **Command** <br>
Encapsulates modifying DB operations (INSERT/UPDATE/DELETE) as objects. <br>
Commands are: Stored, Serialized, Logged, Replayed<br>
<br>
Ensures durability when nodes are temporarily unavailable.

- **Strategy** <br>
Allows dynamic selection of routing algorithms. <br>
Implemented strategies: RoundRobinStrategy, WeightedRoundRobinStrategy, LeastTimeStrategy <br>
<br>
Strategies can be swapped without changing core logic.

## 🤖 Running the application 

### Python

Run the FastAPI backend:

```bash
python -m uvicorn demo_app.main:app --reload
```

### Frontend

1. Start a simple HTTP server in the frontend directory:

```bash
python3 -m http.server 5500 --directory demo_app/frontend
```

❗ If this version does not work try: 
```bash
python -m http.server 5500 --directory demo_app/frontend
```

2. Open your browser at:
   [http://127.0.0.1:5500/](http://127.0.0.1:5500/)

### Docker

1. In the directory with `docker-compose.yml`, start the containers:

```bash
docker compose up -d
```

2. Check running containers:

```bash
docker ps
```

3. Starting and stopping containers (`mysql1`, `mysql2`, `mysql3`, `mysql4`, `mysql5`):

```bash
docker stop mysql1
docker start mysql1
```

4. Checking database contents from the terminal(hasło: `root`):

```bash
docker exec -it mysql1 mysql -u root -proot
USE app;
SELECT * FROM users;
```

```bash
docker exec -i mysql1 mysql -u root -proot -e "USE app; SELECT * FROM users;"
```

## 💫 Failover & Recovery Test Scenario

1️⃣ **Initial State — All Nodes Healthy** <br> 
Expected: <br>
All nodes are synchronized. <br> 
<img width="200" height="200" alt="image" src="https://github.com/user-attachments/assets/0058f137-d9b6-4887-9b0c-ed9883af5d50" /> 
<img width="200" height="200" alt="image" src="https://github.com/user-attachments/assets/12e51820-7ef2-409f-91c7-d09f469ed785" />
<img width="200" height="200" alt="image" src="https://github.com/user-attachments/assets/0c4b4463-2516-471d-95be-7ca996f7c126" />
<img width="200" height="200" alt="image" src="https://github.com/user-attachments/assets/6027adc2-a93a-4ab9-855f-ba6acd9a6aa4" />
<img width="200" height="200" alt="image" src="https://github.com/user-attachments/assets/96736508-f6ab-48a3-8221-f0322a196d7a" /> <br>

Logs: <br>
<img width="400" height="450" alt="image" src="https://github.com/user-attachments/assets/15795c35-c8d1-4646-bb19-59abb49d70ef" /> <br>
<img width="600" height="700" alt="image" src="https://github.com/user-attachments/assets/299eded8-4220-44f8-8928-99df59cdd20d" /> <br>
                     
Result ✅: <br>
Confirmed — SELECT queries return the same data on all nodes. <br>

2️⃣ **Disabling mysql2 and mysql3** <br>
Expected: <br>
Health checker marks nodes as DOWN <br>
Load balancer stops routing queries to them <br>
Write operations are logged for later replay <br> 
<br> 
Command: `docker stop mysql2 mysql3` <br>
Logs: <br>
<img width="451" height="204" alt="image" src="https://github.com/user-attachments/assets/6c34b067-fb8c-4b26-bc8b-d5279a94407c" /> <br> 
<br>
Result ✅: <br>
Nodes detected as unavailable <br>
System continues working on remaining nodes <br>
Command logs created for mysql2 and mysql3 <br>

3️⃣ **Performing Operations During Failure** <br>
Expected: <br>
Executed normally on active nodes <br>
Stored in command logs for down nodes <br>
<br> 
<img width="700" height="216" alt="image" src="https://github.com/user-attachments/assets/3700b639-5d18-4116-9fc7-1932a4fd9f44" />

Command log for databases that are down (database 2 and 3): <br>
<img width="300" height="300" alt="image" src="https://github.com/user-attachments/assets/455f5493-35b7-447f-860a-6847706c42c2" /> <br> 

(For comparison command log for working database ex: mysql1): <br>
<img width="295" height="85" alt="image" src="https://github.com/user-attachments/assets/28bcc99b-abdd-4ecd-9757-bfdbe40cf930" /> <br> 
(Log for working database): <br>
<img width="285" height="300" alt="image" src="https://github.com/user-attachments/assets/9b4400e2-151d-4e1f-9767-ef2c55326f53" /> <br> 

Result ✅: <br>
Active DBs updated immediately <br>
mysql2 & mysql3 accumulated commands in their logs <br>

4️⃣ **Recovery Phase - Enabling databases mysql2 and mysql3** <br>
Expected:<br>
Recovery manager detects nodes are back <br>
Command logs replayed <br>
Logs cleared after replay <br>
Data synchronized<br>
<br>
Command: `docker start mysql2 mysql3`  <br>
Logs: <br>
<img width="636" height="278" alt="image" src="https://github.com/user-attachments/assets/e8434d55-3e7e-4e15-8231-d040630d20a2" /> <br>
As we can see, command_log for database 2 and 3 is now completly cleared: <br> 
<img width="374" height="148" alt="image" src="https://github.com/user-attachments/assets/b84c3d78-da87-4ef2-9f28-3784d86a8e43" /> <br>
And data has been completly restored: <br>
<img width="303" height="400" alt="image" src="https://github.com/user-attachments/assets/7f3cca9b-5c30-4ace-9546-703e853fe940" /> 
<img width="303" height="414" alt="image" src="https://github.com/user-attachments/assets/2fbc5198-8d16-4b11-9eb3-833c1699c506" /> <br>
<br>
Result ✅: <br> 
Logs replayed successfully <br>
Command logs cleared <br>
Data fully restored and consistent across nodes <br>

**Final Conclusion** : The system demonstrates: fault tolerance, reliable write-ahead logging, automatic failover, full data recovery after outages. The load balancer ensures eventual consistency and high availability even during node failures.

















