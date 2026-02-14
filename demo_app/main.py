"""
Demo application main module.
Creates engines, registers them with the singleton LoadBalancer,
creates per-node CommandLog objects, creates a FrontendProxyEngine
which acts as the frontend/interceptor and starts a periodic health checker.
Provides the objects via the FastAPI app.state so endpoints can use them.
"""

import os
import asyncio
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from config.config_loader import ConfigLoader
from connection.engine_factory import EngineFactory
from connection.proxy_engine import FrontendProxyEngine
from load_balancer.load_balancer import LoadBalancer, NoAvailableNodesError
from replication.command_log import CommandLog
from monitoring.health_checker import HealthChecker
from monitoring.failover_manager import FailoverManager
from replication.recovery_manager import RecoveryManager

os.makedirs("command_logs", exist_ok=True)
os.makedirs("data", exist_ok=True)

HEALTH_CHECK_INTERVAL_SECONDS = 5


async def _health_check_loop(checker: HealthChecker, interval: int, app: FastAPI):
    """
    Periodically run health checks.
    Runs in background task created on startup.
    """
    try:
        while True:
            await asyncio.to_thread(checker.run_check)
            await asyncio.sleep(interval)
    except asyncio.CancelledError:
        return


def init_system_components():
    """
    Initialize ConfigLoader, EngineFactory, LoadBalancer, per-node command logs,
    HealthChecker and managers. Return a dict with created objects.
    """
    cfg = ConfigLoader("config/database_config.yaml")

    # Create engines for configured DB nodes
    ef = EngineFactory(cfg)
    engines = ef.create_engines()  # dict name -> Engine

    lb = LoadBalancer()
    ef.register_with_load_balancer(lb)

    # Create per-node CommandLog objects
    command_logs = {}
    for name in engines.keys():
        path = os.path.join("command_logs", f"command_{name}.json")
        command_logs[name] = CommandLog(path)

    health_checker = HealthChecker(engines)
    failover = FailoverManager(lb)
    recovery = RecoveryManager(engines, command_logs, load_balancer=lb)

    health_checker.add_observer(failover)
    health_checker.add_observer(recovery)

    return {
        "config_loader": cfg,
        "engine_factory": ef,
        "engines": engines,
        "load_balancer": lb,
        "command_logs": command_logs,
        "health_checker": health_checker,
        "failover_manager": failover,
        "recovery_manager": recovery,
    }


def create_demo_app() -> FastAPI:
    app = FastAPI(title="Load Balancer Demo App")
    # Enable CORS for the minimal frontend served on port 5500
    origins = ["http://127.0.0.1:5500", "http://localhost:5500"]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    components = init_system_components()

    # create frontend proxy engine (acts as interceptor/frontend)
    # lb = components["load_balancer"]
    # frontend_engine = FrontendProxyEngine(lb, app.state.command_logs)
    frontend_engine = FrontendProxyEngine(
    components["load_balancer"],
    components["command_logs"]
)

    # store components on app.state so routers/endpoints can access them
    app.state.cfg = components["config_loader"]
    app.state.engine_factory = components["engine_factory"]
    app.state.backend_engines = components["engines"]
    app.state.command_logs = components["command_logs"]
    app.state.load_balancer = components["load_balancer"]
    app.state.health_checker = components["health_checker"]
    app.state.frontend_engine = frontend_engine

    # Prepare databases (create "users" table on all backend engines)
    for name, eng in app.state.backend_engines.items():
        try:
            with eng.begin() as conn:
                conn.execute(
                    text(
                        """
                        CREATE TABLE IF NOT EXISTS users (
                            id INTEGER PRIMARY KEY AUTO_INCREMENT,
                            name VARCHAR(255)
                        )
                        """
                    )
                )
        except OperationalError:
            print(f"[Startup] Database {name} is unavailable.")
        except Exception as e:
            print(f"[Startup] Unexpected error on {name}: {type(e).__name__}")

    # include API router
    from demo_app.api_endpoints import router as api_router
    app.include_router(api_router)

    # start periodic health checker background task
    health_task = None

    @app.on_event("startup")
    async def on_startup():
        nonlocal health_task
        loop = asyncio.get_event_loop()
        health_task = loop.create_task(
            _health_check_loop(app.state.health_checker, HEALTH_CHECK_INTERVAL_SECONDS, app)
        )
        app.state._health_task = health_task
        print("[Startup] Demo app initialized. Health checker started.")

    @app.on_event("shutdown")
    async def on_shutdown():
        nonlocal health_task
        if getattr(app.state, "_health_task", None):
            app.state._health_task.cancel()
            try:
                await app.state._health_task
            except asyncio.CancelledError:
                pass
        print("[Shutdown] Demo app stopped.")

    @app.exception_handler(NoAvailableNodesError)
    async def no_available_nodes_handler(request, exc):
        if exc.operation == "SELECT":
            return JSONResponse(
                status_code=503,
                content={"detail": "Database unavailable - cannot fetch data"}
            )

        if exc.operation == "DML":
            return JSONResponse(
                status_code=202,
                content={"detail": "No database available. Operation queued and will be executed when DB is back."}
            )
    
    return app


app = create_demo_app()



if __name__ == "__main__":
    print("Starting demo app components in standalone mode (no HTTP server).")
    _ = create_demo_app()
    print("Components created. Use `uvicorn demo_app.main:app --reload` to run the HTTP server.")
