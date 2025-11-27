from abc import ABC, abstractmethod
from sqlalchemy import text

class Command(ABC):
    '''
    Database operation that can be executed on any database engine.
    Used for logging and recovery
    '''
    @abstractmethod
    def execute(self, engine):
        pass 

    @abstractmethod
    def serialize(self) -> dict:
        "Converting command to JSON so it can be stored as JSON-like dict."
        pass 

    @staticmethod
    @abstractmethod
    def deserialize(data: dict):
        "Reconstructing command from dict"
        pass 
    