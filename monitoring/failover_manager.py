'''
FailoverManager is an Observer responsible for reacting when a database node goes DOWN.
When HealthChecker notifies that a database is DOWN, FailoverManager disables this node 
in the LoadBalancer so that no traffic is routed to the failed database.
When the database comes back UP, it re-enables the node.

FailoverManager DOES NOT handle recovery logic (this will be done by RecoveryManager).
It focuses only on immediate failover reaction.
'''

from monitoring.observer import Observer

class FailoverManager(Observer):
    def __init__(self, load_balancer):
        """
        load_balancer must implement:
        - disable_node(db_name)
        - enable_node(db_name)
        """
        self.load_balancer = load_balancer
    
    def update(self, event:dict):
        db = event['db']
        status = event['status']
        if status =="DOWN":
            print(f"[FailoverManager] disabling database: {db}")
            self.load_balancer.disable_node(db)
        elif status == "UP":
            print(f"[FailoverManager] noticed {db} is UP (Recovery will handle enabling)")
