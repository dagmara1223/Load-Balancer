class NodeInfo:
    def __init__(self, name: str, engine, weight: int = 1, enabled: bool = True):
        self.name = name
        self.engine = engine
        self.enabled = enabled
        self.weight = weight
        
        # LeastTime metrics
        self.total_time = 0.0
        self.query_count = 0

    def record_execution(self, elapsed: float):
        self.total_time += elapsed
        self.query_count += 1

    @property
    def avg_response_time(self) -> float:
        if self.query_count == 0:
            return float("inf")
        return self.total_time / self.query_count

    def __repr__(self):
        return f"<NodeInfo {self.name} enabled={self.enabled} weight={self.weight} avg_response_time={self.avg_response_time}>"