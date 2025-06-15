import multiprocessing
import threading
import os
from datetime import datetime

import time
from typing import Callable

from common import ComparablePonder, Publication, Subscription, SubscriptionPonders, SubscriptionMatcher, Comparable, Comparator, City
import common

import pubsub_pb2 as proto
import uuid

PUBLICATIONS_COUNT = int(os.getenv("PUBLICATIONS_COUNT", 100))
SUBSCRIPTIONS_COUNT = int(os.getenv("SUBSCRIPTIONS_COUNT", 10000))
PROCESSES = int(os.getenv("PROCESSES", 1))
THREADS = int(os.getenv("THREADS", 1))


ponders = SubscriptionPonders(
    stationid=ComparablePonder(equality_ponder=0.6121335763499347, existance_ponder=0.5292710042118085),
    city=ComparablePonder(equality_ponder=0.3463345451866571, existance_ponder=0.8127223672318329),
    temp=ComparablePonder(equality_ponder=0.6018724372232028, existance_ponder=0.5770973878067571),
    rain=ComparablePonder(equality_ponder=0.01188073999266237, existance_ponder=0.7010314666467584),
    wind=ComparablePonder(equality_ponder=0.7221635296656853, existance_ponder=0.6216120497616565),
    direction=ComparablePonder(equality_ponder=0.43111820367966425, existance_ponder=0.1065752163739988),
    date=ComparablePonder(equality_ponder=0.9824093178815014, existance_ponder=0.21008443873019977),
)


def generate_publications(count: int):
    t = time.time()
    publications = [Publication.random() for _ in range(count)]
    with open("publications.txt", "a+") as f:
        for publication in publications:
            f.write(f"{publication}\n")
    elapsed_time = time.time() - t
    print(f"Generated {len(publications)} publications in {elapsed_time} seconds.")
    return publications


def generate_subscriptions(count: int):
    t = time.time()
    subscriptions = [Subscription.random(ponders) for _ in range(count)]
    with open("subscriptions.txt", "a+") as f:
        for subscription in subscriptions:
            f.write(f"{subscription}\n")
    elapsed_time = time.time() - t
    print(f"Generated {len(subscriptions)} subscriptions in {elapsed_time} seconds.")
    return subscriptions


def generate_threads(function: Callable, count: int):
    threads = []
    for _ in range(THREADS):
        thread = threading.Thread(target=function, args=(count // THREADS,))
        threads.append(thread)
        thread.start()
    for thread in threads:
        thread.join()


def main():
    if os.path.exists("publications.txt"):
        os.remove("publications.txt")
    if os.path.exists("subscriptions.txt"):
        os.remove("subscriptions.txt")

    start_time = time.time()

    pc = PUBLICATIONS_COUNT // PROCESSES
    sc = SUBSCRIPTIONS_COUNT // PROCESSES

    processes = []

    for i in range(PROCESSES):
        ppc = pc
        if i == PROCESSES - 1:
            ppc = PUBLICATIONS_COUNT - (PUBLICATIONS_COUNT // PROCESSES) * (PROCESSES - 1)
        process = multiprocessing.Process(
            target=generate_threads, args=(generate_publications, ppc)
        )
        processes.append(process)
        process.start()
    for i in range(PROCESSES):
        psc = sc
        if i == PROCESSES - 1:
            psc = SUBSCRIPTIONS_COUNT - (SUBSCRIPTIONS_COUNT // PROCESSES) * (PROCESSES - 1)
        process = multiprocessing.Process(
            target=generate_threads, args=(generate_subscriptions, psc)
        )
        processes.append(process)
        process.start()

    for process in processes:
        process.join()

    elapsed_time = time.time() - start_time
    print(
        f"Generated {PUBLICATIONS_COUNT} publications and {SUBSCRIPTIONS_COUNT} subscriptions in {elapsed_time} seconds."
    )

def test_matcher():
    subscriptions=Subscription.load_from_file("../../subscriptions.txt")
    # publications = Publication.load_from_file("publications.txt")

    matcher_city = SubscriptionMatcher(subscriptions, field="city")
    matches_city = matcher_city.match(common.City.BUCHAREST)
    print(f"Matches for city Bucharest: {len(matches_city)}")

def test_proto_pubsub():
  
    pub_py = Publication(
        id=str(uuid.uuid4()),
        stationid="1",
        city="Bucharest",
        temp=25,
        rain=0.1,
        wind=10,
        direction="NE",
        date="2023-06-15"
    )
    sub_py = Subscription(
        id=str(uuid.uuid4()),
        stationid=Comparable[str](value=str(uuid.uuid4()), comparator=Comparator.GREATER_EQUAL),
        city=Comparable[str](value="Bucharest", comparator=Comparator.EQUAL),
        temp=Comparable[int](value=25, comparator=Comparator.GREATER),
        rain=Comparable[float](value=0.2, comparator=Comparator.LESS_EQUAL),
        wind=Comparable[int](value=10, comparator=Comparator.LESS),
        direction=Comparable[str](value="NE", comparator=Comparator.EQUAL),
        date=Comparable[datetime](value=datetime(2023, 6, 15), comparator=Comparator.EQUAL)
    )

    # Conversie la protobuf
    pub_proto = pub_py.to_proto()
    sub_proto = sub_py.to_proto()

    # Serializare
    pub_bytes = pub_proto.SerializeToString()
    sub_bytes = sub_proto.SerializeToString()

    # Deserializare
    pub_proto2 = proto.Publication()
    pub_proto2.ParseFromString(pub_bytes)
    sub_proto2 = proto.Subscription()
    sub_proto2.ParseFromString(sub_bytes)

    # Conversie inapoi la clasele Python
    pub_py2 = Publication.from_proto(pub_proto2)
    sub_py2 = Subscription.from_proto(sub_proto2)


    print("Publication original:", pub_py)
    print("\nPublication proto:", pub_proto2)
    print("\nPublication final:", pub_py2)

    print("\nSubscription original:", sub_py)
    print("\nSubscription proto:", sub_proto2)
    print("\nSubscription final:", sub_py2)

if __name__ == "__main__":
    # main()
    test_proto_pubsub()
    # test_matcher()
