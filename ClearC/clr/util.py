"""
Module containing miscellaneous utility functions.
"""

from typing import TypeVar, Callable, Iterable, Dict, Set, Tuple, Any

T = TypeVar("T")  # pylint: disable=invalid-name
K = TypeVar("K")  # pylint: disable=invalid-name


def group_by(key_func: Callable[[T], K], values: Iterable[T]) -> Dict[K, Set[T]]:
    """
    Group an iterable of values by a given key function.
    """
    grouping: Dict[K, Set[T]] = {}
    for value in values:
        key = key_func(value)
        if key in grouping:
            grouping[key].add(value)
        else:
            grouping[key] = {value}
    return grouping


def split_instances(clazz: type, values: Iterable[T]) -> Tuple[Set[Any], Set[T]]:
    """
    Split an iterable into instances of a type and other values.
    """
    instances = set()
    rest = set()
    for value in values:
        if isinstance(value, clazz):
            instances.add(value)
        else:
            rest.add(value)
    return instances, rest


def break_before(value: T, iterable: Iterable[T]) -> Iterable[T]:
    """
    Break after reaching the given value in an iterable.
    """
    for element in iterable:
        if element == value:
            break
        yield element
