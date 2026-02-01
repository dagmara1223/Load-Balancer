from abc import ABC, abstractmethod
from typing import List
from load_balancer.node_info import NodeInfo

class ISelectionStrategy(ABC):
    @abstractmethod
    def pick_node(self, enabled_nodes: List[NodeInfo]) -> NodeInfo:
        pass


class RoundRobinStrategy(ISelectionStrategy):
    def __init__(self):
        self._index = 0

    def pick_node(self, enabled_nodes):
        node = enabled_nodes[self._index]
        self._index = (self._index + 1) % len(enabled_nodes)
        return node


class WeightedRoundRobinStrategy(ISelectionStrategy):
    def __init__(self):
        self._index = 0
        self._counter = 0

    def pick_node(self, enabled_nodes: List[NodeInfo]) -> NodeInfo:
        node = enabled_nodes[self._index]

        self._counter += 1
        if self._counter >= node.weight:
            self._counter = 0
            self._index = (self._index + 1) % len(enabled_nodes)

        return node
    

class LeastTimeStrategy(ISelectionStrategy):
    def pick_node(self, enabled_nodes):

        return min(enabled_nodes, key=lambda n: n.avg_response_time)
