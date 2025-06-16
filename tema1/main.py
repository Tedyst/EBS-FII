import multiprocessing
import threading
import os

import time
from typing import Callable

from common import ComparablePonder, Publication, Subscription, SubscriptionPonders


PUBLICATIONS_COUNT = int(os.getenv("PUBLICATIONS_COUNT", 100))
SUBSCRIPTIONS_COUNT = int(os.getenv("SUBSCRIPTIONS_COUNT", 100))
PROCESSES = int(os.getenv("PROCESSES", 4))
THREADS = int(os.getenv("THREADS", 4))


ponders = SubscriptionPonders(
    stationid=ComparablePonder(
        equality_ponder=0.6121335763499347, existance_ponder=0.5292710042118085
    ),
    city=ComparablePonder(equality_ponder=1, existance_ponder=0.8127223672318329),
    temp=ComparablePonder(
        equality_ponder=0.6018724372232028, existance_ponder=0.5770973878067571
    ),
    rain=ComparablePonder(
        equality_ponder=0.01188073999266237, existance_ponder=0.7010314666467584
    ),
    wind=ComparablePonder(
        equality_ponder=0.7221635296656853, existance_ponder=0.6216120497616565
    ),
    direction=ComparablePonder(equality_ponder=1, existance_ponder=0.1065752163739988),
    date=ComparablePonder(
        equality_ponder=0.9824093178815014, existance_ponder=0.21008443873019977
    ),
    rain_agg=ComparablePonder(equality_ponder=0.12, existance_ponder=0.23454),
    wind_agg=ComparablePonder(equality_ponder=0.234, existance_ponder=0.324324),
    temp_agg=ComparablePonder(equality_ponder=0.324, existance_ponder=0.6),
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
    for i in range(THREADS):
        tc = count // THREADS
        if i == 0:
            tc = count - (count // THREADS) * (THREADS - 1)
        thread = threading.Thread(target=function, args=(tc,))
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
            ppc = PUBLICATIONS_COUNT - (PUBLICATIONS_COUNT // PROCESSES) * (
                PROCESSES - 1
            )
        process = multiprocessing.Process(
            target=generate_threads, args=(generate_publications, ppc)
        )
        processes.append(process)
        process.start()
    for i in range(PROCESSES):
        psc = sc
        if i == PROCESSES - 1:
            psc = SUBSCRIPTIONS_COUNT - (SUBSCRIPTIONS_COUNT // PROCESSES) * (
                PROCESSES - 1
            )
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


if __name__ == "__main__":
    main()
