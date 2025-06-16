import unittest
from datetime import date
from common import (
    Comparable,
    Comparator,
    Subscription,
    Publication,
    City,
    Direction,
    PublicationWithData,
)
from matching import AllComparableFilter, ComparableFilter


class TestComparableFilter(unittest.TestCase):
    def setUp(self):
        # Set up a filter for the 'stationid' field with EQUAL comparator
        self.filter = ComparableFilter("stationid", Comparator.EQUAL)
        
        # Create test subscriptions with different stationid values
        self.subscription1 = Subscription(
            id="sub1",
            stationid=Comparable(value=1, comparator=Comparator.EQUAL),
        )
        self.subscription2 = Subscription(
            id="sub2",
            stationid=Comparable(value=2, comparator=Comparator.EQUAL),
        )
        self.subscription3 = Subscription(
            id="sub3",
            stationid=Comparable(value=1, comparator=Comparator.GREATER),  # Different comparator
        )
        
        # Add subscriptions to filter
        self.filter.add_subscription(self.subscription1)
        self.filter.add_subscription(self.subscription2)
        self.filter.add_subscription(self.subscription3)  # Should be ignored due to different comparator

    def test_add_subscription(self):
        # Check if subscriptions were added correctly
        self.assertIn(self.subscription1, self.filter.buckets[1])
        self.assertIn(self.subscription2, self.filter.buckets[2])
        # subscription3 should be ignored because it has a different comparator
        self.assertNotIn(self.subscription3, self.filter.buckets.get(1, set()))
    
    def test_remove_subscription(self):
        # Remove subscription and verify it's gone
        self.filter.remove_subscription(self.subscription1)
        self.assertNotIn(self.subscription1, self.filter.buckets.get(1, set()))
        # Bucket for value 2 should still exist
        self.assertIn(self.subscription2, self.filter.buckets[2])
    
    def test_match(self):
        # Create test publication with stationid=1
        pub = Publication(
            stationid=1,
            city=City.BUCHAREST,
            temp=20,
            rain=0.5,
            wind=5,
            direction=Direction.NE,
            date=date(2023, 6, 15)
        )
        
        # Matching should return only subscription1
        matches = self.filter.match(pub)
        self.assertIn(self.subscription1, matches)
        self.assertNotIn(self.subscription2, matches)
        self.assertNotIn(self.subscription3, matches)


class TestAllComparableFilter(unittest.TestCase):
    def setUp(self):
        # Create a filter for the 'temp' field
        self.filter = AllComparableFilter("temp")
        
        # Create test subscriptions with various temperature comparisons
        self.sub_equal = Subscription(
            id="equal",
            temp=Comparable(value=20, comparator=Comparator.EQUAL)
        )
        self.sub_greater = Subscription(
            id="greater",
            temp=Comparable(value=15, comparator=Comparator.GREATER)
        )
        self.sub_less = Subscription(
            id="less",
            temp=Comparable(value=25, comparator=Comparator.LESS)
        )
        self.sub_no_temp = Subscription(
            id="no_temp",
            stationid=Comparable(value=1, comparator=Comparator.EQUAL)
        )
        
        # Add subscriptions to filter        
        self.filter.add_subscription(self.sub_equal)
        self.filter.add_subscription(self.sub_greater)
        self.filter.add_subscription(self.sub_less)
        self.filter.add_subscription(self.sub_no_temp)
        
    def test_add_and_match_subscription(self):
        # Check if subscription with no temp filter is in not_filtering
        self.assertIn(self.sub_no_temp, self.filter.not_filtering)
        
        # Create test publication
        pub = Publication(
            stationid=1,
            city=City.BUCHAREST,
            temp=20,
            rain=0.5,
            wind=5,
            direction=Direction.NE,
            date=date(2023, 6, 15)
        )
        # Matching should return subscriptions with appropriate filters
        matches = self.filter.match(pub)
        self.assertIn(self.sub_equal, matches)  # temp=20 matches temp=20
        self.assertIn(self.sub_greater, matches)  # temp=20 > temp=15
        self.assertIn(self.sub_no_temp, matches)  # no temp filter always matches
        self.assertIn(self.sub_less, matches)  # For LESS comparator, it checks if pub.temp < sub.value, which is 20 < 25, so it should match
    
    def test_remove_subscription(self):
        # Remove subscription and verify it's gone
        self.filter.remove_subscription(self.sub_no_temp)
        self.assertNotIn(self.sub_no_temp, self.filter.not_filtering)
        
        self.filter.remove_subscription(self.sub_equal)
        
        # Create test publication
        pub = Publication(
            stationid=1,
            city=City.BUCHAREST,
            temp=20,
            rain=0.5,
            wind=5,
            direction=Direction.NE,
            date=date(2023, 6, 15)
        )
        
        # Matching should not include removed subscription
        matches = self.filter.match(pub)
        self.assertNotIn(self.sub_equal, matches)


if __name__ == '__main__':
    unittest.main()
