from common import (
    Publication,
    Subscription,
    ComparablePonder,
    SubscriptionPonders,
)
from matching import AllComparableFilter
import time

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


def main():
    subscriptions = generate_subscriptions(10)
    publications = generate_publications(10)

    for subscription in subscriptions:
        print(f"Subscription: {subscription}")
    for publication in publications:
        print(f"Publication: {publication}")

    field = "stationid"

    f = AllComparableFilter(field)
    for subscription in subscriptions:
        f.add_subscription(subscription)
    for publication in publications:
        matched = f.match(publication)
        if not matched:
            continue
        print(f"Matched {len(matched)} subscriptions for publication {publication}")
        for s in matched:
            print(f"Matched subscription: {s}")


if __name__ == "__main__":
    main()
