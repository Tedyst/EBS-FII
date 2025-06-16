from dataclasses import dataclass
import enum
import multiprocessing
from multiprocessing.sharedctypes import Synchronized
import uuid
import pubsub_pb2
from typing import Callable, Optional

from pydantic import BaseModel, Field

from datetime import date as Date, datetime, timedelta
import random

SUBSCRIPTIONS_STREAM = "SUBSCRIPTIONS"
AGGREGATION_STREAM = "AGGREGATION"


class AppState:
    def __init__(
        self,
        host: str,
        username: str,
        password: str,
    ) -> None:
        self.username = username
        self.password = password
        self.host = host


class City(enum.Enum):
    BUCHAREST = "Bucharest"
    CLUJ = "Cluj"
    TIMISOARA = "Timisoara"
    IASI = "Iasi"
    CONSTANTA = "Constanta"

    @classmethod
    def from_index(cls, index: int):
        if index == 0:
            return cls.BUCHAREST
        elif index == 1:
            return cls.CLUJ
        elif index == 2:
            return cls.TIMISOARA
        elif index == 3:
            return cls.IASI
        elif index == 4:
            return cls.CONSTANTA
        else:
            raise ValueError(f"Unknown city index: {index}")

    def __str__(self):
        return self.value


class Direction(enum.Enum):
    NE = "NE"
    NW = "NW"
    SE = "SE"
    SW = "SW"

    @classmethod
    def from_index(cls, index: int):
        if index == 0:
            return cls.NE
        elif index == 1:
            return cls.NW
        elif index == 2:
            return cls.SE
        elif index == 3:
            return cls.SW
        else:
            raise ValueError(f"Unknown direction index: {index}")

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
    def fields(cls):
        return [
            "stationid",
            "city",
            "temp",
            "rain",
            "wind",
            "direction",
            "date",
        ]

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
        return f'{{(stationid,{self.stationid});(city,"{self.city}");(temp,{self.temp});(rain,{self.rain});(wind,{self.wind});(direction,"{self.direction}");(date,{self.date.strftime("%d.%m.%Y")})}}'


class PublicationWithData(Publication):
    parsed_fields: list[str] = Field(default_factory=list)
    remaining_subscriptions: list[str] = Field(default_factory=list)
    all_subscriptions: bool = Field(default=False)

    @classmethod
    def random(cls):
        obj = super().random()
        obj.all_subscriptions = True
        return obj

    def remaining_filter_fields(self):
        return [
            field
            for field in self.fields()
            if field not in self.parsed_fields
            and getattr(self, field, None) is not None
        ]

    def to_proto(self, without_metadata=False):
        p = pubsub_pb2.Publication()
        p.stationid = self.stationid
        p.city = pubsub_pb2.City.Value(self.city.name)
        p.temp = self.temp
        p.rain = self.rain
        p.wind = self.wind
        p.direction = pubsub_pb2.Direction.Value(self.direction.name)
        p.date = self.date.strftime("%Y-%m-%d")
        if without_metadata:
            return p
        p.parsed_fields.extend(self.parsed_fields)
        p.remaining_subscriptions.extend(self.remaining_subscriptions)
        p.all_subscriptions = self.all_subscriptions
        return p

    @classmethod
    def from_proto(cls, proto_pub: pubsub_pb2.Publication):
        return cls(
            stationid=proto_pub.stationid,
            city=City.from_index(proto_pub.city),
            temp=proto_pub.temp,
            rain=proto_pub.rain,
            wind=proto_pub.wind,
            direction=Direction.from_index(proto_pub.direction),
            date=datetime.strptime(proto_pub.date, "%Y-%m-%d").date(),
            parsed_fields=list(proto_pub.parsed_fields),
            remaining_subscriptions=list(proto_pub.remaining_subscriptions),
            all_subscriptions=proto_pub.all_subscriptions,
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

    @classmethod
    def from_index(cls, index: int):
        if index == 0:
            return cls.EQUAL
        elif index == 1:
            return cls.GREATER
        elif index == 2:
            return cls.GREATER_EQUAL
        elif index == 3:
            return cls.LESS
        elif index == 4:
            return cls.LESS_EQUAL
        else:
            raise ValueError(f"Unknown comparator index: {index}")

    def compare(self, a, b):
        if self == Comparator.EQUAL:
            return a == b
        elif self == Comparator.GREATER:
            return a > b
        elif self == Comparator.GREATER_EQUAL:
            return a >= b
        elif self == Comparator.LESS:
            return a < b
        elif self == Comparator.LESS_EQUAL:
            return a <= b
        else:
            raise ValueError(f"Unknown comparator: {self}")


class Comparable[T](BaseModel):
    value: T
    comparator: Comparator

    class Config:
        frozen = True

    def matches(self, other: T) -> bool:
        if isinstance(other, Comparable):
            return self.comparator.compare(self.value, other.value)
        return self.comparator.compare(self.value, other)


class AggregateType(enum.Enum):
    SUM = "SUM"
    AVG = "AVG"
    MIN = "MIN"
    MAX = "MAX"

    @classmethod
    def from_index(cls, index: int):
        if index == 0:
            return cls.SUM
        elif index == 1:
            return cls.AVG
        elif index == 2:
            return cls.MIN
        elif index == 3:
            return cls.MAX
        else:
            raise ValueError(f"Unknown aggregate type index: {index}")

    def __str__(self):
        return self.value


class Aggregatable[T](BaseModel):
    value: T
    comparator: Comparator
    agregate_type: AggregateType

    class Config:
        frozen = True

    def __str__(self):
        return f"({self.comparator.value},{self.value},{self.agregate_type})"


lock_comparator = multiprocessing.Lock()
lock_existance = multiprocessing.Lock()


class ComparablePonder:
    def __init__(
        self,
        equality_ponder: float = 1,
        existance_ponder: float = 0,
    ):
        self.equality_ponder = equality_ponder
        self.existance_ponder = existance_ponder
        self.count_equality: "Synchronized[int]" = multiprocessing.Value(
            "i", 0, lock=False
        )
        self.count_nonequality: "Synchronized[int]" = multiprocessing.Value(
            "i", 0, lock=False
        )
        self.count_nonexistants: "Synchronized[int]" = multiprocessing.Value(
            "i", 0, lock=False
        )
        self.count_existants: "Synchronized[int]" = multiprocessing.Value(
            "i", 0, lock=False
        )

    def get_comparator(self):
        with lock_comparator:
            if (
                self.count_equality.value + self.count_nonequality.value
            ) * self.equality_ponder >= self.count_equality.value:
                self.count_equality.value += 1
                return Comparator.EQUAL
            self.count_nonequality.value += 1
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
            if (
                self.count_nonexistants.value + self.count_existants.value
            ) * self.existance_ponder > self.count_existants.value:
                self.count_existants.value += 1
                return True
            self.count_nonexistants.value += 1
            return False

    def __str__(self):
        return f"({self.equality_ponder=},{self.existance_ponder=},{self.count_equality.value=},{self.count_nonequality.value=},{self.count_existants.value=},{self.count_nonexistants.value=})"


@dataclass
class SubscriptionPonders:
    stationid: ComparablePonder = ComparablePonder()
    city: ComparablePonder = ComparablePonder()
    temp: ComparablePonder = ComparablePonder()
    rain: ComparablePonder = ComparablePonder()
    wind: ComparablePonder = ComparablePonder()
    direction: ComparablePonder = ComparablePonder()
    date: ComparablePonder = ComparablePonder()

    temp_agg: ComparablePonder = ComparablePonder()
    rain_agg: ComparablePonder = ComparablePonder()
    wind_agg: ComparablePonder = ComparablePonder()


class Subscription(BaseModel):
    id: str

    stationid: Optional[Comparable[int]] = None
    city: Optional[Comparable[City]] = None
    temp: Optional[Comparable[int]] = None
    rain: Optional[Comparable[float]] = None

    wind: Optional[Comparable[int]] = None
    direction: Optional[Comparable[Direction]] = None

    date: Optional[Comparable[Date]] = None

    temp_agg: Optional[Aggregatable[int]] = None
    rain_agg: Optional[Aggregatable[float]] = None
    wind_agg: Optional[Aggregatable[int]] = None

    return_topic: Optional[str] = None

    class Config:
        frozen = True

    @classmethod
    def random_stationid(cls):
        return random.randint(1, 100)

    @classmethod
    def random_city(cls):
        return random.choice(list(City))

    @classmethod
    def random_temp(cls):
        return random.randint(-10, 40)

    @classmethod
    def random_rain(cls):
        return round(random.uniform(0, 1), 2)

    @classmethod
    def random_wind(cls):
        return random.randint(0, 20)

    @classmethod
    def random_direction(cls):
        return random.choice(list(Direction))

    @classmethod
    def random_date(cls):
        return (datetime(2023, 1, 1) + timedelta(days=random.randint(0, 364))).date()

    @classmethod
    def fields(cls):
        return [
            "stationid",
            "city",
            "temp",
            "rain",
            "wind",
            "direction",
            "date",
        ]

    @classmethod
    def agg_fields(cls):
        return [
            "temp_agg",
            "rain_agg",
            "wind_agg",
        ]

    @classmethod
    def _random_comparable_field(
        cls, ponders: SubscriptionPonders, field_name: str, force=False
    ):
        if field_name not in cls.fields():
            return None
        random_function: Optional[Callable] = getattr(cls, "random_" + field_name, None)
        if random_function is None:
            return None
        if not force and not getattr(ponders, field_name).should_exist():
            return None
        return Comparable(
            value=random_function(),
            comparator=getattr(ponders, field_name).get_comparator(),
        )

    @classmethod
    def _random_aggregatable_field(
        cls, ponders: SubscriptionPonders, field_name: str, force=False
    ):
        if field_name not in cls.agg_fields():
            return None
        random_function: Optional[Callable] = getattr(
            cls, "random_" + field_name.replace("_agg", ""), None
        )
        if random_function is None:
            return None
        if not force and not getattr(ponders, field_name).should_exist():
            return None
        return Aggregatable(
            value=random_function(),
            comparator=getattr(ponders, field_name).get_comparator(),
            agregate_type=random.choice(list(AggregateType)),
        )

    @classmethod
    def random(cls, ponders: SubscriptionPonders, return_topic: Optional[str] = None):
        fields = {}
        fields["id"] = str(uuid.uuid4())
        empty = True
        for field_name in cls.fields():
            fields[field_name] = cls._random_comparable_field(ponders, field_name)
            if fields[field_name] is not None:
                empty = False
        for field_name in cls.agg_fields():
            fields[field_name] = cls._random_aggregatable_field(ponders, field_name)
        if empty:
            field = random.choice(cls.fields())
            p: Optional[ComparablePonder] = getattr(ponders, field, None)
            if not p:
                raise ValueError(f"Field {field} not found in ponders")
            with lock_existance:
                p.count_nonexistants.value -= 1
                p.count_existants.value += 1
            fields[field] = cls._random_comparable_field(ponders, field, True)
        fields["return_topic"] = return_topic
        return cls(**fields)

    def enabled_aggregation_fields(self):
        f = []
        for field_name in self.agg_fields():
            if getattr(self, field_name) is not None:
                f.append(field_name)
        return f

    def to_proto(self):
        sub = pubsub_pb2.Subscription(id=self.id)
        if self.stationid:
            sub.stationid = self.stationid.value
            sub.stationid_comparator = pubsub_pb2.Comparator.Value(
                self.stationid.comparator.name
            )
        if self.city:
            sub.city = pubsub_pb2.City.Value(self.city.value.name)
            sub.city_comparator = pubsub_pb2.Comparator.Value(self.city.comparator.name)
        if self.temp:
            sub.temp = self.temp.value
            sub.temp_comparator = pubsub_pb2.Comparator.Value(self.temp.comparator.name)
        if self.rain:
            sub.rain = self.rain.value
            sub.rain_comparator = pubsub_pb2.Comparator.Value(self.rain.comparator.name)
        if self.wind:
            sub.wind = self.wind.value
            sub.wind_comparator = pubsub_pb2.Comparator.Value(self.wind.comparator.name)
        if self.direction:
            sub.direction = pubsub_pb2.Direction.Value(self.direction.value.name)
            sub.direction_comparator = pubsub_pb2.Comparator.Value(
                self.direction.comparator.name
            )
        if self.date:
            sub.date = self.date.value.strftime("%Y-%m-%d")
            sub.date_comparator = pubsub_pb2.Comparator.Value(self.date.comparator.name)
        if self.temp_agg:
            sub.temp_agg = self.temp_agg.value
            sub.temp_agg_comparator = pubsub_pb2.Comparator.Value(
                self.temp_agg.comparator.name
            )
            sub.temp_agg_type = pubsub_pb2.AggregateType.Value(
                self.temp_agg.agregate_type.name
            )
        if self.rain_agg:
            sub.rain_agg = self.rain_agg.value
            sub.rain_agg_comparator = pubsub_pb2.Comparator.Value(
                self.rain_agg.comparator.name
            )
            sub.rain_agg_type = pubsub_pb2.AggregateType.Value(
                self.rain_agg.agregate_type.name
            )
        if self.wind_agg:
            sub.wind_agg = self.wind_agg.value
            sub.wind_agg_comparator = pubsub_pb2.Comparator.Value(
                self.wind_agg.comparator.name
            )
            sub.wind_agg_type = pubsub_pb2.AggregateType.Value(
                self.wind_agg.agregate_type.name
            )
        if self.return_topic:
            sub.return_topic = self.return_topic
        return sub

    @classmethod
    def from_proto(cls, s: pubsub_pb2.Subscription):
        fields = {}
        fields["id"] = s.id
        if s.HasField("stationid"):
            fields["stationid"] = Comparable(
                value=s.stationid,
                comparator=Comparator.from_index(int(s.stationid_comparator)),
            )
        if s.HasField("city"):
            fields["city"] = Comparable(
                value=City.from_index(int(s.city)),
                comparator=Comparator.from_index(int(s.city_comparator)),
            )
        if s.HasField("temp"):
            fields["temp"] = Comparable(
                value=s.temp,
                comparator=Comparator.from_index(int(s.temp_comparator)),
            )
        if s.HasField("rain"):
            fields["rain"] = Comparable(
                value=s.rain,
                comparator=Comparator.from_index(int(s.rain_comparator)),
            )
        if s.HasField("wind"):
            fields["wind"] = Comparable(
                value=s.wind,
                comparator=Comparator.from_index(int(s.wind_comparator)),
            )
        if s.HasField("direction"):
            fields["direction"] = Comparable(
                value=Direction.from_index(int(s.direction)),
                comparator=Comparator.from_index(int(s.direction_comparator)),
            )
        if s.HasField("date"):
            fields["date"] = Comparable(
                value=datetime.strptime(s.date, "%Y-%m-%d").date(),
                comparator=Comparator.from_index(int(s.date_comparator)),
            )
        if s.HasField("temp_agg"):
            fields["temp_agg"] = Aggregatable(
                value=s.temp_agg,
                comparator=Comparator.from_index(int(s.temp_agg_comparator)),
                agregate_type=AggregateType.from_index(int(s.temp_agg_type)),
            )
        if s.HasField("rain_agg"):
            fields["rain_agg"] = Aggregatable(
                value=s.rain_agg,
                comparator=Comparator.from_index(int(s.rain_agg_comparator)),
                agregate_type=AggregateType.from_index(int(s.rain_agg_type)),
            )
        if s.HasField("wind_agg"):
            fields["wind_agg"] = Aggregatable(
                value=s.wind_agg,
                comparator=Comparator.from_index(int(s.wind_agg_comparator)),
                agregate_type=AggregateType.from_index(int(s.wind_agg_type)),
            )
        fields["return_topic"] = s.return_topic
        return cls(**fields)

    def __str__(self) -> str:
        return (
            f"id={self.id},"
            "{"
            + ";".join(
                [
                    f"({key},{value.comparator.value},{value.value})"
                    for key in self.fields()
                    if (value := getattr(self, key)) is not None
                ]
                + [
                    f"({key.replace('_agg', '')}_{value.agregate_type.value.lower()},{value.comparator.value},{value.value})"
                    for key in self.agg_fields()
                    if (value := getattr(self, key)) is not None
                ]
            )
            + "}"
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
                kwargs["stationid"] = Comparable[str](
                    value=str(value), comparator=Comparator(op)
                )
            elif key == "city":
                kwargs["city"] = Comparable[City](
                    value=City(value), comparator=Comparator(op)
                )
            elif key == "temp":
                kwargs["temp"] = Comparable[int](
                    value=int(value), comparator=Comparator(op)
                )
            elif key == "rain":
                kwargs["rain"] = Comparable[float](
                    value=float(value), comparator=Comparator(op)
                )
            elif key == "wind":
                kwargs["wind"] = Comparable[int](
                    value=int(value), comparator=Comparator(op)
                )
            elif key == "direction":
                kwargs["direction"] = Comparable[Direction](
                    value=Direction(value), comparator=Comparator(op)
                )
            elif key == "date":
                kwargs["date"] = Comparable[Date](
                    value=datetime.strptime(value, "%Y-%m-%d").date(),
                    comparator=Comparator(op),
                )
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
