#!/usr/bin/env python3
# filepath: /home/dan/Documents/Master_S2/Sisteme bazate pe evenimente/Proiect/EBS-FII/tema1/evaluate_system.py
import argparse
import asyncio
import time
import random
import sys
import json
import os
from datetime import datetime
from typing import Dict, List, Set, Optional, Tuple

# Import system components
from common import (
    AppState,
    Publication,
    PublicationWithData,
    Subscription,
    ComparablePonder,
    SubscriptionPonders,
    Comparator,
    City,
    Direction,
    SUBSCRIPTIONS_STREAM
)
import pubsub_pb2
import rstream
import aio_pika

# Constants
DEFAULT_EVALUATION_TIME = 180  # 3 minutes
DEFAULT_SUBSCRIPTION_COUNT = 10000
DEFAULT_PUBLICATION_RATE = 50  # publications per second
TEST_FIELD = "temp"  # Field to test equality operators on
RETURN_TOPIC_100_PCT = "EVAL_TOPIC_100PCT"
RETURN_TOPIC_25_PCT = "EVAL_TOPIC_25PCT"

class EvaluationMetrics:
    """Tracks evaluation metrics"""
    def __init__(self):
        self.start_time = None
        self.end_time = None
        self.publications_sent = 0
        self.publications_delivered_100pct = 0
        self.publications_delivered_25pct = 0
        self.latency_sum_ms_100pct = 0
        self.latency_sum_ms_25pct = 0
        self.latency_count_100pct = 0
        self.latency_count_25pct = 0
        self.subscriptions_100pct = 0
        self.subscriptions_25pct = 0
        
    @property
    def total_publications_delivered(self):
        return self.publications_delivered_100pct + self.publications_delivered_25pct
    
    @property
    def avg_latency_100pct(self):
        if self.latency_count_100pct > 0:
            return self.latency_sum_ms_100pct / self.latency_count_100pct
        return 0
        
    @property
    def avg_latency_25pct(self):
        if self.latency_count_25pct > 0:
            return self.latency_sum_ms_25pct / self.latency_count_25pct
        return 0
    
    @property
    def avg_latency(self):
        total_count = self.latency_count_100pct + self.latency_count_25pct
        if total_count > 0:
            return (self.latency_sum_ms_100pct + self.latency_sum_ms_25pct) / total_count
        return 0
    
    @property
    def match_rate_100pct(self):
        if self.publications_sent > 0:
            return self.publications_delivered_100pct / self.publications_sent
        return 0
    
    @property
    def match_rate_25pct(self):
        if self.publications_sent > 0:
            return self.publications_delivered_25pct / self.publications_sent
        return 0
    
    @property
    def match_ratio(self):
        if self.match_rate_25pct > 0:
            return self.match_rate_100pct / self.match_rate_25pct
        return 0

    @property
    def duration(self):
        if self.start_time and self.end_time:
            return (self.end_time - self.start_time).total_seconds()
        return 0
    
    @property
    def publications_per_second(self):
        if self.duration > 0:
            return self.total_publications_delivered / self.duration
        return 0

# Global metrics object
metrics = EvaluationMetrics()

async def setup_message_consumers(appstate: AppState):
    """Setup consumers for receiving matched publications"""
    connection = await aio_pika.connect_robust(
        host=appstate.host,
        login=appstate.username,
        password=appstate.password,
        timeout=30,  # Longer timeout
        heartbeat=60,  # Increased heartbeat
    )
    channel = await connection.channel()
    
    # Purge the evaluation queues
    await channel.queue_delete(RETURN_TOPIC_100_PCT, if_unused=False, if_empty=False)
    await channel.queue_delete(RETURN_TOPIC_25_PCT, if_unused=False, if_empty=False)
    
    # 100% equality topic consumer
    channel_100pct = await connection.channel()
    await channel_100pct.set_qos(prefetch_count=1000)
    
    # Declare the queue (create if doesn't exist)
    queue_100pct = await channel_100pct.declare_queue(
        RETURN_TOPIC_100_PCT, 
        durable=True,
        auto_delete=False
    )
    
    # 25% equality topic consumer
    channel_25pct = await connection.channel()
    await channel_25pct.set_qos(prefetch_count=1000)
    
    queue_25pct = await channel_25pct.declare_queue(
        RETURN_TOPIC_25_PCT, 
        durable=True,
        auto_delete=False
    )
    
    # Start consuming messages
    await queue_100pct.consume(handle_100pct_message)
    await queue_25pct.consume(handle_25pct_message)
    
    print(f"Set up consumers for topics {RETURN_TOPIC_100_PCT} and {RETURN_TOPIC_25_PCT}")
    return connection

async def handle_100pct_message(message: aio_pika.IncomingMessage):
    """Handler for 100% equality topic messages"""
    global metrics
    async with message.process():
        current_time = datetime.now().timestamp() * 1000
        
        try:
            parsed = pubsub_pb2.MatchedPublicationWithSubscription()
            parsed.ParseFromString(message.body)
            pub_timestamp = parsed.publication.timestamp
            
            metrics.publications_delivered_100pct += 1
            
            if pub_timestamp > 0:
                latency = current_time - pub_timestamp
                metrics.latency_sum_ms_100pct += latency
                metrics.latency_count_100pct += 1
        except Exception as e:
            print(f"Error processing 100% message: {e}")

async def handle_25pct_message(message: aio_pika.IncomingMessage):
    """Handler for 25% equality topic messages"""
    global metrics
    async with message.process():
        current_time = datetime.now().timestamp() * 1000
        
        try:
            parsed = pubsub_pb2.MatchedPublicationWithSubscription()
            parsed.ParseFromString(message.body)
            pub_timestamp = parsed.publication.timestamp
            
            metrics.publications_delivered_25pct += 1
            
            if pub_timestamp > 0:
                latency = current_time - pub_timestamp
                metrics.latency_sum_ms_25pct += latency
                metrics.latency_count_25pct += 1
        except Exception as e:
            print(f"Error processing 25% message: {e}")

def create_ponders_with_equality_rate(equality_rate: float):
    """Create subscription ponders with the specified equality rate for test field"""
    ponders = SubscriptionPonders()
    
    for field in Subscription.fields():
        field_equality = equality_rate if field == TEST_FIELD else 0.5
        setattr(
            ponders, 
            field, 
            ComparablePonder(
                equality_ponder=field_equality,
                existance_ponder=0.8  # 80% chance field exists
            )
        )
    
    return ponders

async def create_test_subscriptions(appstate: AppState, count: int):
    """Create subscriptions for testing - half with 100% equality, half with 25%"""
    global metrics
    
    # Create ponders for 100% equality on test field
    ponders_100pct = create_ponders_with_equality_rate(1.0)
    
    # Create ponders for 25% equality on test field
    ponders_25pct = create_ponders_with_equality_rate(0.25)
    
    # Generate subscriptions
    subscriptions_100pct = [
        Subscription.random(ponders_100pct, RETURN_TOPIC_100_PCT) 
        for _ in range(count // 2)
    ]
    metrics.subscriptions_100pct = len(subscriptions_100pct)
    
    subscriptions_25pct = [
        Subscription.random(ponders_25pct, RETURN_TOPIC_25_PCT) 
        for _ in range(count // 2)
    ]
    metrics.subscriptions_25pct = len(subscriptions_25pct)
    
    # Register subscriptions
    async with rstream.Producer(
        host="127.0.0.1",  # Use IP address instead of hostname
        port=5552,
        username="user",
        password="password",
    ) as producer:
        await producer.start()
        await producer.create_stream(stream=SUBSCRIPTIONS_STREAM, exists_ok=True)
        
        # Register 100% equality subscriptions
        print(f"Registering {len(subscriptions_100pct)} subscriptions with 100% equality on {TEST_FIELD}...")
        message = pubsub_pb2.SubscriptionMessage()
        message.subscription_type = pubsub_pb2.SubscriptionType.SUBSCRIBE
        for sub in subscriptions_100pct:
            message.subscriptions.append(sub.to_proto())
        
        await producer.send(
            stream=SUBSCRIPTIONS_STREAM,
            message=message.SerializeToString(),
        )
        
        # Register 25% equality subscriptions
        print(f"Registering {len(subscriptions_25pct)} subscriptions with 25% equality on {TEST_FIELD}...")
        message = pubsub_pb2.SubscriptionMessage()
        message.subscription_type = pubsub_pb2.SubscriptionType.SUBSCRIBE
        for sub in subscriptions_25pct:
            message.subscriptions.append(sub.to_proto())
        
        await producer.send(
            stream=SUBSCRIPTIONS_STREAM,
            message=message.SerializeToString(),
        )
    
    print("All test subscriptions registered")
    return subscriptions_100pct, subscriptions_25pct

async def publish_test_data(appstate: AppState, duration: int, rate_limit: Optional[int] = None):
    """Publish test data for the specified duration with optional rate limiting"""
    global metrics
    
    connection = await aio_pika.connect_robust(
        host=appstate.host,
        login=appstate.username,
        password=appstate.password,
    )
    
    async with connection:
        channel = await connection.channel()
        
        # Declare filter queues for each field
        filter_queues = {}
        for field in Publication.fields():
            queue_name = f"FILTER_{field.upper()}"
            filter_queues[field] = await channel.declare_queue(
                queue_name, 
                durable=True
            )
        
        print(f"Starting publication feed for {duration} seconds...")
        metrics.start_time = datetime.now()
        end_time = time.time() + duration
        
        while time.time() < end_time:
            start_batch_time = time.time()
            batch_size = rate_limit if rate_limit else 100
            
            for _ in range(batch_size):
                # Create publication with timestamp
                pub = Publication.random()
                proto_pub = pubsub_pb2.Publication()
                proto_pub.stationid = pub.stationid
                proto_pub.city = pubsub_pb2.City.Value(pub.city.name)
                proto_pub.temp = pub.temp
                proto_pub.rain = pub.rain
                proto_pub.wind = pub.wind
                proto_pub.direction = pubsub_pb2.Direction.Value(pub.direction.name)
                proto_pub.date = pub.date.strftime("%Y-%m-%d")
                proto_pub.all_subscriptions = True
                proto_pub.timestamp = int(datetime.now().timestamp() * 1000)
                
                # Choose a random field to start filtering with
                start_field = random.choice(Publication.fields())
                
                # Send to filter queue
                await channel.default_exchange.publish(
                    aio_pika.Message(body=proto_pub.SerializeToString()),
                    routing_key=f"FILTER_{start_field.upper()}",
                )
                metrics.publications_sent += 1
            
            # If rate limiting enabled, sleep to maintain rate
            if rate_limit:
                # Calculate how long this batch took
                batch_duration = time.time() - start_batch_time
                # Sleep for the remainder of the second if needed
                sleep_time = max(0, 1.0 - batch_duration)
                if sleep_time > 0:
                    await asyncio.sleep(sleep_time)
            else:
                # Small sleep to prevent overloading
                await asyncio.sleep(0.001)
        
        metrics.end_time = datetime.now()
        pub_duration = metrics.duration
        print(f"Published {metrics.publications_sent} messages in {pub_duration:.2f} seconds")
        print(f"Publication rate: {metrics.publications_sent/pub_duration:.2f} msgs/sec")

def write_results():
    """Write evaluation results to file"""
    with open("evaluation_results.md", "w") as f:
        f.write("# Pub/Sub System Evaluation Results\n\n")
        
        f.write("## Test Configuration\n\n")
        f.write(f"- Test field for equality operator comparison: {TEST_FIELD}\n")
        f.write(f"- Evaluation period: {metrics.duration:.2f} seconds\n")
        f.write(f"- Total subscriptions: {metrics.subscriptions_100pct + metrics.subscriptions_25pct}\n")
        f.write(f"  - 100% equality subscriptions: {metrics.subscriptions_100pct}\n")
        f.write(f"  - 25% equality subscriptions: {metrics.subscriptions_25pct}\n")
        f.write(f"- Publications sent: {metrics.publications_sent}\n")
        f.write(f"- Start time: {metrics.start_time}\n")
        f.write(f"- End time: {metrics.end_time}\n\n")
        
        f.write("## Results\n\n")
        
        # a) Publications delivered
        f.write("### a) Publication Delivery\n\n")
        f.write(f"- Total publications delivered: {metrics.total_publications_delivered}\n")
        f.write(f"- Publications delivered per second: {metrics.publications_per_second:.2f}\n")
        f.write(f"- Delivery success rate: {(metrics.total_publications_delivered/metrics.publications_sent)*100:.2f}%\n\n")
        
        # b) Latency
        f.write("### b) Latency\n\n")
        f.write(f"- Overall average latency: {metrics.avg_latency:.2f} ms\n")
        f.write(f"- 100% equality subscriptions latency: {metrics.avg_latency_100pct:.2f} ms\n")
        f.write(f"- 25% equality subscriptions latency: {metrics.avg_latency_25pct:.2f} ms\n\n")
        
        # c) Matching rates
        f.write("### c) Matching Rates\n\n")
        
        f.write("#### 100% Equality Operator\n\n")
        f.write(f"- Subscriptions: {metrics.subscriptions_100pct}\n")
        f.write(f"- Matched publications: {metrics.publications_delivered_100pct}\n")
        f.write(f"- Matching rate: {metrics.match_rate_100pct*100:.2f}%\n\n")
        
        f.write("#### 25% Equality Operator\n\n")
        f.write(f"- Subscriptions: {metrics.subscriptions_25pct}\n")
        f.write(f"- Matched publications: {metrics.publications_delivered_25pct}\n")
        f.write(f"- Matching rate: {metrics.match_rate_25pct*100:.2f}%\n\n")
        
        f.write("#### Comparison\n\n")
        if metrics.match_rate_25pct > 0:
            f.write(f"- Equality operator ratio (100% vs 25%): {metrics.match_ratio:.2f}x\n")

def print_progress(duration: int):
    """Print progress during the test"""
    start_time = time.time()
    while time.time() - start_time < duration + 10:  # +10 seconds for processing
        elapsed = time.time() - start_time
        if elapsed > duration:
            print(f"Test complete, processing final messages ({elapsed:.1f}s / {duration+10}s)")
        else:
            print(f"Running test ({elapsed:.1f}s / {duration}s): {metrics.publications_sent} sent, " 
                  f"{metrics.total_publications_delivered} delivered")
        time.sleep(5)  # Update every 5 seconds

async def cleanup(connection):
    """Close connections cleanly"""
    try:
        await connection.close()
    except Exception as e:
        print(f"Error during cleanup: {e}")

async def run_evaluation(appstate: AppState, duration: int, sub_count: int, rate_limit: Optional[int] = None):
    """Run the complete evaluation"""
    try:
        # Make sure our consumer queues exist
        connection = await aio_pika.connect_robust(
            host=appstate.host,
            login=appstate.username,
            password=appstate.password,
        )
        channel = await connection.channel()
        await channel.declare_queue(RETURN_TOPIC_100_PCT, durable=True)
        await channel.declare_queue(RETURN_TOPIC_25_PCT, durable=True)
        await connection.close()
        
        # Set up message consumers
        consumer_connection = await setup_message_consumers(appstate)
        
        # Create test subscriptions
        await create_test_subscriptions(appstate, sub_count)
        
        # Wait for subscriptions to be processed
        print("Waiting for subscriptions to be processed...")
        await asyncio.sleep(5)
        
        # Start progress reporting task
        progress_task = asyncio.create_task(asyncio.to_thread(print_progress, duration))
        
        # Run publication feed
        await publish_test_data(appstate, duration, rate_limit)
        
        # Wait for remaining messages to be processed
        print("Waiting for remaining messages to be processed...")
        await asyncio.sleep(10)
        
        # Clean up
        await cleanup(consumer_connection)
        await progress_task
        
        # Write results
        write_results()
        print("\nEvaluation complete! Results written to evaluation_results.md")
        
        # Print summary
        print("\nSUMMARY:")
        print(f"- Publications sent: {metrics.publications_sent}")
        print(f"- Publications delivered: {metrics.total_publications_delivered}")
        print(f"- Average latency: {metrics.avg_latency:.2f} ms")
        print(f"- Matching rate (100% equality): {metrics.match_rate_100pct*100:.2f}%")
        print(f"- Matching rate (25% equality): {metrics.match_rate_25pct*100:.2f}%")
        if metrics.match_rate_25pct > 0:
            print(f"- Ratio: {metrics.match_ratio:.2f}x")
        
    except Exception as e:
        print(f"Error during evaluation: {e}")
        import traceback
        traceback.print_exc()

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='Evaluate pub/sub system')
    parser.add_argument('--time', type=int, default=DEFAULT_EVALUATION_TIME, 
                        help=f'Evaluation time in seconds (default: {DEFAULT_EVALUATION_TIME})')
    parser.add_argument('--subs', type=int, default=DEFAULT_SUBSCRIPTION_COUNT,
                        help=f'Number of subscriptions to create (default: {DEFAULT_SUBSCRIPTION_COUNT})')
    parser.add_argument('--rate', type=int, 
                        help='Publications per second (rate limiting)')
    parser.add_argument('--no-rate-limit', action='store_true',
                        help='Disable rate limiting (publish as fast as possible)')
    
    return parser.parse_args()

def main():
    """Main entry point"""
    # Parse arguments
    args = parse_arguments()
    
    # Check for incompatible args
    if args.rate is not None and args.no_rate_limit:
        print("Error: Cannot specify both --rate and --no-rate-limit")
        sys.exit(1)
    
    # Determine rate limit
    rate_limit = None if args.no_rate_limit else (args.rate or DEFAULT_PUBLICATION_RATE)
    
    # Create app state
    appstate = AppState(
        host=os.getenv("RABBITMQ_HOST", "localhost"),
        username=os.getenv("RABBITMQ_USER", "user"),
        password=os.getenv("RABBITMQ_PASS", "password"),
    )
    
    print(f"=== Pub/Sub System Evaluation ===")
    print(f"Duration: {args.time} seconds")
    print(f"Subscriptions: {args.subs}")
    if args.no_rate_limit:
        print("Rate: UNLIMITED (maximum throughput)")
    else:
        print(f"Rate: {rate_limit} publications/second")
    print(f"Testing equality operators on field: {TEST_FIELD}")
    print("================================")
    
    # Run the evaluation
    asyncio.run(run_evaluation(
        appstate=appstate, 
        duration=args.time, 
        sub_count=args.subs,
        rate_limit=rate_limit
    ))

if __name__ == "__main__":
    main()