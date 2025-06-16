#!/usr/bin/env python3
import asyncio
import random
import time
import json
import uuid
import argparse
from datetime import datetime, timedelta, date
import signal
import sys
from typing import Optional, Dict, List, Set, Tuple

import aio_pika
import rstream

from common import (
    AppState, Subscription, Publication, PublicationWithData,
    Comparable, Comparator, Aggregatable, AggregateType,
    SubscriptionPonders, ComparablePonder, City, Direction
)
from matching import AllComparableFilter, ComparableFilter
from aggregation import AggregationFilter, Aggregator
import pubsub_pb2

# Constants
SUBSCRIPTIONS_STREAM = "SUBSCRIPTIONS"
PUBLICATIONS_STREAM = "PUBLICATIONS"
RETURN_TOPIC_100_PCT = "EVAL_TOPIC_100PCT"
RETURN_TOPIC_25_PCT = "EVAL_TOPIC_25PCT"
RETURN_TOPIC_AGGREGATION = "EVAL_TOPIC_AGGREGATION"
TEST_FIELD = "temp"  # Field to test equality operator on

class EvaluationMetrics:
    def __init__(self):
        # Publication metrics
        self.publications_sent = 0
        self.publications_delivered_100pct = 0
        self.publications_delivered_25pct = 0
        self.publications_delivered_agg = 0
        self.start_time = None
        self.end_time = None
        
        # Latency metrics
        self.latency_sum_ms_100pct = 0
        self.latency_count_100pct = 0
        self.latency_sum_ms_25pct = 0
        self.latency_count_25pct = 0
        self.latency_sum_ms_agg = 0
        self.latency_count_agg = 0
        
        # Subscription metrics
        self.subscriptions_100pct = 0
        self.subscriptions_25pct = 0
        self.subscriptions_agg = 0
    
    @property
    def total_publications_delivered(self):
        return self.publications_delivered_100pct + self.publications_delivered_25pct + self.publications_delivered_agg
    
    @property
    def avg_latency_ms_100pct(self):
        if self.latency_count_100pct > 0:
            return self.latency_sum_ms_100pct / self.latency_count_100pct
        return 0
    
    @property
    def avg_latency_ms_25pct(self):
        if self.latency_count_25pct > 0:
            return self.latency_sum_ms_25pct / self.latency_count_25pct
        return 0
        
    @property
    def avg_latency_ms_agg(self):
        if self.latency_count_agg > 0:
            return self.latency_sum_ms_agg / self.latency_count_agg
        return 0
    
    @property
    def avg_latency_ms_total(self):
        total_sum = self.latency_sum_ms_100pct + self.latency_sum_ms_25pct + self.latency_sum_ms_agg
        total_count = self.latency_count_100pct + self.latency_count_25pct + self.latency_count_agg
        if total_count > 0:
            return total_sum / total_count
        return 0
    
    @property
    def match_rate_100pct(self):
        if self.publications_sent > 0:
            return (self.publications_delivered_100pct / self.publications_sent) * 100
        return 0
    
    @property
    def match_rate_25pct(self):
        if self.publications_sent > 0:
            return (self.publications_delivered_25pct / self.publications_sent) * 100
        return 0
    
    @property
    def match_rate_agg(self):
        if self.publications_sent > 0:
            return (self.publications_delivered_agg / self.publications_sent) * 100
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

async def handle_100pct_message(message: aio_pika.IncomingMessage):
    """Handler for 100% equality topic messages"""
    global metrics
    async with message.process():
        current_time = datetime.now().timestamp() * 1000
        
        try:
            parsed = pubsub_pb2.MatchedPublicationWithSubscription()
            parsed.ParseFromString(message.body)
            
            # Debug message structure if needed
            #print(f"Debug 100% message: {parsed}")
            
            # Access timestamp from the publication
            if not parsed.HasField('publication'):
                print("Warning: No publication field in message")
                pub_timestamp = 0
            else:
                # Get timestamp
                pub_timestamp = parsed.publication.timestamp
                if pub_timestamp == 0:
                    print("Warning: Publication has zero timestamp")
            
            metrics.publications_delivered_100pct += 1
            
            if pub_timestamp > 0:
                latency = current_time - pub_timestamp
                if latency > 0:  # Sanity check
                    metrics.latency_sum_ms_100pct += latency
                    metrics.latency_count_100pct += 1
                    #print(f"100% message latency: {latency:.2f} ms")
        except Exception as e:
            print(f"Error processing 100% message: {e}")
            import traceback
            traceback.print_exc()

async def handle_25pct_message(message: aio_pika.IncomingMessage):
    """Handler for 25% equality topic messages"""
    global metrics
    async with message.process():
        current_time = datetime.now().timestamp() * 1000
        
        try:
            parsed = pubsub_pb2.MatchedPublicationWithSubscription()
            parsed.ParseFromString(message.body)
            
            # Debug message structure if needed
            #print(f"Debug 25% message: {parsed}")
            
            # Access timestamp from the publication
            if not parsed.HasField('publication'):
                print("Warning: No publication field in message")
                pub_timestamp = 0
            else:
                # Get timestamp
                pub_timestamp = parsed.publication.timestamp
                if pub_timestamp == 0:
                    print("Warning: Publication has zero timestamp")
            
            metrics.publications_delivered_25pct += 1
            
            if pub_timestamp > 0:
                latency = current_time - pub_timestamp
                if latency > 0:  # Sanity check
                    metrics.latency_sum_ms_25pct += latency
                    metrics.latency_count_25pct += 1
                    #print(f"25% message latency: {latency:.2f} ms")
        except Exception as e:
            print(f"Error processing 25% message: {e}")
            import traceback
            traceback.print_exc()

async def handle_agg_message(message: aio_pika.IncomingMessage):
    """Handler for aggregation topic messages"""
    global metrics
    async with message.process():
        current_time = datetime.now().timestamp() * 1000
        
        try:
            parsed = pubsub_pb2.MatchedPublicationWithSubscription()
            parsed.ParseFromString(message.body)
            
            # Access timestamp from the publication
            if not parsed.HasField('publication'):
                print("Warning: No publication field in message")
                pub_timestamp = 0
            else:
                # Get timestamp
                pub_timestamp = parsed.publication.timestamp
                if pub_timestamp == 0:
                    print("Warning: Aggregation publication has zero timestamp")
            
            metrics.publications_delivered_agg += 1
            
            if pub_timestamp > 0:
                latency = current_time - pub_timestamp
                if latency > 0:  # Sanity check
                    metrics.latency_sum_ms_agg += latency
                    metrics.latency_count_agg += 1
        except Exception as e:
            print(f"Error processing aggregation message: {e}")
            import traceback
            traceback.print_exc()

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
    
    # First purge all queues to ensure clean test
    print("Purging existing queues...")
    try:
        await channel.queue_delete(RETURN_TOPIC_100_PCT, if_unused=False, if_empty=False)
        await channel.queue_delete(RETURN_TOPIC_25_PCT, if_unused=False, if_empty=False)
        await channel.queue_delete(RETURN_TOPIC_AGGREGATION, if_unused=False, if_empty=False)
    except Exception as e:
        print(f"Queue purging error (can be ignored if queues don't exist yet): {e}")
    
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
    
    # Aggregation topic consumer
    channel_agg = await connection.channel()
    await channel_agg.set_qos(prefetch_count=1000)
    
    queue_agg = await channel_agg.declare_queue(
        RETURN_TOPIC_AGGREGATION, 
        durable=True,
        auto_delete=False
    )
    
    # Start consuming messages
    await queue_100pct.consume(handle_100pct_message)
    await queue_25pct.consume(handle_25pct_message)
    await queue_agg.consume(handle_agg_message)
    
    return connection

async def create_aggregation_subscriptions(appstate: AppState, count: int):
    """Create aggregation subscriptions"""
    global metrics
    
    aggregation_subscriptions = []
    
    # Create aggregation subscriptions for temperature (moving average)
    for i in range(count):
        # Create random temperature threshold between 15-30 (as integer)
        threshold = int(random.uniform(15, 30))
        
        # Create aggregation subscription
        sub = Subscription(
            id=f"agg_temp_{i}",
            return_topic=RETURN_TOPIC_AGGREGATION,  # Note: return_topic, not return_address
            temp_agg=Aggregatable(
                agregate_type=AggregateType.AVG,
                value=threshold,
                comparator=Comparator.GREATER
            )
        )
        aggregation_subscriptions.append(sub)
    
    metrics.subscriptions_agg = len(aggregation_subscriptions)
    
    # Register aggregation subscriptions
    async with rstream.Producer(
        host="127.0.0.1",  # Use IP address instead of hostname
        port=5552,
        username="user",
        password="password",
    ) as producer:
        await producer.start()
        await producer.create_stream(stream=SUBSCRIPTIONS_STREAM, exists_ok=True)
        
        print(f"Registering {len(aggregation_subscriptions)} aggregation subscriptions...")
        message = pubsub_pb2.SubscriptionMessage()
        message.subscription_type = pubsub_pb2.SubscriptionType.SUBSCRIBE
        for sub in aggregation_subscriptions:
            message.subscriptions.append(sub.to_proto())
            print(f"Adding subscription {sub.id}")
        
        await producer.send(
            stream=SUBSCRIPTIONS_STREAM,
            message=message.SerializeToString(),
        )
    
    return aggregation_subscriptions

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
            print(f"Adding subscription {sub.id}")
        
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
            print(f"Adding subscription {sub.id}")
        
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
                # Create publication
                pub = Publication.random()
                
                # Create protobuf message
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
    with open("test_system_results.md", "w") as f:
        f.write("# Pub/Sub System Evaluation Results\n\n")
        
        f.write("## Test Configuration\n\n")
        f.write(f"- Test field for equality operator comparison: {TEST_FIELD}\n")
        f.write(f"- Evaluation period: {metrics.duration:.2f} seconds\n")
        f.write("- Total subscriptions: {}\n".format(
            metrics.subscriptions_100pct + metrics.subscriptions_25pct + metrics.subscriptions_agg
        ))
        f.write(f"  - 100% equality subscriptions: {metrics.subscriptions_100pct}\n")
        f.write(f"  - 25% equality subscriptions: {metrics.subscriptions_25pct}\n")
        f.write(f"  - Aggregation subscriptions: {metrics.subscriptions_agg}\n")
        f.write(f"- Publications sent: {metrics.publications_sent}\n")
        f.write(f"- Start time: {metrics.start_time}\n")
        f.write(f"- End time: {metrics.end_time}\n")
        
        f.write("\n## Results\n\n")
        
        f.write("### a) Publication Delivery\n\n")
        f.write(f"- Total publications delivered: {metrics.total_publications_delivered}\n")
        f.write(f"- Publications delivered per second: {metrics.publications_per_second:.2f}\n")
        f.write("- Delivery success rate: {:.2f}%\n".format(
            (metrics.total_publications_delivered / metrics.publications_sent * 100)
            if metrics.publications_sent > 0 else 0
        ))
        
        f.write("\n### b) Latency\n\n")
        f.write(f"- Overall average latency: {metrics.avg_latency_ms_total:.2f} ms\n")
        f.write(f"- 100% equality subscriptions latency: {metrics.avg_latency_ms_100pct:.2f} ms\n")
        f.write(f"- 25% equality subscriptions latency: {metrics.avg_latency_ms_25pct:.2f} ms\n")
        f.write(f"- Aggregation subscriptions latency: {metrics.avg_latency_ms_agg:.2f} ms\n")
        
        f.write("\n### c) Matching Rates\n\n")
        
        f.write("#### 100% Equality Operator\n\n")
        f.write(f"- Subscriptions: {metrics.subscriptions_100pct}\n")
        f.write(f"- Matched publications: {metrics.publications_delivered_100pct}\n")
        f.write(f"- Matching rate: {metrics.match_rate_100pct:.2f}%\n")
        
        f.write("\n#### 25% Equality Operator\n\n")
        f.write(f"- Subscriptions: {metrics.subscriptions_25pct}\n")
        f.write(f"- Matched publications: {metrics.publications_delivered_25pct}\n")
        f.write(f"- Matching rate: {metrics.match_rate_25pct:.2f}%\n")
        
        f.write("\n#### Aggregation\n\n")
        f.write(f"- Subscriptions: {metrics.subscriptions_agg}\n")
        f.write(f"- Matched publications: {metrics.publications_delivered_agg}\n")
        f.write(f"- Matching rate: {metrics.match_rate_agg:.2f}%\n")
        
        f.write("\n#### Comparison\n\n")
        f.write(f"- Equality operator ratio (100% vs 25%): {metrics.match_ratio:.2f}x\n")

async def monitor_metrics(duration: int):
    """Monitor and display metrics during test"""
    end_time = time.time() + duration + 10  # Add buffer time
    
    while time.time() < end_time:
        if metrics.end_time:
            print(f"Test complete, processing final messages ({(time.time() - (end_time - duration - 10)):.1f}s / {duration+10}s)")
            
            # Process data from workers
            conn = await aio_pika.connect_robust(
                host="127.0.0.1",
                login="user",
                password="password",
            )
            
            async with conn:
                channel = await conn.channel()
                
                # Get queue stats
                queue_100pct = await channel.declare_queue(RETURN_TOPIC_100_PCT, passive=True)
                queue_25pct = await channel.declare_queue(RETURN_TOPIC_25_PCT, passive=True)
                queue_agg = await channel.declare_queue(RETURN_TOPIC_AGGREGATION, passive=True)
                
                # If no more messages and test is done, exit
                if queue_100pct.declaration_result.message_count == 0 and \
                   queue_25pct.declaration_result.message_count == 0 and \
                   queue_agg.declaration_result.message_count == 0 and \
                   metrics.end_time and time.time() > metrics.end_time.timestamp() + 10:
                    print("All messages processed. Evaluation complete!")
                    break
        else:
            elapsed = time.time() - (end_time - duration - 10)
            print(f"Running test ({elapsed:.1f}s / {duration}s): {metrics.publications_sent} sent, {metrics.total_publications_delivered} delivered")
        
        await asyncio.sleep(5)

async def run_evaluation(
    subscription_count: int,
    duration: int, 
    rate_limit: Optional[int] = None,
    include_aggregation: bool = True
):
    """Run the complete evaluation"""
    # Initialize app state
    appstate = AppState(
        host="127.0.0.1",  # Use IP address instead of hostname
        username="user",
        password="password",
    )
    
    # Start message consumers
    consumer_connection = await setup_message_consumers(appstate)
    
    # Register test subscriptions
    await create_test_subscriptions(appstate, subscription_count)
    
    # Register aggregation subscriptions if requested
    if include_aggregation:
        await create_aggregation_subscriptions(appstate, subscription_count // 5)  # 20% aggregation subs
    
    # Wait for subscriptions to be processed
    print("Waiting for subscriptions to be processed...")
    await asyncio.sleep(5)
    
    # Run monitoring task in the background
    monitor_task = asyncio.create_task(monitor_metrics(duration))
    
    # Publish test data
    await publish_test_data(appstate, duration, rate_limit)
    
    print("Waiting for remaining messages to be processed...")
    await asyncio.sleep(10)  # Wait for any last messages
    
    # Complete monitoring
    await monitor_task
    
    # Close consumer connection
    await consumer_connection.close()
    
    # Write results to file
    write_results()
    
    # Output summary
    print("\nSUMMARY:")
    print(f"- Publications sent: {metrics.publications_sent}")
    print(f"- Publications delivered: {metrics.total_publications_delivered}")
    print(f"- Average latency: {metrics.avg_latency_ms_total:.2f} ms")
    print(f"- Matching rate (100% equality): {metrics.match_rate_100pct:.2f}%")
    print(f"- Matching rate (25% equality): {metrics.match_rate_25pct:.2f}%")
    print(f"- Matching rate (aggregation): {metrics.match_rate_agg:.2f}%")
    print(f"- Ratio: {metrics.match_ratio:.2f}x")
    
    print("\n=== Results Summary ===")
    with open("test_system_results.md", "r") as f:
        print(f.read())

def main():
    parser = argparse.ArgumentParser(description="Evaluate the pub/sub system")
    parser.add_argument("--time", type=int, default=180, help="Duration of test in seconds (default: 180)")
    parser.add_argument("--subs", type=int, default=10000, help="Number of subscriptions to create (default: 10000)")
    parser.add_argument("--rate", type=int, default=50, help="Publication rate limit per second (default: 50)")
    parser.add_argument("--no-agg", action="store_true", help="Disable aggregation subscriptions")
    
    args = parser.parse_args()
    
    try:
        asyncio.run(run_evaluation(
            subscription_count=args.subs,
            duration=args.time,
            rate_limit=args.rate,
            include_aggregation=not args.no_agg
        ))
    except KeyboardInterrupt:
        print("\nEvaluation interrupted.")
        sys.exit(0)

if __name__ == "__main__":
    main()