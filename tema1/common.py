import enum
import threading
from typing import Optional, List

from pydantic import BaseModel, Field

from datetime import date as Date, datetime, timedelta
import random
import uuid

import pubsub_pb2 as proto

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
    id: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()))
    stationid: str = Field(...)
    city: City
    temp: int = Field(..., ge=-10, le=40)
    rain: float = Field(..., ge=0, le=1)

    wind: int = Field(..., ge=0, le=20)
    direction: Direction

    date: Date

    @classmethod
    def random(cls):
        stationid = str(uuid.uuid4())
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

    def to_proto(self):
        return proto.Publication(
            id=str(self.id),
            stationid=str(self.stationid),
            city=str(self.city.value) if hasattr(self.city, "value") else str(self.city),
            temp=int(self.temp),
            rain=float(self.rain),
            wind=int(self.wind),
            direction=str(self.direction.value) if hasattr(self.direction, "value") else str(self.direction),
            date=str(self.date)
        )

    @classmethod
    def from_proto(cls, proto_pub):
        return cls(
            id=proto_pub.id,
            stationid=proto_pub.stationid,
            city=proto_pub.city,
            temp=proto_pub.temp,
            rain=proto_pub.rain,
            wind=proto_pub.wind,
            direction=proto_pub.direction,
            date=proto_pub.date
        )
    
    @classmethod
    def parse_str(cls, line: str) -> "Publication":
       
        line = line.strip()[1:-1]
        kwargs = {}
        for part in line.split(";"):
            if not part:
                continue
            key, value = part.strip("()").split(",", 1)
            if key == "stationid":
                kwargs["stationid"] = str(value)
            elif key == "city":
                kwargs["city"] = City(value.strip('"'))
            elif key == "temp":
                kwargs["temp"] = int(value)
            elif key == "rain":
                kwargs["rain"] = float(value)
            elif key == "wind":
                kwargs["wind"] = int(value)
            elif key == "direction":
                kwargs["direction"] = Direction(value.strip('"'))
            elif key == "date":
                # Try to parse the date in both formats: "dd.mm.yyyy" and "yyyy-mm-dd"
                try:
                    kwargs["date"] = datetime.strptime(value, "%d.%m.%Y").date()
                except ValueError:
                    kwargs["date"] = datetime.strptime(value, "%Y-%m-%d").date()
        return cls(**kwargs)

    @classmethod
    def load_from_file(cls, filename: str) -> list["Publication"]:
        pubs = []
        with open(filename, "r") as f:
            for line in f:
                line = line.strip()
                if line:
                    pubs.append(cls.parse_str(line))
        return pubs
    

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
            if (self.count_nonexistants + self.count_existants) * self.existance_ponder > self.count_existants:
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
    id: Optional[str] = Field(default_factory=lambda: str(uuid.uuid4()))
    stationid: Optional[Comparable[str]] = None
    city: Optional[Comparable[City]] = None
    temp: Optional[Comparable[int]] = None
    rain: Optional[Comparable[float]] = None

    wind: Optional[Comparable[int]] = None
    direction: Optional[Comparable[Direction]] = None

    date: Optional[Comparable[Date]] = None

    @classmethod
    def random(cls, ponders: SubscriptionPonders):
        stationid = (
            Comparable[str](
                value=str(uuid.uuid4()),
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

        if not stationid and not city and not temp and not rain and not wind and not direction and not date:
            ponders.stationid.count_nonexistants -= 1
            ponders.stationid.count_existants += 1
            return cls(
                stationid=Comparable[str](
                    value=str(uuid.uuid4()),
                    comparator=ponders.stationid.get_comparator(),
                ),
                city=None,
                temp=None,
                rain=None,
                wind=None,
                direction=None,
                date=None,
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

    def __str__(self):
        fields = []
        for key, value in self.__dict__.items():
            if value is None:
                continue
            if hasattr(value, "comparator") and hasattr(value, "value"):
                fields.append(f"({key},{value.comparator.value},{value.value})")
            else:
                fields.append(f"({key},=,{value})")
        return "{" + ";".join(fields) + "}"
    
    def to_proto(self):
        COMPARATOR_MAP = {
            "=": 0,
            ">": 1,
            ">=": 2,
            "<": 3,
            "<=": 4
        }
        
        sub = proto.Subscription(
            id=self.id
        )
        if self.stationid:
            sub.stationid.value = str(self.stationid.value)
            sub.stationid.comparator = COMPARATOR_MAP[self.stationid.comparator.value]
        if self.city:
            sub.city.value = str(self.city.value) if hasattr(self.city, "value") else str(self.city)
            sub.city.comparator = COMPARATOR_MAP[self.city.comparator.value]
        if self.temp:
            sub.temp.value = self.temp.value
            sub.temp.comparator = COMPARATOR_MAP[self.temp.comparator.value]
        if self.rain:
            sub.rain.value = self.rain.value
            sub.rain.comparator = COMPARATOR_MAP[self.rain.comparator.value]
        if self.wind:
            sub.wind.value = self.wind.value
            sub.wind.comparator = COMPARATOR_MAP[self.wind.comparator.value]
        if self.direction:
            sub.direction.value = str(self.direction.value) if hasattr(self.direction, "value") else str(self.direction)
            sub.direction.comparator = COMPARATOR_MAP[self.direction.comparator.value]
        if self.date:
            if hasattr(self.date.value, "strftime"):
                sub.date.value = self.date.value.strftime("%d.%m.%Y")
            else:
                sub.date.value = str(self.date.value)
            sub.date.comparator = COMPARATOR_MAP[self.date.comparator.value]
        return sub

    @classmethod
    def from_proto(cls, proto_sub):
        COMPARATOR_INV_MAP = {
            0: Comparator.EQUAL,
            1: Comparator.GREATER,
            2: Comparator.GREATER_EQUAL,
            3: Comparator.LESS,
            4: Comparator.LESS_EQUAL
        }
        
        return cls(
        id=proto_sub.id,
        stationid=Comparable[str](
            value=proto_sub.stationid.value,
            comparator=COMPARATOR_INV_MAP[proto_sub.stationid.comparator]
        ) if proto_sub.HasField("stationid") else None,
        city=Comparable[str](
            value=proto_sub.city.value,
            comparator=COMPARATOR_INV_MAP[proto_sub.city.comparator]
        ) if proto_sub.HasField("city") else None,
        temp=Comparable[int](
            value=proto_sub.temp.value,
            comparator=COMPARATOR_INV_MAP[proto_sub.temp.comparator]
        ) if proto_sub.HasField("temp") else None,
        rain=Comparable[float](
            value=proto_sub.rain.value,
            comparator=COMPARATOR_INV_MAP[proto_sub.rain.comparator]
        ) if proto_sub.HasField("rain") else None,
        wind=Comparable[int](
            value=proto_sub.wind.value,
            comparator=COMPARATOR_INV_MAP[proto_sub.wind.comparator]
        ) if proto_sub.HasField("wind") else None,
        direction=Comparable[str](
            value=proto_sub.direction.value,
            comparator=COMPARATOR_INV_MAP[proto_sub.direction.comparator]
        ) if proto_sub.HasField("direction") else None,
        date=Comparable[datetime](
            value=datetime.strptime(proto_sub.date.value, "%d.%m.%Y").date(),
            comparator=COMPARATOR_INV_MAP[proto_sub.date.comparator]
        ) if proto_sub.HasField("date") else None,
    )
    
    @classmethod
    def parse_str(cls, line: str) -> "Subscription":
     
        line = line.strip()[1:-1]
        kwargs = {}
        for part in line.split(";"):
            if not part:
                continue
            key, op, value = part.strip("()").split(",", 2)
            if key == "stationid":
                kwargs["stationid"] = Comparable[str](value=str(value), comparator=Comparator(op))
            elif key == "city":
                value = value.strip('"')  # Remove quotes
                kwargs["city"] = Comparable[City](value=City(value), comparator=Comparator(op))
            elif key == "temp":
                kwargs["temp"] = Comparable[int](value=int(value), comparator=Comparator(op))
            elif key == "rain":
                kwargs["rain"] = Comparable[float](value=float(value), comparator=Comparator(op))
            elif key == "wind":
                kwargs["wind"] = Comparable[int](value=int(value), comparator=Comparator(op))
            elif key == "direction":
                kwargs["direction"] = Comparable[Direction](value=Direction(value), comparator=Comparator(op))
            elif key == "date":
                kwargs["date"] = Comparable[Date](value=datetime.strptime(value, "%Y-%m-%d").date(), comparator=Comparator(op))
        return cls(**kwargs)

    @classmethod
    def load_from_file(cls, filename: str) -> list["Subscription"]:
        subs = []
        with open(filename, "r") as f:
            for line in f:
                line = line.strip()
                if line:
                    subs.append(cls.parse_str(line))
        return subs


class SubscriptionMatcher:
    def __init__(self, subscriptions: List[Subscription], field: str):
        self.subscriptions = subscriptions
        self.field = field 

    def match(self, value) -> list[Subscription]:
        matches = []
        for sub in self.subscriptions:
            comp = getattr(sub, self.field)
            if comp is None:
                matches.append(sub)
            else:
                if self._compare(value, comp.value, comp.comparator):
                    matches.append(sub)
        return matches

    def _compare(self, pub_value, sub_value, comparator: Comparator) -> bool:
        if isinstance(pub_value, (City, Direction)):
            pub_value = str(pub_value.value)
            sub_value = str(sub_value.value)
        if comparator == Comparator.EQUAL:
            return pub_value == sub_value
        if comparator == Comparator.GREATER:
            return pub_value > sub_value
        if comparator == Comparator.GREATER_EQUAL:
            return pub_value >= sub_value
        if comparator == Comparator.LESS:
            return pub_value < sub_value
        if comparator == Comparator.LESS_EQUAL:
            return pub_value <= sub_value
        return False