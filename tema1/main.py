import multiprocessing
import threading

import time
from typing import Callable

from common import ComparablePonder, Publication, Subscription, SubscriptionPonders

PUBLICATIONS_COUNT = 100000
SUBSCRIPTIONS_COUNT = 100000

PROCESSES = 8
THREADS = 1

ponders = SubscriptionPonders(
    stationid=ComparablePonder(equality_ponder=0.7, existance_ponder=0.5),
    city=ComparablePonder(equality_ponder=0.7, existance_ponder=0.5),
    temp=ComparablePonder(equality_ponder=0.7, existance_ponder=0.5),
    rain=ComparablePonder(equality_ponder=0.7, existance_ponder=0.5),
    wind=ComparablePonder(equality_ponder=0.7, existance_ponder=0.5),
    direction=ComparablePonder(equality_ponder=0.7, existance_ponder=0.5),
    date=ComparablePonder(equality_ponder=0.7, existance_ponder=0.5),
)

def generate_publications(count: int):
    start_time = time.time()
    publications = [Publication.random() for _ in range(count)]
    elapsed_time = time.time() - start_time
    print(f"Generated {len(publications)} publications in {elapsed_time} seconds.")
    return publications

def generate_subscriptions(count: int):
    start_time = time.time()
    subscriptions = [Subscription.random(ponders) for _ in range(count)]
    elapsed_time = time.time() - start_time
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
    start_time = time.time()

    pc = PUBLICATIONS_COUNT // PROCESSES
    sc = SUBSCRIPTIONS_COUNT // PROCESSES

    processes = []

    for _ in range(PROCESSES):
        process = multiprocessing.Process(target=generate_threads, args=(generate_publications, pc))
        processes.append(process)
        process.start()
    for _ in range(PROCESSES):
        process = multiprocessing.Process(target=generate_threads, args=(generate_subscriptions, sc))
        processes.append(process)
        process.start()

    for process in processes:
        process.join()

    elapsed_time = time.time() - start_time
    print(f"Generated {PUBLICATIONS_COUNT} publications in {elapsed_time} seconds.")

if __name__ == "__main__":
    main()
