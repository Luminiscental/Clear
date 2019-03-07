from enum import Enum


class ValueType(Enum):
    INT = "int"
    NUM = "num"
    STR = "str"
    BOOL = "bool"
    UNRESOLVED = "<unresolved>"

    def __str__(self):
        return self.value


class Resolver:
    def __init__(self):
        self.scopes = [{}]
        self.level = 0

    def _current_scope(self):
        return self.scopes[self.level]

    def _get_scope(self, lookback):
        return self.scopes[self.level - lookback]

    def push_scope(self):
        self.scopes.append({})
        self.level += 1

    def pop_scope(self):
        del self.scopes[self.level]
        self.level -= 1

    def set_type(self, name, value_type):
        self._current_scope()[name] = value_type

    def lookup_type(self, name):
        result = ValueType.UNRESOLVED
        lookback = 0
        while result is ValueType.UNRESOLVED:
            try:
                result = self._get_scope(lookback).get(name, ValueType.UNRESOLVED)
                lookback += 1
            except IndexError:
                break
        return result
