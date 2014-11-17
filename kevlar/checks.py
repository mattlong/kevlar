import re
try:
    from collections.abc import MutableMapping, MutableSequence
except ImportError:
    from collections import MutableMapping, MutableSequence


class Comparison(object):
    def __init__(self, obj):
        self._value = obj.get('value')

    def __ne__(self, other):
        return not self.__eq__(other)

class Equality(Comparison):
    def __eq__(self, other):
        return self._value == other

class Regex(Comparison):
    def __eq__(self, other):
        return re.match(self._value, other)

class Uuid(Comparison):
    _re = re.compile(r'[a-f0-9]{32}')

    def __eq__(self, other):
        return self._re.match(other)

class DateHeader(Comparison):
    def __eq__(self, other):
        from email.utils import parsedate
        return bool(parsedate(other))

class ISO8601DateTime(Comparison):
    _re = re.compile(
        r'(?P<year>\d{4})-(?P<month>\d{1,2})-(?P<day>\d{1,2})'
        r'[T ](?P<hour>\d{1,2}):(?P<minute>\d{1,2})'
        r'(?::(?P<second>\d{1,2})(?:\.(?P<microsecond>\d{1,6})\d{0,6})?)?'
        r'(?P<tzinfo>Z|[+-]\d{2}:?\d{2})?$'
    )

    def __eq__(self, other):
        return bool(self._re.match(other))


def get_comparison(value):
    type_field = '_t'
    if isinstance(value, MutableMapping) and type_field in value:
        _type = value[type_field]
        comparisons = {
            'equal': Equality,
            'regex': Regex,
            'uuid': Uuid,
            'date': DateHeader,
            'iso-8601': ISO8601DateTime,
        }

        if _type in comparisons:
            return comparisons[_type](value)

    return value


def compare(old, new):
    def compare_values(path, value, other):
        value = get_comparison(value)

        if isinstance(value, MutableMapping) and isinstance(other, MutableMapping):
            for thing in compare_dicts(path, value, other):
                yield thing

        elif isinstance(value, MutableSequence) and isinstance(other, MutableSequence):
            for thing in compare_lists(path, value, other):
                yield thing

        elif value != other:
            yield {'path': path, 'status': 'unequal', 'old': value, 'new': other}

        else:
            return

    def compare_dicts(path, value, other):
        for key in value:
            inner_path = path + [key]
            if key not in other:
                yield {'path': inner_path, 'status': 'missing', 'old': value[key]}
                continue

            for thing in compare_values(inner_path, value[key], other[key]):
                yield thing

        for key in other:
            inner_path = path + [key]
            if key not in value:
                yield {'path': inner_path, 'status': 'extra', 'new': other[key]}

    def compare_lists(path, value_list, other_list):
        for n, (value, other) in enumerate(zip(value_list, other_list)):
            inner_path = path + [n]
            for thing in compare_values(inner_path, value, other):
                yield thing

        value_len = len(value_list)
        other_len = len(other_list)
        if value_len < other_len:
            for n, other in enumerate(other_list[value_len:], start=value_len):
                yield {'path': path + [n], 'status': 'extra', 'new': other}
        elif value_len > other_len:
            for n, value in enumerate(value_list[other_len:], start=other_len):
                yield {'path': path + [n], 'status': 'missing', 'old': value}

    return list(compare_values([], old, new))