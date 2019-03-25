from uuid import UUID
from enum import Enum
from json import dumps
from decimal import Decimal
from re import compile
from types import GeneratorType, FunctionType
from datetime import date, time, datetime, timedelta
from typing import Any, Dict
from collections import OrderedDict
from inspect import isclass

__author__ = 'Guillermo Guirao Aguilar'
__email__ = 'contact@guillermoguiraoaguilar.com'
__license__ = 'MIT'
__version__ = '0.0.1'


UNSET = type('UNSET', (), {'__repr__': lambda self: 'UNSET'})()


def parser(entity):
    def matcher(value):
        try:
            return entity(*map(int, regex.match(value).groups()))
        except AttributeError:
            raise ValueError(f'{value} is not a valid iso-formatted date/time')

    patterns = {date: r'(\d{4})-(\d\d)-(\d\d)', time: r'(\d\d):(\d\d):(\d\d)'}
    patterns[datetime] = f'{patterns[date]}[T ]{patterns[time]}'
    regex = compile(patterns[entity])
    return matcher


class Config:
    strict = False
    mutable = False
    encoders: Dict[Any, Any] = {
        UUID: str,
        Decimal: float,
        set: list,
        frozenset: list,
        GeneratorType: list,
        date: str,
        time: str,
        datetime: str,
        Enum: lambda e: e.value,
        bytes: lambda o: o.decode(),
        timedelta: lambda td: td.total_seconds(),
    }
    decoders: Dict[Any, Any] = {
        date: parser(date),
        time: parser(time),
        datetime: parser(datetime)
    }

    def __init__(self,
                 *,
                 strict: bool = False,
                 mutable: bool = False,
                 encoders: Dict[Any, Any] = None,
                 decoders: Dict[Any, Any] = None):
        self.strict = strict
        self.mutable = mutable
        self.encoders = self.encoders.copy()
        self.encoders.update(encoders or {})
        self.decoders = self.decoders.copy()
        self.decoders.update(decoders or {})

    def options(self):
        for attr in ['strict', 'mutable']:
            if getattr(self, attr) != getattr(Config, attr):
                yield attr, getattr(self, attr)
        for attr in ['encoders', 'decoders']:
            tmp = {}
            obj = getattr(self, attr)
            cls = getattr(Config, attr)
            for key in obj:
                if obj[key] != cls.get(key):
                    tmp[key] = obj[key]
            if tmp:
                yield attr, tmp

    def __repr__(self):
        options = [f'{attr}={value}' for attr, value in self.options()]
        return f'Config({", ".join(options)})'

    def __eq__(self, item):
        return isinstance(item, Config) and repr(self) == repr(item)


class MetaSquema(type):
    def __new__(mcs, name, bases, namespace):
        fields = OrderedDict()
        types = {}
        for base in reversed(bases):
            if issubclass(base, Squema) and base != Squema:
                fields.update(base.__fields__)
                types.update(getattr(base, '__annotations__', {}))

        annotations = namespace.get('__annotations__', {})
        for key, value in annotations.items():
            if key in namespace:
                fields[key] = namespace[key]
            elif key not in fields:
                fields[key] = UNSET

        new_namespace = {
            **{k: v for k, v in namespace.items() if k not in fields},
            '__fields__': fields,
            '__values__': {},
            '__annotations__': {**types, **annotations}
        }

        return super().__new__(mcs, name, bases, new_namespace)


class Squema(metaclass=MetaSquema):
    __config__ = Config()

    def __init__(self, *args, **kwargs):
        assert not (args and kwargs), ValueError(
            f'Cannot instantiate squema with args and kwargs')

        object.__setattr__(self, '__values__', self.__fields__.copy())
        if args:
            if self.__config__.strict and len(args) > len(self.__values__):
                raise ValueError(
                    f'Too many arguments for <{self.__class__.__name__}>')
            kwargs = dict(zip(self.__values__.keys(), args))

        for key, v in kwargs.items():
            if key in self.__values__:
                self.__values__[key] = self.__getval__(key, v)
            elif self.__config__.strict:
                raise AttributeError(f'"{key}" is not a valid attribute '
                                     f'of <{self.__class__.__name__}>')

        if self.__config__.strict:
            empty = [k for k, v in self.__values__.items() if v is UNSET]
            if empty:
                raise ValueError(f'Missing value for {", ".join(empty)}')

    def __str__(self) -> str:
        return dumps(dict(self.items()), default=self.encode)

    def __repr__(self) -> str:
        values = [f'{k}={repr(v)}' for k, v in self.items()]
        return f'{self.__class__.__name__}({", ".join(values)})'

    def __getval__(self, key, value):
        """ Convert a value to the key type defined in the annotations """
        unit = self.__annotations__[key]
        if not isinstance(unit, FunctionType) and isinstance(value, unit):
            return value
        elif unit in self.__config__.decoders:
            return self.__config__.decoders[unit](value)
        elif type(unit) is type:
            try:
                return unit(value)
            except ValueError:
                raise ValueError(f'Expected type <{unit.__name__}> for field '
                                 f'"{key}", but got <{type(value).__name__}>')
        elif isclass(unit) and issubclass(unit, Squema):
            try:
                return unit(**value)
            except TypeError:
                raise TypeError(f'The value for "{key}" must be a mapping, '
                                f'not <{value.__name__}>')
        elif callable(unit):
            return unit(value)
        else:
            raise TypeError(f'No decoder defined for type {type(value)}')

    def __getattr__(self, key):
        try:
            return self.__values__[key]
        except KeyError:
            raise AttributeError(f'"{key}" is not an attribute of '
                                 f'<{self.__class__.__name__}>')

    def __setattr__(self, key, value):
        if key in self.__values__:
            if self.__config__.mutable:
                self.__values__[key] = self.__getval__(key, value)
            else:
                raise TypeError(f'<{self.__class__.__name__}> is immutable')
        elif not self.__config__.strict:
            object.__setattr__(self, key, value)
        else:
            raise ValueError(f'"{key}" is not a field of '
                             f'<{self.__class__.__name__}>')

    def __len__(self):
        return len(self.__values__)

    def __eq__(self, item):
        return item.__class__ is self.__class__ and hash(item) == hash(self)

    def __ne__(self, item):
        return not self == item

    def __hash__(self):
        return hash(repr(self))

    def __getitem__(self, key):
        if key in self.__values__:
            return self.__getattr__(key)
        else:
            raise KeyError(f'"{key}" is not a key of '
                           f'<{self.__class__.__name__}>')

    def __setitem__(self, key, value):
        if key in self.__values__:
            self.__setattr__(key, value)
        else:
            raise KeyError(f'"{key}" is not a key of '
                           f'<{self.__class__.__name__}>')

    def __delitem__(self, key):
        if not self.__config__.mutable:
            raise TypeError(f'<{self.__class__.__name__}> is immutable')
        self.__values__[key] = UNSET

    def __iter__(self):
        return self.keys()

    def __reversed__(self):
        return reversed(*self)

    def keys(self):
        return (key for key, value in self.items())

    def values(self):
        return (value for key, value in self.items())

    def items(self):
        if self.__config__.strict:
            return self.__values__.items()
        else:
            for key, value in self.__values__.items():
                if value is not UNSET:
                    yield key, value

    def copy(self):
        return self.__class__(**self.__values__.items())

    def update(self, data: Dict[str, Any]):
        values = {k: v for k, v in data.items() if k in self.__values__}
        if self.__config__.strict and len(data) != len(values):
            raise ValueError(f'Invalid fields for <{self.__class__.__name__}>')
        self.__values__.update(values)

    @classmethod
    def encode(cls, value):
        if type(value) in cls.__config__.encoders:
            return cls.__config__.encoders[type(value)](value)
        elif isinstance(value, Squema):
            return dict(value.items())
        else:
            for base in bases(type(value)):
                if base in cls.__config__.encoders:
                    return cls.__config__.encoders[base](value)
            raise TypeError('No encoder provided for type '
                            f'<{type(value).__name__}>')


def bases(item):
    for base in item.__bases__:
        yield base
        bases(base)
