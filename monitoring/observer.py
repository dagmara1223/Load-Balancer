'''
Observer is a listener and also a reactor to events. It is an object that waits for
messages and then reacts based on delivered information.
FailoverManager -> reacts when database is down
RecoveryManager -> reacts when database is back UP
CommandLogManager -> reacts for data changes then logs operations
'''

from abc import ABC, abstractmethod

class Observer(ABC):
    @abstractmethod 
    def update(self, event: dict):
        """
        event example:
        {
            "db":"db1",
            "status":"UP | DOWN"
        }
        """
        pass