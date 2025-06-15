from collections import defaultdict, deque
from typing import Dict, List, Deque, Any, Set, Tuple
import statistics
from datetime import datetime

from common import Publication, City
from complex_subscription import ComplexSubscription, AggregationType, Comparator

class WindowProcessor:
    def __init__(self, window_size: int = 10):
        self.window_size = window_size
        # Dictionary mapping city to its publication window
        self.city_windows: Dict[City, Deque[Publication]] = defaultdict(lambda: deque(maxlen=window_size))
        # Dictionary to track window completions
        self.window_counts: Dict[City, int] = defaultdict(int)
    
    def add_publication(self, publication: Publication) -> Tuple[bool, City, Dict[str, Any]]:
        """
        Adds a publication to the appropriate window.
        Returns (is_window_complete, city, aggregations)
        """
        city = publication.city
        window = self.city_windows[city]
        window.append(publication)
        
        # If we have a full window, calculate aggregations and notify
        if len(window) == self.window_size:
            aggregations = self._calculate_aggregations(window)
            self.window_counts[city] += 1
            # For tumbling window behavior, clear the window after processing
            self.city_windows[city] = deque(maxlen=self.window_size)
            return True, city, aggregations
        
        return False, city, {}
    
    def _calculate_aggregations(self, window: Deque[Publication]) -> Dict[str, Any]:
        """Calculate all possible aggregations for a window of publications"""
        result = {}
        
        # Temperature aggregations
        temps = [pub.temp for pub in window if pub.temp is not None]
        if temps:
            result["avg_temp"] = sum(temps) / len(temps)
            result["max_temp"] = max(temps)
            result["min_temp"] = min(temps)
        
        # Wind aggregations
        winds = [pub.wind for pub in window if pub.wind is not None]
        if winds:
            result["avg_wind"] = sum(winds) / len(winds)
            result["max_wind"] = max(winds)
            result["min_wind"] = min(winds)
        
        # Rain aggregations
        rains = [pub.rain for pub in window if pub.rain is not None]
        if rains:
            result["avg_rain"] = sum(rains) / len(rains)
            result["max_rain"] = max(rains)
            result["min_rain"] = min(rains)
        
        # Add timestamp for measuring latency later
        result["window_complete_time"] = datetime.now().timestamp()
        
        return result
    
    def match_complex_subscriptions(self, complex_subs: List[ComplexSubscription], 
                                   city: City, aggregations: Dict[str, Any]) -> List[ComplexSubscription]:
        """Find all complex subscriptions that match the aggregations"""
        matching_subs = []
        
        for sub in complex_subs:
            # Check city filter if present
            if sub.city and city != sub.city.value:
                continue
                
            # Check all aggregation fields
            all_match = True
            for agg_field in sub.aggregation_fields:
                field_key = f"{agg_field.operation.value}_{agg_field.field_name}"
                
                if field_key not in aggregations:
                    all_match = False
                    break
                
                # Compare aggregated value with subscription condition
                if not self._compare_values(aggregations[field_key], 
                                           agg_field.value, 
                                           agg_field.comparator):
                    all_match = False
                    break
            
            if all_match:
                matching_subs.append(sub)
                
        return matching_subs
    
    def _compare_values(self, actual_value, expected_value, comparator):
        if comparator == Comparator.EQUAL:
            return actual_value == expected_value
        elif comparator == Comparator.GREATER:
            return actual_value > expected_value
        elif comparator == Comparator.GREATER_EQUAL:
            return actual_value >= expected_value
        elif comparator == Comparator.LESS:
            return actual_value < expected_value
        elif comparator == Comparator.LESS_EQUAL:
            return actual_value <= expected_value
        return False