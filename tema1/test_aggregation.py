import unittest
from datetime import date
from common import (
    Aggregatable,
    AggregateType,
    Comparable,
    Comparator,
    Subscription,
    PublicationWithData,
    City,
    Direction,
)
from aggregation import AggregationFilter, Aggregator


class TestAggregationFilter(unittest.TestCase):
    def setUp(self):
        # Create a subscription with temp_agg that calculates average and checks if it's > 20
        self.subscription = Subscription(
            id="sub1",
            temp_agg=Aggregatable(
                value=20,
                comparator=Comparator.GREATER,
                agregate_type=AggregateType.AVG
            )
        )
        
        # Create aggregation filter with a window size of 3
        self.filter = AggregationFilter(self.subscription, "temp_agg", window_size=3)
    
    def test_window_value_avg(self):
        # Test average aggregation
        self.filter.window = [10, 20, 30]
        self.filter._cached_value = None
        self.assertEqual(self.filter.window_value(), 20)
    
    def test_window_value_sum(self):
        # Set up filter for SUM aggregation
        subscription = Subscription(
            id="sub2",
            temp_agg=Aggregatable(
                value=50,
                comparator=Comparator.GREATER,
                agregate_type=AggregateType.SUM
            )
        )
        filter_sum = AggregationFilter(subscription, "temp_agg", window_size=3)
        filter_sum.window = [10, 20, 30]
        
        self.assertEqual(filter_sum.window_value(), 60)
    
    def test_window_value_min(self):
        # Set up filter for MIN aggregation
        subscription = Subscription(
            id="sub3",
            temp_agg=Aggregatable(
                value=5,
                comparator=Comparator.GREATER,
                agregate_type=AggregateType.MIN
            )
        )
        filter_min = AggregationFilter(subscription, "temp_agg", window_size=3)
        filter_min.window = [10, 5, 30]
        
        self.assertEqual(filter_min.window_value(), 5)
    
    def test_window_value_max(self):
        # Set up filter for MAX aggregation
        subscription = Subscription(
            id="sub4",
            temp_agg=Aggregatable(
                value=25,
                comparator=Comparator.GREATER,
                agregate_type=AggregateType.MAX
            )
        )
        filter_max = AggregationFilter(subscription, "temp_agg", window_size=3)
        filter_max.window = [10, 20, 30]
        
        self.assertEqual(filter_max.window_value(), 30)
    
    def test_matches_incomplete_window(self):
        # Window not filled yet should return False
        self.assertFalse(self.filter.matches(25))
        self.assertFalse(self.filter.matches(30))
        
        # Window now has [25, 30] but needs 3 elements
        self.assertEqual(len(self.filter.window), 2)
    
    def test_matches_complete_window_success(self):
        # Fill window with values that will make the average > 20
        self.filter.matches(15)  # First value
        self.filter.matches(25)  # Second value
        result = self.filter.matches(35)  # Third value, completes window
        
        # Average is (15 + 25 + 35) / 3 = 25, which is > 20
        self.assertTrue(result)
    
    def test_matches_complete_window_failure(self):
        # Fill window with values that will make the average <= 20
        self.filter.matches(10)  # First value
        self.filter.matches(15)  # Second value
        result = self.filter.matches(20)  # Third value, completes window
        
        # Average is (10 + 15 + 20) / 3 = 15, which is not > 20
        self.assertFalse(result)
    
    def test_window_rolling(self):
        # Fill window and roll it
        self.filter.matches(10)
        self.filter.matches(20)
        self.filter.matches(30)  # Window now [10, 20, 30], avg = 20
        
        result = self.filter.matches(60)  # Window becomes [20, 30, 60], avg = 36.67
        
        # New average is > 20
        self.assertTrue(result)
        self.assertEqual(len(self.filter.window), 3)  # Window size remains 3
        self.assertEqual(self.filter.window, [20, 30, 60])  # First value is removed


class TestAggregator(unittest.TestCase):
    def setUp(self):
        # Create an aggregator with window size of 3
        self.aggregator = Aggregator(window_size=3)
        
        # Create subscriptions with aggregation conditions
        self.subscription_temp = Subscription(
            id="temp_sub",
            temp_agg=Aggregatable(
                value=20,
                comparator=Comparator.GREATER,
                agregate_type=AggregateType.AVG
            )
        )
        
        self.subscription_wind = Subscription(
            id="wind_sub",
            wind_agg=Aggregatable(
                value=5,
                comparator=Comparator.GREATER,
                agregate_type=AggregateType.MAX
            )
        )
        
        self.subscription_both = Subscription(
            id="both_sub",
            temp_agg=Aggregatable(
                value=15,
                comparator=Comparator.GREATER,
                agregate_type=AggregateType.AVG
            ),
            wind_agg=Aggregatable(
                value=10,
                comparator=Comparator.LESS,
                agregate_type=AggregateType.MAX
            )
        )
    
    def test_add_subscription(self):
        # Add subscription and check if it's correctly stored
        self.aggregator.add_subscription(self.subscription_temp)
        
        self.assertIn(self.subscription_temp.id, self.aggregator.aggregators)
        self.assertIn(
            ("temp_agg", Comparator.GREATER), 
            self.aggregator.aggregators[self.subscription_temp.id]
        )
    
    def test_remove_subscription(self):
        # Add and then remove subscription
        self.aggregator.add_subscription(self.subscription_temp)
        self.aggregator.remove_subscription(self.subscription_temp)
        
        self.assertNotIn(self.subscription_temp.id, self.aggregator.aggregators)
    
    def test_match_single_field(self):
        # Add subscription and test matching with publications
        self.aggregator.add_subscription(self.subscription_temp)
        
        # Create publications
        pub1 = PublicationWithData(
            stationid=1,
            city=City.BUCHAREST,
            temp=25,  # Higher temp
            rain=0,
            wind=5,
            direction=Direction.NE,
            date=date(2023, 6, 15)
        )
        
        # First publication, not enough for window
        self.assertFalse(self.aggregator.match(pub1, self.subscription_temp))
        
        pub2 = PublicationWithData(
            stationid=1,
            city=City.BUCHAREST,
            temp=30,  # Higher temp
            rain=0,
            wind=5,
            direction=Direction.NE,
            date=date(2023, 6, 16)
        )
        
        # Second publication, not enough for window
        self.assertFalse(self.aggregator.match(pub2, self.subscription_temp))
        
        pub3 = PublicationWithData(
            stationid=1,
            city=City.BUCHAREST,
            temp=25,  # Higher temp
            rain=0,
            wind=5,
            direction=Direction.NE,
            date=date(2023, 6, 17)
        )
        
        # Third publication completes window with avg of (25+30+25)/3 = 26.67 > 20
        self.assertTrue(self.aggregator.match(pub3, self.subscription_temp))
    
    def test_match_multiple_fields(self):
        # Test subscription with multiple aggregation conditions
        self.aggregator.add_subscription(self.subscription_both)
        
        # Fill the window with 3 publications
        for i in range(3):
            pub = PublicationWithData(
                stationid=1,
                city=City.BUCHAREST,
                temp=20,  # Average will be > 15
                rain=0,
                wind=8,  # Max will be < 10
                direction=Direction.NE,
                date=date(2023, 6, 15 + i)
            )
            if i < 2:
                # First two won't match because window not full
                self.assertFalse(self.aggregator.match(pub, self.subscription_both))
            else:
                # Third publication completes window
                self.assertTrue(self.aggregator.match(pub, self.subscription_both))
        
        # Now add a publication that violates the wind condition
        pub_fail = PublicationWithData(
            stationid=1,
            city=City.BUCHAREST,
            temp=20,  # Still good for temp avg
            rain=0,
            wind=12,  # Now max is 12 which is not < 10
            direction=Direction.NE,
            date=date(2023, 6, 18)
        )
        
        # Should not match due to wind condition
        self.assertFalse(self.aggregator.match(pub_fail, self.subscription_both))


if __name__ == '__main__':
    unittest.main()
