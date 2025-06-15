from enum import Enum
from typing import Optional, List
from pydantic import BaseModel
from datetime import date as Date

from common import Comparable, Comparator, City, Direction

class AggregationType(str, Enum):
    AVG = "avg"
    MAX = "max"
    MIN = "min"
    SUM = "sum"
    COUNT = "count"

class AggregationField(BaseModel):
    field_name: str
    operation: AggregationType
    value: float
    comparator: Comparator
    
    def __str__(self) -> str:
        return f"({self.operation.value}_{self.field_name},{self.comparator.value},{self.value})"

class ComplexSubscription(BaseModel):
    city: Optional[Comparable[City]] = None
    window_size: int = 10
    aggregation_fields: List[AggregationField] = []
    
    def __str__(self) -> str:
        city_part = []
        if self.city:
            city_part = [f"(city,{self.city.comparator.value},{self.city.value.value})"]
        
        agg_parts = [str(agg) for agg in self.aggregation_fields]
        
        return "{" + ";".join(city_part + agg_parts) + "}"

    @classmethod
    def parse_str(cls, line: str) -> "ComplexSubscription":
        line = line.strip()[1:-1]
        city = None
        aggregation_fields = []
        
        for part in line.split(";"):
            if not part:
                continue
            
            key, op, value = part.strip("()").split(",", 2)
            
            if key == "city":
                city = Comparable[City](value=City(value.strip('"')), comparator=Comparator(op))
            elif key.startswith("avg_") or key.startswith("max_") or key.startswith("min_") or key.startswith("sum_") or key.startswith("count_"):
                op_type, field_name = key.split("_", 1)
                agg_field = AggregationField(
                    field_name=field_name,
                    operation=AggregationType(op_type),
                    value=float(value),
                    comparator=Comparator(op)
                )
                aggregation_fields.append(agg_field)
        
        return cls(city=city, aggregation_fields=aggregation_fields)