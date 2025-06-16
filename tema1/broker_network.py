import time
import threading
from typing import List, Dict

from broker import Broker
from common import Publication

class BrokerNetwork:
    def __init__(self, broker_count: int = 3, base_port: int = 5000, window_size: int = 10):
        self.brokers: List[Broker] = []
        
        # Create brokers
        for i in range(broker_count):
            broker = Broker(
                broker_id=f"broker_{i}",
                port=base_port + i,
                window_size=window_size
            )
            self.brokers.append(broker)
    
    def start(self):
        """Start all brokers"""
        for broker in self.brokers:
            broker.start()
            
        # Give brokers time to initialize
        time.sleep(1)
    
    def stop(self):
        """Stop all brokers"""
        print("Stopping broker network...")
        for broker in self.brokers:
            broker.stop()
        print("Broker network stopped")
    
    def broadcast_publication(self, publication: Publication):
        """Send a publication to all brokers"""
        for broker in self.brokers:
            broker.process_publication(publication)
    
    def get_metrics(self) -> List[Dict]:
        """Get metrics from all brokers"""
        return [broker.get_metrics() for broker in self.brokers]