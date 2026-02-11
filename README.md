# Load-Balancer
A fault-tolerant database load balancer built with design patterns. The system intercepts SQL queries, routes SELECT statements across multiple databases, broadcasts write operations, and supports automatic failover with operation logging and full recovery after node outages.

## Uruchomienie aplikacji

### Środowisko Python

Uruchom backend FastAPI:

```bash
python -m uvicorn demo_app.main:app --reload
```

### Frontend

1. Uruchom prosty serwer HTTP w katalogu frontendu:

```bash
python3 -m http.server 5500 --directory demo_app/frontend
```

2. Otwórz przeglądarkę pod adresem:
   [http://127.0.0.1:5500/](http://127.0.0.1:5500/)

## Docker

1. W katalogu z `docker-compose.yml` uruchom kontenery:

```bash
docker compose up -d
```

2. Sprawdź działające kontenery:

```bash
docker ps
```

3. Włączanie i wyłączanie kontenerów (`mysql1`, `mysql2`, `mysql3`, `mysql4`, `mysql5`):

```bash
docker stop mysql1
docker start mysql1
```

4. Sprawdzenie zawartości bazy danych z poziomu terminala (hasło: `root`):

```bash
docker exec -it mysql1 mysql -u root -p
USE app;
SELECT * FROM users;
```
