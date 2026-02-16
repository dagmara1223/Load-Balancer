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

## 💫 Demo and visualization 

1️⃣ All databases have the same data: <br> 


