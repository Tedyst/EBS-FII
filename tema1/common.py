import enum
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


class ComparablePonder(BaseModel):
    equality_ponder: float = Field(default=1, ge=0, le=1)
    existance_ponder: float = Field(default=0, ge=0, le=1)

    def get_comparator(self):
        return random.choices(
            [
                Comparator.EQUAL,
                Comparator.GREATER,
                Comparator.GREATER_EQUAL,
                Comparator.LESS,
                Comparator.LESS_EQUAL,
            ],
            weights=[
                self.equality_ponder,
                (1 - self.equality_ponder) / 3,
                (1 - self.equality_ponder) / 3,
                (1 - self.equality_ponder) / 3,
                (1 - self.equality_ponder) / 3,
            ],
            k=1,
        )[0]


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
            if random.random() < ponders.stationid.existance_ponder
            else None
        )
        city = (
            Comparable[City](
                value=random.choice(list(City)),
                comparator=ponders.city.get_comparator(),
            )
            if random.random() < ponders.city.existance_ponder
            else None
        )
        temp = (
            Comparable[int](
                value=random.randint(-10, 40),
                comparator=ponders.temp.get_comparator(),
            )
            if random.random() < ponders.temp.existance_ponder
            else None
        )
        rain = (
            Comparable[float](
                value=round(random.uniform(0, 1), 2),
                comparator=ponders.rain.get_comparator(),
            )
            if random.random() < ponders.rain.existance_ponder
            else None
        )
        wind = (
            Comparable[int](
                value=random.randint(0, 20),
                comparator=ponders.wind.get_comparator(),
            )
            if random.random() < ponders.wind.existance_ponder
            else None
        )
        direction = (
            Comparable[Direction](
                value=random.choice(list(Direction)),
                comparator=ponders.direction.get_comparator(),
            )
            if random.random() < ponders.direction.existance_ponder
            else None
        )
        date = (
            Comparable[Date](
                value=(
                    datetime(2023, 1, 1) + timedelta(days=random.randint(0, 364))
                ).date(),
                comparator=ponders.date.get_comparator(),
            )
            if random.random() < ponders.date.existance_ponder
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
