"""
This module provides a Resolver class to visit AST nodes resolving
identifiers to find their types and variable indices.
"""
from enum import Enum
from collections import namedtuple, defaultdict


class ValueType(Enum):
    """
    This class enumerates the possible types of Clear variables,
    including an unresolved option.
    """

    INT = "int"
    NUM = "num"
    STR = "str"
    BOOL = "bool"
    UNRESOLVED = "<unresolved>"

    def __str__(self):
        return self.value


ResolvedName = namedtuple(
    "ResolvedName",
    ("value_type", "index", "is_global"),
    defaults=(ValueType.UNRESOLVED, -1, False),
)


class Resolver:
    """
    This class provides functionality for visiting AST nodes to resolve
    the type and variable index of identifiers / declarations thereof.
    """

    def __init__(self):
        self.scopes = [defaultdict(ResolvedName)]
        self.level = 0
        self.local_index = 0
        self.global_index = 0

    def _current_scope(self):
        return self.scopes[self.level]

    def _global_scope(self):
        return self.scopes[0]

    def _get_scope(self, lookback):
        return self.scopes[self.level - lookback]

    def push_scope(self):
        """
        This function pushes a new scope to resolve within.
        """
        self.scopes.append(defaultdict(ResolvedName))
        self.level += 1

    def pop_scope(self):
        """
        This function pops the current resolution scope.
        """
        if self.level > 0:
            popped = self._current_scope()
            if popped:
                self.local_index = min(
                    [r.index for r in popped.values() if r.index != -1]
                )
        del self.scopes[self.level]
        self.level -= 1

    def add_name(self, name, value_type):
        """
        This function resolves the given name as a new variable in the current scope
        or as a redefinition of it if it already exists, returning the resolved information.
        """
        prev = self.lookup_name(name)
        if prev.value_type == ValueType.UNRESOLVED:
            if self.level > 0:
                idx = self.local_index
                self.local_index += 1
            else:
                idx = self.global_index
                self.global_index += 1
        else:
            idx = prev.index
        result = ResolvedName(value_type, idx, self.level == 0)
        self._current_scope()[name] = result
        return result

    def lookup_name(self, name):
        """
        This function resolves the given name to a previously resolved
        declaration, returning the resolved information set as unresolved
        if no such declaration was found.
        """
        result = ResolvedName()
        lookback = 0
        while lookback < self.level:
            result = self._get_scope(lookback)[name]
            lookback += 1
            if result.value_type != ValueType.UNRESOLVED:
                break
        else:
            result = self._global_scope()[name]
        return result
