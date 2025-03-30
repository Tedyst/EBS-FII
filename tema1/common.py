import enum
import threading
from typing import Optional

from pydantic import BaseModel, Field

from datetime import date as Date, datetime, timedelta
import random


class City(enum.Enum):
    BUCHAREST = "Bucharest"
    CLUJ = "Cluj"
    TIMISOARA = "Timisoara"
    IASI = "Iasi"
    CONSTANTA = "Constanta"

    def __str__(self):
        return self.value


class Direction(enum.Enum):
    NE = "NE"
    NW = "NW"
    SE = "SE"
    SW = "SW"

    def __str__(self):
        return self.value


class Publication(BaseModel):
    stationid: int = Field(..., ge=1, le=100)
    city: City
    temp: int = Field(..., ge=-10, le=40)
    rain: float = Field(..., ge=0, le=1)

    wind: int = Field(..., ge=0, le=20)
    direction: Direction

    date: Date

    @classmethod
    def random(cls):
        stationid = random.randint(1, 100)
        city = random.choice(list(City))
        temp = random.randint(-10, 40)
        rain = round(random.uniform(0, 1), 2)
        wind = random.randint(0, 20)
        direction = random.choice(list(Direction))
        date = (datetime(2023, 1, 1) + timedelta(days=random.randint(0, 364))).date()

        return cls(
            stationid=stationid,
            city=city,
            temp=temp,
            rain=rain,
            wind=wind,
            direction=direction,
            date=date,
        )

    def __str__(self):
        return f"{{(stationid,{self.stationid});(city,\"{self.city}\");(temp,{self.temp});(rain,{self.rain});(wind,{self.wind});(direction,\"{self.direction}\");(date,{self.date.strftime('%d.%m.%Y')})}}"


class Comparator(enum.Enum):
    EQUAL = "="
    GREATER = ">"
    GREATER_EQUAL = ">="
    LESS = "<"
    LESS_EQUAL = "<="


class Comparable[T](BaseModel):
    value: T
    comparator: Comparator


lock_comparator = threading.Lock()
lock_existance = threading.Lock()

class ComparablePonder(BaseModel):
    equality_ponder: float = Field(default=1, ge=0, le=1)
    existance_ponder: float = Field(default=0, ge=0, le=1)

    count_equality: int = 0
    count_nonequality: int = 0

    count_nonexistants: int = 0
    count_existants: int = 0

    def get_comparator(self):
        with lock_comparator:
            if (self.count_equality + self.count_nonequality) * self.equality_ponder >= self.count_equality:
                self.count_equality += 1 
                return Comparator.EQUAL
            self.count_nonequality += 1
            return random.choices(
                [
                    Comparator.GREATER,
                    Comparator.GREATER_EQUAL,
                    Comparator.LESS,
                    Comparator.LESS_EQUAL,
                ],
                weights=[
                    (1 - self.equality_ponder) / 4,
                    (1 - self.equality_ponder) / 4,
                    (1 - self.equality_ponder) / 4,
                    (1 - self.equality_ponder) / 4,
                ],
                k=1,
            )[0]

    def should_exist(self):
        with lock_existance:
            if (self.count_nonexistants + self.count_existants) * self.existance_ponder >= self.count_existants:
                self.count_existants += 1
                return True
            self.count_nonexistants += 1
            return False


class SubscriptionPonders(BaseModel):
    stationid: ComparablePonder = ComparablePonder()
    city: ComparablePonder = ComparablePonder()
    temp: ComparablePonder = ComparablePonder()
    rain: ComparablePonder = ComparablePonder()
    wind: ComparablePonder = ComparablePonder()
    direction: ComparablePonder = ComparablePonder()
    date: ComparablePonder = ComparablePonder()


class Subscription(BaseModel):
    stationid: Optional[Comparable[int]] = None
    city: Optional[Comparable[City]] = None
    temp: Optional[Comparable[int]] = None
    rain: Optional[Comparable[float]] = None

    wind: Optional[Comparable[int]] = None
    direction: Optional[Comparable[Direction]] = None

    date: Optional[Comparable[Date]] = None

    @classmethod
    def random(cls, ponders: SubscriptionPonders):
        stationid = (
            Comparable[int](
                value=random.randint(1, 100),
                comparator=ponders.stationid.get_comparator(),
            )
            if ponders.stationid.should_exist()
            else None
        )
        city = (
            Comparable[City](
                value=random.choice(list(City)),
                comparator=ponders.city.get_comparator(),
            )
            if ponders.city.should_exist()
            else None
        )
        temp = (
            Comparable[int](
                value=random.randint(-10, 40),
                comparator=ponders.temp.get_comparator(),
            )
            if ponders.temp.should_exist()
            else None
        )
        rain = (
            Comparable[float](
                value=round(random.uniform(0, 1), 2),
                comparator=ponders.rain.get_comparator(),
            )
            if ponders.rain.should_exist()
            else None
        )
        wind = (
            Comparable[int](
                value=random.randint(0, 20),
                comparator=ponders.wind.get_comparator(),
            )
            if ponders.wind.should_exist()
            else None
        )
        direction = (
            Comparable[Direction](
                value=random.choice(list(Direction)),
                comparator=ponders.direction.get_comparator(),
            )
            if ponders.direction.should_exist()
            else None
        )
        date = (
            Comparable[Date](
                value=(
                    datetime(2023, 1, 1) + timedelta(days=random.randint(0, 364))
                ).date(),
                comparator=ponders.date.get_comparator(),
            )
            if ponders.date.should_exist()
            else None
        )

        return cls(
            stationid=stationid,
            city=city,
            temp=temp,
            rain=rain,
            wind=wind,
            direction=direction,
            date=date,
        )

    def __str__(self) -> str:
        return (
            "{"
            + ";".join(
                [
                    f"({key},{value.comparator.value},{value.value})"
                    for key in self.model_fields
                    if (value := getattr(self, key)) is not None
                ]
            )
            + "}"
        )
