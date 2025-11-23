'''
Subject generates events. It is an objects that holds list with all the observers and then
informs them when change happened. In our case the most important from all subjects is a Health 
Checker since he can see that the database is up / down. Subject logs events and sends them
to all observers.
'''

class Subject:
    def __init__(self):
        self._observers = [] # list of all ovservers

    def add_observer(self, observer):
        if observer not in self._observers:
            self._observers.append(observer)
    
    def remove_observer(self, observer):
        if observer in self._observers:
            self._observers.remove(observer)
    
    def notify(self, event:dict):
        for observer in self._observers:
            observer.update(event)