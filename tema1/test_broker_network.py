import time
import json
import socket
import threading
from typing import List, Dict

from common import Publication, Subscription
from complex_subscription import ComplexSubscription, AggregationField, AggregationType
from broker_network import BrokerNetwork

# Test settings
WINDOW_SIZE = 10
BROKER_COUNT = 3
BASE_PORT = 5000

class Subscriber:
    def __init__(self, subscriber_id: str, broker_port: int):
        self.subscriber_id = subscriber_id
        self.broker_port = broker_port
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.notifications = []
        self.running = True
        
    def connect(self):
        """Connect to a broker"""
        try:
            self.socket.connect(('localhost', self.broker_port))
            # Send subscriber ID as first message
            self.socket.sendall(self.subscriber_id.encode())
            
            # Start receiving thread
            self.receive_thread = threading.Thread(target=self._receive_notifications)
            self.receive_thread.daemon = True
            self.receive_thread.start()
            return True
        except Exception as e:
            print(f"Error connecting to broker on port {self.broker_port}: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from broker"""
        self.running = False
        try:
            self.socket.close()
        except:
            pass
    
    def send_simple_subscription(self, subscription: Subscription):
        """Send a simple subscription to the broker"""
        message = {
            "type": "simple_subscription",
            "data": str(subscription)
        }
        self._send_message(message)
    
    def send_complex_subscription(self, subscription: ComplexSubscription):
        """Send a complex subscription to the broker"""
        message = {
            "type": "complex_subscription",
            "data": str(subscription)
        }
        self._send_message(message)
    
    def _send_message(self, message: Dict):
        """Send a message to the broker"""
        try:
            self.socket.sendall((json.dumps(message) + '\n').encode())
        except Exception as e:
            print(f"Error sending message: {e}")
    
    def _receive_notifications(self):
        """Receive notifications from broker"""
        buffer = ""
        while self.running:
            try:
                data = self.socket.recv(4096).decode()
                if not data:
                    break
                
                buffer += data
                while '\n' in buffer:
                    line, buffer = buffer.split('\n', 1)
                    notification = json.loads(line)
                    self.notifications.append(notification)
                    print(f"Subscriber {self.subscriber_id} received: {notification}")
            except Exception as e:
                if self.running:
                    print(f"Error receiving notification: {e}")
                break

def main():
    # Start the broker network
    network = BrokerNetwork(broker_count=BROKER_COUNT, base_port=BASE_PORT, window_size=WINDOW_SIZE)
    network.start()
    
    try:
        # Create subscribers
        subscribers = []
        for i in range(3):
            # Connect each subscriber to a different broker
            subscriber = Subscriber(f"sub_{i}", BASE_PORT + (i % BROKER_COUNT))
            if subscriber.connect():
                subscribers.append(subscriber)
                print(f"Subscriber {subscriber.subscriber_id} connected to broker on port {subscriber.broker_port}")
        
        if not subscribers:
            print("No subscribers could connect. Aborting test.")
            return
        
        # Register some simple subscriptions
        simple_sub1 = Subscription.parse_str("{(city,=,\"Bucharest\");(temp,>=,10);(wind,<,11)}")
        simple_sub2 = Subscription.parse_str("{(city,=,\"Cluj\");(temp,>,15)}")
        
        subscribers[0].send_simple_subscription(simple_sub1)
        subscribers[1].send_simple_subscription(simple_sub2)
        
        # Register a complex subscription
        complex_sub = ComplexSubscription(
            city=simple_sub1.city,  # Same city as simple_sub1
            window_size=WINDOW_SIZE,
            aggregation_fields=[
                AggregationField(
                    field_name="temp",
                    operation=AggregationType.AVG,
                    value=8.5,
                    comparator=simple_sub1.temp.comparator  # Use same comparator as simple_sub1
                ),
                AggregationField(
                    field_name="wind",
                    operation=AggregationType.AVG,
                    value=13.0,
                    comparator=simple_sub1.wind.comparator  # Use same comparator as simple_sub1
                )
            ]
        )
        
        subscribers[2].send_complex_subscription(complex_sub)
        
        # Wait for subscriptions to be processed
        time.sleep(1)
        
        # Generate and send test publications
        print("\nSending test publications:")
        for i in range(30):  # Send enough to fill multiple windows
            # Create publications that will match the subscriptions
            if i % 3 == 0:
                pub = Publication.parse_str(f"{{(stationid,{i+1});(city,\"Bucharest\");(temp,{10+i%5});(rain,0.5);(wind,{8+i%3});(direction,\"NE\");(date,2023-06-15)}}")
            elif i % 3 == 1:
                pub = Publication.parse_str(f"{{(stationid,{i+1});(city,\"Cluj\");(temp,{16+i%3});(rain,0.3);(wind,12);(direction,\"SW\");(date,2023-06-15)}}")
            else:
                pub = Publication.parse_str(f"{{(stationid,{i+1});(city,\"Iasi\");(temp,5);(rain,0.8);(wind,15);(direction,\"SE\");(date,2023-06-15)}}")
                
            print(f"Publication {i}: {pub}")
            network.broadcast_publication(pub)
            time.sleep(0.2)  # Small delay between publications
        
        # Wait for all notifications to be processed
        time.sleep(3)
        
        # Print metrics
        print("\nBroker Network Metrics:")
        for metrics in network.get_metrics():
            print(json.dumps(metrics, indent=2))
            
    finally:
        # Cleanup
        for subscriber in subscribers:
            subscriber.disconnect()
        network.stop()

if __name__ == "__main__":
    main()