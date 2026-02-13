from typing import Dict
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

from config.config_loader import ConfigLoader
from load_balancer.load_balancer import LoadBalancer


class EngineFactory:
    def __init__(self, config_loader: ConfigLoader):
        self.config_loader = config_loader
        self.engines: Dict[str, Engine] = {}

    def create_engines(self) -> Dict[str, Engine]:
        config = self.config_loader.load()

        for db_cfg in config["databases"]:
            name = db_cfg["name"]
            url = db_cfg["url"]

            engine = create_engine(url, echo=False, future=True)
            self.engines[name] = engine

        return self.engines

    def register_with_load_balancer(self, lb: LoadBalancer):
        config = self.config_loader.load()

        for db_cfg in config["databases"]:
            name = db_cfg["name"]
            weight = db_cfg.get("weight", 1)

            engine = self.engines[name]
            # Register node as disabled initially. HealthChecker + FailoverManager
            # will enable nodes once they respond to pings.
            lb.add_node(name=name, engine=engine, weight=weight, enabled=False)