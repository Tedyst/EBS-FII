import time
from typing import Dict, List, Set, Optional, Tuple
import threading
import socket
import pickle
import json
from datetime import datetime

from common import Publication, Subscription, SubscriptionMatcher
from complex_subscription import ComplexSubscription
from window_processor import WindowProcessor

class Broker:
    def __init__(self, broker_id: str, port: int, window_size: int = 10):
        self.broker_id = broker_id
        self.port = port
        
        # Data structures for subscriptions
        self.simple_subscriptions: List[Subscription] = []
        self.complex_subscriptions: List[ComplexSubscription] = []
        
        # Maps subscriber_id to subscription indices
        self.subscriber_subscriptions: Dict[str, Set[int]] = {}
        self.subscriber_complex_subscriptions: Dict[str, Set[int]] = {}
        
        # Processing components
        self.matcher = SubscriptionMatcher(self.simple_subscriptions)
        self.window_processor = WindowProcessor(window_size)
        
        # For metrics collection
        self.publication_count = 0
        self.matched_count = 0
        self.start_time = None
        self.latencies = []
        
        # Subscriber connections
        self.subscribers: Dict[str, socket.socket] = {}
        
        # Communication setup
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server_socket.settimeout(1.0)  # Add timeout so accept() doesn't block forever
        self.server_socket.bind(('localhost', port))
        self.server_socket.listen(5)
        
        # Threading
        self.running = True
        self.accept_thread = threading.Thread(target=self._accept_connections)
        
    def start(self):
        """Start the broker"""
        print(f"Broker {self.broker_id} starting on port {self.port}")
        self.start_time = time.time()
        self.accept_thread.start()
    
    def stop(self):
        """Stop the broker"""
        print(f"Stopping broker {self.broker_id}...")
        self.running = False
        
        # First close all subscriber connections
        for sub_id, conn in list(self.subscribers.items()):
            try:
                conn.close()
            except:
                pass
        self.subscribers.clear()
        
        # Now close the server socket
        try:
            self.server_socket.close()
        except:
            pass
        
        # Wait for accept thread to terminate (should be quick now)
        if self.accept_thread.is_alive():
            self.accept_thread.join(timeout=2.0)  # Add timeout to avoid hanging
        
        print(f"Broker {self.broker_id} stopped")
    
    def register_subscription(self, subscriber_id: str, subscription: Subscription):
        """Register a simple subscription"""
        sub_index = len(self.simple_subscriptions)
        self.simple_subscriptions.append(subscription)
        
        if subscriber_id not in self.subscriber_subscriptions:
            self.subscriber_subscriptions[subscriber_id] = set()
        
        self.subscriber_subscriptions[subscriber_id].add(sub_index)
        self.matcher = SubscriptionMatcher(self.simple_subscriptions)
        
        print(f"Broker {self.broker_id}: Registered simple subscription for {subscriber_id}")
    
    def register_complex_subscription(self, subscriber_id: str, subscription: ComplexSubscription):
        """Register a complex subscription"""
        sub_index = len(self.complex_subscriptions)
        self.complex_subscriptions.append(subscription)
        
        if subscriber_id not in self.subscriber_complex_subscriptions:
            self.subscriber_complex_subscriptions[subscriber_id] = set()
        
        self.subscriber_complex_subscriptions[subscriber_id].add(sub_index)
        
        print(f"Broker {self.broker_id}: Registered complex subscription for {subscriber_id}")
    
    def process_publication(self, publication: Publication):
        """Process a publication and notify matching subscribers"""
        self.publication_count += 1
        recv_time = time.time()
        
        # Process for simple subscriptions
        matching_subscriptions = self.matcher.match(publication)
        
        # Find subscribers to notify for simple subscriptions
        subscribers_to_notify = set()
        for i, sub in enumerate(self.simple_subscriptions):
            if sub in matching_subscriptions:
                for subscriber_id, sub_indices in self.subscriber_subscriptions.items():
                    if i in sub_indices:
                        subscribers_to_notify.add(subscriber_id)
                        self.matched_count += 1
        
        # Send notifications for simple subscriptions
        for subscriber_id in subscribers_to_notify:
            if subscriber_id in self.subscribers:
                self._send_notification(subscriber_id, publication, "simple_match")
                
                # Record latency
                self.latencies.append(time.time() - recv_time)
        
        # Process for complex subscriptions (window processing)
        is_window_complete, city, aggregations = self.window_processor.add_publication(publication)
        
        if is_window_complete:
            matching_complex_subs = self.window_processor.match_complex_subscriptions(
                self.complex_subscriptions, city, aggregations
            )
            
            # Find subscribers to notify for complex subscriptions
            for i, complex_sub in enumerate(self.complex_subscriptions):
                if complex_sub in matching_complex_subs:
                    for subscriber_id, sub_indices in self.subscriber_complex_subscriptions.items():
                        if i in sub_indices and subscriber_id in self.subscribers:
                            # Create meta-publication
                            meta_publication = {
                                "type": "complex_match",
                                "city": str(city.value),
                                "conditions_met": True,
                                "aggregations": {k: v for k, v in aggregations.items() 
                                               if not k.endswith("time")},
                                "window_id": self.window_processor.window_counts[city]
                            }
                            
                            # Send notification
                            self._send_notification(subscriber_id, meta_publication, "complex_match")
    
    def _send_notification(self, subscriber_id: str, data, msg_type: str):
        """Send a notification to a subscriber"""
        if subscriber_id in self.subscribers:
            try:
                message = {
                    "type": msg_type,
                    "broker_id": self.broker_id,
                    "timestamp": time.time(),
                    "data": str(data) if isinstance(data, (Publication, ComplexSubscription)) else data
                }
                self.subscribers[subscriber_id].sendall(json.dumps(message).encode() + b'\n')
            except Exception as e:
                print(f"Error sending to subscriber {subscriber_id}: {e}")
                # Remove disconnected subscriber
                if subscriber_id in self.subscribers:
                    del self.subscribers[subscriber_id]
    
    def _accept_connections(self):
        """Accept incoming connections from subscribers"""
        while self.running:
            try:
                client_sock, addr = self.server_socket.accept()
                # First message should contain subscriber ID
                data = client_sock.recv(1024).decode().strip()
                if data:
                    subscriber_id = data
                    self.subscribers[subscriber_id] = client_sock
                    print(f"Broker {self.broker_id}: Subscriber {subscriber_id} connected")
                    
                    # Start a thread to handle this subscriber
                    thread = threading.Thread(target=self._handle_subscriber, args=(subscriber_id, client_sock))
                    thread.daemon = True
                    thread.start()
            except socket.timeout:
                # This is expected - the timeout allows us to check self.running periodically
                continue
            except Exception as e:
                if self.running:  # Only log if not intentionally stopping
                    print(f"Error accepting connection: {e}")
    
    def _handle_subscriber(self, subscriber_id: str, client_sock: socket.socket):
        """Handle messages from a specific subscriber"""
        while self.running:
            try:
                data = client_sock.recv(4096).decode().strip()
                if not data:
                    break
                    
                # Parse message
                message = json.loads(data)
                msg_type = message.get("type")
                
                if msg_type == "simple_subscription":
                    sub_data = message.get("data")
                    subscription = Subscription.parse_str(sub_data)
                    self.register_subscription(subscriber_id, subscription)
                    
                elif msg_type == "complex_subscription":
                    sub_data = message.get("data")
                    complex_sub = ComplexSubscription.parse_str(sub_data)
                    self.register_complex_subscription(subscriber_id, complex_sub)
                    
            except Exception as e:
                print(f"Error handling subscriber {subscriber_id}: {e}")
                break
                
        # Clean up when subscriber disconnects
        if subscriber_id in self.subscribers:
            del self.subscribers[subscriber_id]
        print(f"Broker {self.broker_id}: Subscriber {subscriber_id} disconnected")
    
    def get_metrics(self):
        """Get broker performance metrics"""
        elapsed = time.time() - self.start_time if self.start_time else 0
        avg_latency = sum(self.latencies) / len(self.latencies) if self.latencies else 0
        
        return {
            "broker_id": self.broker_id,
            "publications_received": self.publication_count,
            "publications_matched": self.matched_count,
            "match_ratio": self.matched_count / self.publication_count if self.publication_count > 0 else 0,
            "elapsed_time": elapsed,
            "publications_per_second": self.publication_count / elapsed if elapsed > 0 else 0,
            "avg_latency_ms": avg_latency * 1000,  # in milliseconds
            "subscriber_count": len(self.subscribers),
            "simple_subscription_count": len(self.simple_subscriptions),
            "complex_subscription_count": len(self.complex_subscriptions)
        }