from threading import Lock
from typing import List, Dict, Any
import itertools

class LoadBalancer:
    _instance = None
    _lock = Lock()  # ensure thread-safe singleton

    def __new__(cls, *args, **kwargs):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self.nodes: Dict[str, Dict[str, Any]] = {}  # node_name -> {engine, enabled}
        self._rr_iter = None  # round-robin iterator
        self._initialized = True

    # ----------------------
    # Node management
    # ----------------------
    def add_node(self, name: str, engine, weight: int = 1):
        self.nodes[name] = {"engine": engine, "enabled": True, "weight": weight}
        self._update_rr_iter()
        print(f"[LoadBalancer] Added node '{name}' with weight {weight}")


    def remove_node(self, name: str):
        if name in self.nodes:
            del self.nodes[name]
            self._update_rr_iter()
        print(f"[LoadBalancer] Removed node '{name}'")

    def disable_node(self, name: str):
        if name in self.nodes:
            self.nodes[name]["enabled"] = False
            self._update_rr_iter()
        print(f"[LoadBalancer] Disabled node '{name}'")

    def enable_node(self, name: str):
        if name in self.nodes:
            self.nodes[name]["enabled"] = True
            self._update_rr_iter()
        print(f"[LoadBalancer] Enabled node '{name}'")

    def _update_rr_iter(self):
        """Create weighted round-robin iterator only with enabled nodes"""
        weighted_nodes: List[str] = []
        for name, info in self.nodes.items():
            if info["enabled"]:
                weighted_nodes.extend([name] * info.get("weight", 1))
        self._rr_iter = itertools.cycle(weighted_nodes) if weighted_nodes else None

    # ----------------------
    # Routing
    # ----------------------
    def route_select(self, query: str):
        """Return a single engine for SELECT queries using round-robin"""
        if not self._rr_iter:
            raise Exception("No enabled nodes available")
        node_name = next(self._rr_iter)
        print(f"[LoadBalancer] Routing SELECT query to node '{node_name}'")
        return self.nodes[node_name]["engine"]

    def route_dml(self, query: str):
        """Return all enabled engines for INSERT/UPDATE/DELETE"""
        print(f"[LoadBalancer] Routing DML query to all enabled nodes")
        return [info["engine"] for info in self.nodes.values() if info["enabled"]]
