from threading import Lock
from typing import Dict, List
from load_balancer.strategies import ISelectionStrategy, WeightedRoundRobinStrategy, RoundRobinStrategy, LeastTimeStrategy
from load_balancer.node_info import NodeInfo

class NoAvailableNodesError(Exception):
    pass

class LoadBalancer:
    _instance = None
    _instance_lock = Lock()

    def __new__(cls, *args, **kwargs):
        with cls._instance_lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, strategy: ISelectionStrategy | None = None):
        if hasattr(self, "_initialized"):
            return

        self._nodes: Dict[str, NodeInfo] = {}
        self._lock = Lock()
        self._strategy = strategy or RoundRobinStrategy()
        self._initialized = True

    # Node management methods
    
    def add_node(self, name: str, engine, weight: int = 1):
        with self._lock:
            self._nodes[name] = NodeInfo(name, engine, weight)

    def remove_node(self, name: str):
        with self._lock:
            self._nodes.pop(name, None)

    def disable_node(self, name: str):
        with self._lock:
            if name in self._nodes:
                self._nodes[name].enabled = False

    def enable_node(self, name: str):
        with self._lock:
            if name in self._nodes:
                self._nodes[name].enabled = True

    def set_strategy(self, strategy: ISelectionStrategy):
        with self._lock:
            self._strategy = strategy

    # Routing methods

    def get_disabled_nodes(self):
        with self._lock:
            return [n for n in self._nodes.values() if not n.enabled]

    def _enabled_nodes(self) -> List[NodeInfo]:
        return [n for n in self._nodes.values() if n.enabled]

    def route_select(self, query: str):
        """
        SELECT - single database node
        """
        with self._lock:
            nodes = self._enabled_nodes()
            if len(nodes) == 0:
                raise NoAvailableNodesError("No enabled database nodes available for SELECT")

            node = self._strategy.pick_node(nodes)
            print(f"[LoadBalancer] SELECT from: {node.name}")
            return node.engine

    def route_dml(self, query: str):
        """
        INSERT / UPDATE / DELETE - broadcast
        """
        with self._lock:
            nodes = self._enabled_nodes()
            if len(nodes) == 0:
                raise NoAvailableNodesError("No enabled database nodes available for DML")

            return [n.engine for n in nodes]

