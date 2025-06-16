from typing import Optional
from common import (
    Comparable,
    Subscription,
    Publication,
    Comparator,
)


class BaseFilter[T]:
    def __init__(self, field: str) -> None:
        self.field = field
        if field not in Subscription.fields():
            raise ValueError(f"Field {field} is not a valid field for Subscription")

    def add_subscription(self, subscription: Subscription) -> None:
        raise NotImplementedError("add_subscription must be implemented in subclasses")

    def remove_subscription(self, subscription: Subscription) -> None:
        raise NotImplementedError(
            "remove_subscription must be implemented in subclasses"
        )

    def match(self, publication: T) -> set[Subscription]:
        raise NotImplementedError("match must be implemented in subclasses")


class AllComparableFilter(BaseFilter[Publication]):
    def __init__(self, field: str) -> None:
        self.field = field
        self.filters = [
            ComparableFilter(field, comparator) for comparator in Comparator
        ]

        self.not_filtering: set[Subscription] = set()

    def add_subscription(self, subscription: Subscription) -> None:
        if getattr(subscription, self.field, None) is None:
            self.not_filtering.add(subscription)
            return
        for f in self.filters:
            f.add_subscription(subscription)

    def remove_subscription(self, subscription: Subscription) -> None:
        if getattr(subscription, self.field, None) is None:
            self.not_filtering.discard(subscription)
            return
        for f in self.filters:
            f.remove_subscription(subscription)

    def match(self, publication: Publication) -> set[Subscription]:
        sets = set()
        for f in self.filters:
            sets = sets.union(f.match(publication))
        sets = sets.union(self.not_filtering)
        return sets


class ComparableFilter[T]:
    def __init__(self, field: str, comparator: Comparator) -> None:
        self.buckets: dict[T, set[Subscription]] = {}
        self.comparator = comparator
        self.field = field
        if field not in Subscription.fields():
            raise ValueError(f"Field {field} is not a valid field for Subscription")

    def add_subscription(self, subscription: Subscription) -> None:
        value: Optional[Comparable[T]] = getattr(subscription, self.field, None)
        if value is None:
            return
        if value.comparator != self.comparator:
            return
        if value.value not in self.buckets:
            self.buckets[value.value] = set()
        self.buckets[value.value].add(subscription)

    def remove_subscription(self, subscription: Subscription) -> None:
        value = getattr(subscription, self.field, None)
        if value is None:
            return
        if value.comparator != self.comparator:
            return
        if value.value not in self.buckets:
            return
        self.buckets[value.value].discard(subscription)
        if not self.buckets[value.value]:
            del self.buckets[value.value]

    def match(self, publication: Publication) -> set[Subscription]:
        value = getattr(publication, self.field, None)
        if value is None:
            return set()
        result: set[Subscription] = set()
        for bucket, subscriptions in self.buckets.items():
            if self.comparator.compare(value, bucket):
                result = result.union(subscriptions)
        return result
