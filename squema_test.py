from enum import Enum, IntEnum
from pytest import raises
from typing import NewType
from datetime import date, time, datetime

from squema import Squema, Config, UNSET


NewInt = NewType("NewInt", int)
Choice = Enum("Choice", ["yes", "no"])


class Entity(Squema):
    boolean: bool


class SampleModel(Squema):
    number: int
    string: str
    entity: Entity
    newint: NewInt
    choice: Choice
    default: float = 0.0


sample_data = {
    "number": 1,
    "string": "1",
    "entity": Entity(boolean=True),
    "newint": NewInt(1),
    "choice": Choice.yes,
}


def check_sample_model(model):
    assert model.number == 1
    assert model.string == "1"
    assert model.entity.boolean is True
    assert model.newint == 1
    assert model.choice is Choice.yes
    assert model.default == 1.0
    assert isinstance(model.entity, Entity)


def test_load_values():
    check_sample_model(SampleModel(default=1.0, **sample_data))


def test_convert_values():
    check_sample_model(
        SampleModel(
            number="1",
            string=1,
            entity={"boolean": True},
            newint=1,
            choice=1,
            default=1,
        )
    )


def test_default_values():
    model = SampleModel(**sample_data)
    assert model.default == 0.0


def test_nested_squemas():
    entity = Entity(True)
    model = SampleModel(entity=entity)
    assert model.entity is entity


def test_inheritance():
    class Submodel(SampleModel):
        data: dict
        default: float = 1.0

    model = Submodel(data=[("a", 1)], **sample_data)
    assert model.data == {"a": 1}
    check_sample_model(model)


def test_extra_values():
    model = SampleModel(extra=True, **sample_data)
    assert "extra" not in model
    with raises(AttributeError):
        model.extra
    with raises(KeyError):
        model["extra"]


def test_extra_attributes():
    model = SampleModel(**sample_data)
    model.attr = True
    assert "attr" not in model
    assert model.attr is True
    with raises(KeyError):
        model["attr"]


def test_spread_operator():
    model = SampleModel(**sample_data)
    assert len([*model]) == 6


def test_attribute_definitions():
    class Model(Squema):
        number: int = 0
        other = True
        __string__: str

    model = Model()
    assert model.number == 0
    assert "other" not in model
    assert "__string__" not in model
    assert model.other is True


def test_override_field():
    TinyInt = IntEnum("TinyInt", ["one", "two"])

    class Submodel(SampleModel):
        number: TinyInt

    model = Submodel(number=1)
    assert model.number is TinyInt.one


def test_date_decoders():
    class Model(Squema):
        date: date
        time: time
        datetime: datetime

    model = Model("1999-12-31", "23:59:59", "1999-12-31T23:59:59")
    assert model.date == date(1999, 12, 31)
    assert model.time == time(23, 59, 59)
    assert model.datetime == datetime(1999, 12, 31, 23, 59, 59)
    model = Model(datetime="1999-12-31 23:59:59")
    assert model.datetime == datetime(1999, 12, 31, 23, 59, 59)


def test_date_encoders():
    assert Squema.encode(date(1999, 12, 31)) == "1999-12-31"


def test_repr():
    model = SampleModel(number=1)
    assert repr(model) == "SampleModel(number=1, default=0.0)"
    model = SampleModel(**sample_data)
    assert repr(model) == (
        "SampleModel(number=1, string='1', entity=Entity(boolean=True), "
        "newint=1, choice=<Choice.yes: 1>, default=0.0)"
    )


def test_str():
    model = SampleModel(number=1)
    assert str(model) == '{"number": 1, "default": 0.0}'
    model = SampleModel(**sample_data)
    assert str(model) == (
        '{"number": 1, "string": "1", "entity": {"boolean": true}, '
        '"newint": 1, "choice": 1, "default": 0.0}'
    )


def test_config():
    c1 = Config(mutable=True)
    c2 = Config(strict=False, mutable=True, encoders={set: list})
    assert c1 == c2


def test_default_config():
    config = Config()
    assert config.strict is False
    assert config.mutable is False


def test_config_options():
    config = Config(mutable=True, encoders={int: float})
    options = list(config.options())
    assert options == [("mutable", True), ("encoders", {int: float})]


def test_strict_mode():
    class Model(Squema):
        number: int
        __config__ = Config(strict=True)

    model = Model(1)
    assert model.number == 1
    with raises(ValueError):
        model = Model()
    with raises(ValueError):
        model = Model(1, 2)


def test_mutable_squema():
    class Model(Squema):
        number: int
        __config__ = Config(mutable=True)

    model = Model(1)
    assert model.number == 1
    model.number = 2
    assert model.number == 2
    model["number"] = 3
    assert model.number == 3
    del model["number"]
    assert model.number is UNSET


def test_immutable_squema():
    model = SampleModel(**sample_data)
    model.attr = True
    assert model.attr is True
    with raises(TypeError):
        model.number = 2
    with raises(TypeError):
        del model["number"]
