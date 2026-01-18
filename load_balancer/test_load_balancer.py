import pytest
from load_balancer.load_balancer import LoadBalancer
from load_balancer.node_info import NodeInfo
from load_balancer.strategies import RoundRobinStrategy, WeightedRoundRobinStrategy, LeastTimeStrategy


'''
LoadBalancer Tests
'''

class MockEngine:
    def __init__(self, name):
        self.name = name
        self.executed = []

    def execute(self, sql):
        self.executed.append(sql)


@pytest.fixture
def lb():
    LoadBalancer._instance = None
    return LoadBalancer()


@pytest.fixture
def engines():
    return [MockEngine("db1"), MockEngine("db2"), MockEngine("db3")]


def test_add_and_remove_nodes(lb, engines):
    lb.add_node("db1", engines[0])
    lb.add_node("db2", engines[1])

    assert "db1" in lb._nodes
    assert "db2" in lb._nodes

    lb.remove_node("db1")
    assert "db1" not in lb._nodes
    assert "db2" in lb._nodes


def test_enable_disable_nodes(lb, engines):
    lb.add_node("db1", engines[0])
    lb.add_node("db2", engines[1])

    lb.disable_node("db1")
    assert not lb._nodes["db1"].enabled
    lb.enable_node("db1")
    assert lb._nodes["db1"].enabled


def test_route_select_respects_strategy(lb, engines):
    lb.add_node("db1", engines[0])
    lb.add_node("db2", engines[1])

    lb.set_strategy(RoundRobinStrategy())
    picked1 = lb.route_select("SELECT * FROM t")
    picked2 = lb.route_select("SELECT * FROM t")

    assert picked1 == engines[0]
    assert picked2 == engines[1]


def test_route_select_skips_disabled_nodes(lb, engines):
    lb.add_node("db1", engines[0])
    lb.add_node("db2", engines[1])

    lb.disable_node("db1")
    engine = lb.route_select("SELECT * FROM t")
    assert engine == engines[1]


def test_route_dml_broadcast(lb, engines):
    lb.add_node("db1", engines[0])
    lb.add_node("db2", engines[1])
    lb.add_node("db3", engines[2])

    lb.disable_node("db2")
    engines_list = lb.route_dml("INSERT INTO t VALUES (1)")
    assert engines[0] in engines_list
    assert engines[2] in engines_list
    assert engines[1] not in engines_list  # disabled node skipped


def test_strategy_switch(lb, engines):
    lb.add_node("db1", engines[0])
    lb.add_node("db2", engines[1])

    lb.set_strategy(WeightedRoundRobinStrategy())
    engine1 = lb.route_select("SELECT * FROM t")
    engine2 = lb.route_select("SELECT * FROM t")

    assert engine1 != engine2



'''
RoundRobinStrategy Tests
'''

def make_nodes():
    return [
        NodeInfo("db1", engine=object()),
        NodeInfo("db2", engine=object()),
        NodeInfo("db3", engine=object()),
    ]


def test_round_robin_cycles_in_order():
    strategy = RoundRobinStrategy()
    nodes = make_nodes()

    picked = [strategy.pick_node(nodes).name for _ in range(5)]

    assert picked == ["db1", "db2", "db3", "db1", "db2"]


def test_round_robin_ignores_disabled_nodes():
    strategy = RoundRobinStrategy()
    nodes = make_nodes()

    nodes[1].enabled = False  # db2 disabled
    enabled = [n for n in nodes if n.enabled]

    picked = [strategy.pick_node(enabled).name for _ in range(4)]

    assert picked == ["db1", "db3", "db1", "db3"]


def test_round_robin_no_nodes_raises():
    strategy = RoundRobinStrategy()

    with pytest.raises(RuntimeError):
        strategy.pick_node([])

'''
WeightedRoundRobinStrategy Tests
'''


def test_weighted_round_robin_respects_weights():
    strategy = WeightedRoundRobinStrategy()

    nodes = [
        NodeInfo("db1", engine=object(), weight=2),
        NodeInfo("db2", engine=object(), weight=1),
    ]

    picked = [strategy.pick_node(nodes).name for _ in range(6)]

    # db1 twice, db2 once → repeating
    assert picked == ["db1", "db1", "db2", "db1", "db1", "db2"]


def test_weighted_rr_single_node():
    strategy = WeightedRoundRobinStrategy()
    nodes = [NodeInfo("db1", engine=object(), weight=5)]

    picked = [strategy.pick_node(nodes).name for _ in range(3)]

    assert picked == ["db1", "db1", "db1"]


def test_weighted_rr_no_nodes_raises():
    strategy = WeightedRoundRobinStrategy()

    with pytest.raises(RuntimeError):
        strategy.pick_node([])


'''
LeastTimeStrategy Tests
'''


def test_least_time_picks_fastest_node():
    strategy = LeastTimeStrategy()

    slow = NodeInfo("slow", engine=object())
    fast = NodeInfo("fast", engine=object())

    slow.record_execution(2.0)
    slow.record_execution(2.0)

    fast.record_execution(0.2)
    fast.record_execution(0.3)

    picked = strategy.pick_node([slow, fast])

    assert picked.name == "fast"


def test_least_time_ignores_nodes_with_no_history():
    strategy = LeastTimeStrategy()

    fresh = NodeInfo("fresh", engine=object())
    slow = NodeInfo("slow", engine=object())

    slow.record_execution(1.5)

    picked = strategy.pick_node([fresh, slow])

    assert picked.name == "slow"


def test_least_time_no_nodes_raises():
    strategy = LeastTimeStrategy()

    with pytest.raises(RuntimeError):
        strategy.pick_node([])
