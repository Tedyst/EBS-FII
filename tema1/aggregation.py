from typing import Optional
from common import (
    Aggregatable,
    AggregateType,
    Comparable,
    Comparator,
    PublicationWithData,
    Subscription,
)


class AggregationFilter:
    def __init__(self, subscription: Subscription, field: str, window_size: int):
        self.window: list[float] = []
        self.field: Aggregatable = getattr(subscription, field)
        self.field_name = field
        self.window_size = window_size
        self.subscription = subscription

        self._cached_value: Optional[float] = None

    def window_value(self):
        if self._cached_value is not None:
            return self._cached_value
        if self.field.agregate_type == AggregateType.SUM:
            self._cached_value = sum(self.window)
        elif self.field.agregate_type == AggregateType.AVG:
            self._cached_value = (
                sum(self.window) / len(self.window) if self.window else 0
            )
        elif self.field.agregate_type == AggregateType.MIN:
            self._cached_value = min(self.window) if self.window else 0
        elif self.field.agregate_type == AggregateType.MAX:
            self._cached_value = max(self.window) if self.window else 0
        else:
            raise ValueError(f"Unknown aggregation type: {self.field.agregate_type}")
        return self._cached_value

    def matches(self, value):
        self.window.append(value)
        if len(self.window) > self.window_size:
            self.window.pop(0)
        self._cached_value = None
        if len(self.window) < self.window_size:
            return False
        return self.field.comparator.compare(self.window_value(), value)


class Aggregator:
    def __init__(
        self,
        window_size: int = 10,
    ) -> None:
        self.aggregators: dict[
            int, dict[tuple[str, Comparator], AggregationFilter]
        ] = {}
        self.window_size = window_size

    def add_subscription(self, subscription: Subscription) -> None:
        if subscription.id not in self.aggregators:
            self.aggregators[subscription.id] = {}
        for field in subscription.enabled_aggregation_fields():
            value: Aggregatable = getattr(subscription, field)
            self.aggregators[subscription.id][(field, value.comparator)] = (
                AggregationFilter(
                    subscription=subscription,
                    field=field,
                    window_size=self.window_size,
                )
            )

    def remove_subscription(self, subscription: Subscription) -> None:
        self.aggregators.pop(subscription.id, None)

    def match(self, publication: PublicationWithData, subscription: Subscription):
        if subscription.id not in self.aggregators:
            self.add_subscription(subscription)
        filters = self.aggregators[subscription.id]
        matches = True
        for (field, _), f in filters.items():
            real_field = field.replace("_agg", "")
            value: Comparable = getattr(publication, real_field)
            if not f.matches(value):
                matches = False
        return matches
