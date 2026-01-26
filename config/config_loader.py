import yaml
from typing import Dict, Any


class ConfigLoader:
    def __init__(self, config_path: str):
        self.config_path = config_path


    def load(self) -> Dict[str, Any]:
        with open(self.config_path, "r") as f:
            return yaml.safe_load(f)