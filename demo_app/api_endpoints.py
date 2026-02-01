"""
FastAPI endpoints for the demo application.

- GET /users -> SELECT query (should be routed to a single backend via LoadBalancer)
- POST /users -> INSERT (DML) -> will be broadcast to enabled nodes.
                 For nodes currently disabled, the Insert command will be appended to their
                 per-node CommandLog so it can be replayed later.
- GET /nodes -> return info about backend nodes (enabled, weight)
- POST /nodes/{name}/disable and /enable -> manual control for demo/testing
"""

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import text
from replication.commands import Insert
from typing import Dict, Any

router = APIRouter()


class CreateUserRequest(BaseModel):
    name: str


def _get_app_state(request: Request):
    return request.app.state


@router.get("/users")
def list_users(request: Request):
    """
    Execute SELECT on the frontend engine.
    The SQLAlchemy listener will route the SELECT
    to a single backend engine (weighted round-robin).
    """
    state = _get_app_state(request)
    engine = state.frontend_engine

    with engine.connect() as conn:
        result = conn.execute(text("SELECT id, name FROM users ORDER BY id"))
        rows = [dict(row) for row in result.fetchall()]

    return {"rows": rows}


@router.post("/users")
def create_user(payload: CreateUserRequest, request: Request):
    """
    Create a user. For the demo we will:
    - Construct an Insert command object and persist it to any currently-disabled nodes' CommandLog.
    - Execute an INSERT via the frontend engine (which will cause the listener to broadcast to all enabled nodes).
    """
    state = _get_app_state(request)
    frontend_engine = state.frontend_engine
    lb = state.load_balancer
    command_logs: Dict[str, Any] = state.command_logs

    # Creating command object to log for disabled nodes.
    # We store only minimal info (table, values).
    insert_cmd = Insert("users", {"name": payload.name})

    # Inspecting internal LoadBalancer node states to find disabled nodes
    disabled_nodes = []
    try:
        for name, node in lb._nodes.items():
            if not node.enabled:
                disabled_nodes.append(name)
    except Exception:
        disabled_nodes = []

    # Appending command to disabled nodes' command logs (so they will be replayed later)
    for name in disabled_nodes:
        log = command_logs.get(name)
        if log:
            print(f"[API] Persisting command to log for node {name}")
            log.add(insert_cmd)

    # Execute INSERT on frontend engine.
    # Listener will broadcast to all enabled backend engines.
    with frontend_engine.begin() as conn:
        conn.execute(text("INSERT INTO users (name) VALUES (:name)"), {"name": payload.name})

    return {"status": "created", "name": payload.name}


@router.get("/nodes")
def nodes_info(request: Request):
    state = _get_app_state(request)
    lb = state.load_balancer

    info = []
    for name, node in lb._nodes.items():
        info.append(
            {
                "name": name,
                "enabled": bool(node.enabled),
                "weight": int(node.weight),
                "repr": repr(node),
            }
        )
    return {"nodes": info}


@router.post("/nodes/{name}/disable")
def disable_node(name: str, request: Request):
    state = _get_app_state(request)
    lb = state.load_balancer
    if name not in lb._nodes:
        raise HTTPException(status_code=404, detail="Node not found")
    lb.disable_node(name)
    return {"node": name, "enabled": False}


@router.post("/nodes/{name}/enable")
def enable_node(name: str, request: Request):
    state = _get_app_state(request)
    lb = state.load_balancer
    if name not in lb._nodes:
        raise HTTPException(status_code=404, detail="Node not found")
    lb.enable_node(name)
    return {"node": name, "enabled": True}
