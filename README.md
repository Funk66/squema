# squema

[![Build Status](https://travis-ci.org/Funk66/squema.svg?branch=master)](https://travis-ci.org/Funk66/squema)
[![Code Quality](https://api.codacy.com/project/badge/Grade/82ed6d0ba33640228359793ba77874f6)](https://www.codacy.com/app/Funk66/squema?utm_source=github.com&amp;utm_medium=referral&amp;utm_content=Funk66/squema&amp;utm_campaign=Badge_Grade)
[![Coverage](https://api.codacy.com/project/badge/Coverage/82ed6d0ba33640228359793ba77874f6)](https://www.codacy.com/app/Funk66/squema?utm_source=github.com&utm_medium=referral&utm_content=Funk66/squema&utm_campaign=Badge_Coverage)

Type annotations help your IDE understand your code and warn you of potential
errors as you type. Squema wields this information to provide automatic data
conversion, allowing you to write simpler and cleaner code when interacting
with databases and other external APIs that require a non-native data formats
such as JSON.

*Disclaimer*: this module is a proof of concept. Updates may include breaking changes.

## Installation

  ```bash
  $ pip install squema
  ```

## Basic usage

Declare your data structures as subclasses of `Squema` with annotated attributes.

```python
from uuid import UUID
from enum import Enum
from squema import Squema
from datetime import date
from typing import NewType


Gender = Enum('Gender', ['male', 'female', 'other'])
Password = NewType('Password', str)


class Info(Squema):
    name: str
    gender: Gender
    married: bool
    birthday: date


class User(Squema):
    id: UUID
    password: Password
    info: Info
    credit: int = 0


user = User(
    id='00112233-4455-6677-8899-aabbccddeeff',
    name='Akis',
    password='pa5sw0rd',
    info={'gender': 3, 'married': True, 'birthday': '1723-05-09'},
)

print(repr(user))
print(user)
```

The script above is functional and will print the following two lines:

```
User(id=UUID('00112233-4455-6677-8899-aabbccddeeff'), password='pa5sw0rd', info=Info(gender=<Gender.other: 3>, married=True, birthday=datetime.date(1723, 5, 9)), credit=0)
{"id": "00112233-4455-6677-8899-aabbccddeeff", "password": "pa5sw0rd", "info": {"gender": 3, "married": true, "birthday": "1723-05-09"}, "credit": 0}
```

Here's what's going on:

- The data structure `User` is defined and instantiated as `user`
- Arguments are converted to their corresponding types:
  - `id` is converted to a `UUID` entity
  - `name` is not defined as a field of `User` and its value is silently ignored
  - `password` remains as a string, but type checkers will identify it as being of type `Password`
- `info` is a nested squema with its own values loaded from a mapping
- `Info.name` doesn't receive a value and therefore is not included in the output
- `credit` is declared with a default value, so it is always included in the output

Squema values can be accessed as object attributes and dictionary keys.

```python
assert user.id is user['id']
```

They also behave like dictionaries, but only fields defined at the class level
and with annotations can be treated as dictionary keys. Squemas work like normal
objects otherwise.

```python
assert user.name is user['name']
user.age = 25
assert 'age' not in user
assert user.age == 25
assert user.get('age') is None
```

This is to allow squemas to be used as a type-safe alternative to dictionaries
while at the same time keeping the versatility and convenience of normal objects.

## Options

Squemas can be configured for custom behaviour. To do so, simply assign
`squema.Config` object initialized with the desired arguments as the `Squema.__config__`
attribute at the class level.

```python
class Document(Squema):
    __config__ = Config(strict=True, mutable=True)
    pages: int
    public: bool
```

### Strict

Default: False

Strict mode enforces the instantiation of squemas with all the non-default values.
Missing and extra fields raise a `ValueError`.

Assigning extra attributes to the object is also forbidden.


### Mutable

Default: False

This option allows squema values to be changed after initialization.
The behaviour of custom attributes is not affected.

```python
user = User(password='pa5sw0rd')
user.password = 'pwd'
assert user.password == 'pwd'
del user['password']
assert 'password' not in user
```

### Encoders

You can configure your own encoders for data conversion on instantiation.
The `encoders` argument of the squema configuration extends and overwrites the
default encoding dictionary, mapping field types to functions.

In the example below, the field `deadline` is declared to be of type `datetime`.
To enable the creation of `Report` objects by providing a custom value, such as
a timestamp, an enconding function is defined in the configuration to convert
these values to their corresponding types.

```python
from datetime import datetime


class Report(Squema):
    __config__ = Config(encoders={datetime: datetime.from_timestamp})
    deadline: datetime


report = Report(deadline=1234567890)
assert report.deadline == datetime(2009, 2, 14, 0, 31, 30)
```

This feature could be used for data validation too. However, this module is
intended to be as simple and lightweight as possible. Other libraries offer more
versatility for this kind of purposes (see `pydantic`).


### Decoders

Decoders work similarly to encoders, but are meant to convert native values to
valid JSON data structures.

```python
from datetime import datetime


class Report(Squema):
    __config__ = Config(decoders={datetime: lambda d: d.strftime('%d.%m.%Y')})
    deadline: datetime


report = Report(deadline='2000-12-31')
assert str(report) == '{"deadline": "31.12.2000"}'
```
