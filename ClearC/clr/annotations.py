"""
Contains definitions for annotations of the ast.
"""

from typing import Union, List

import enum

Comparison = Union[bool, "NotImplemented"]

# Type Annotations:

TypeAnnot = Union[
    "BuiltinTypeAnnot", "FuncTypeAnnot", "OptionalTypeAnnot", "UnresolvedTypeAnnot"
]


class UnresolvedTypeAnnot:
    """
    Type annotation for an unresolved node.
    """

    def __init__(self) -> None:
        self.unresolved = True

    def __str__(self) -> str:
        return "<unresolved>"

    def __eq__(self, other: object) -> Comparison:
        if isinstance(other, BuiltinTypeAnnot):
            return False
        if isinstance(other, FuncTypeAnnot):
            return False
        if isinstance(other, OptionalTypeAnnot):
            return False
        if isinstance(other, UnresolvedTypeAnnot):  # maybe return True here?
            return False
        return NotImplemented

    def __ne__(self, other: object) -> Comparison:
        return not self == other


class BuiltinTypeAnnot:
    """
    Type annotation for a built in type.
    """

    def __init__(self, name: str) -> None:
        self.name = name
        self.unresolved = False

    def __str__(self) -> str:
        return self.name

    def __eq__(self, other: object) -> Comparison:
        if isinstance(other, BuiltinTypeAnnot):
            return self.name == other.name
        if isinstance(other, FuncTypeAnnot):
            return False
        if isinstance(other, OptionalTypeAnnot):
            return False
        if isinstance(other, UnresolvedTypeAnnot):
            return False
        return NotImplemented

    def __ne__(self, other: object) -> Comparison:
        return not self == other


class FuncTypeAnnot:
    """
    Type annotation for a function type.
    """

    def __init__(self, params: List[TypeAnnot], return_type: TypeAnnot) -> None:
        self.params = params
        self.return_type = return_type
        self.unresolved = False

    def __str__(self) -> str:
        param_str = ", ".join(str(param) for param in self.params)
        return f"func({param_str}) {self.return_type}"

    def __eq__(self, other: object) -> Comparison:
        if isinstance(other, BuiltinTypeAnnot):
            return False
        if isinstance(other, FuncTypeAnnot):
            return self.params == other.params and self.return_type == other.return_type
        if isinstance(other, OptionalTypeAnnot):
            return False
        if isinstance(other, UnresolvedTypeAnnot):
            return False
        return NotImplemented

    def __ne__(self, other: object) -> Comparison:
        return not self == other


class OptionalTypeAnnot:
    """
    Type annotation for an optional type.
    """

    def __init__(self, target: TypeAnnot) -> None:
        self.target = target
        self.unresolved = False

    def __str__(self) -> str:
        return f"({self.target})?"

    def __eq__(self, other: object) -> Comparison:
        if isinstance(other, BuiltinTypeAnnot):
            return False
        if isinstance(other, FuncTypeAnnot):
            return False
        if isinstance(other, OptionalTypeAnnot):
            return self.target == other.target
        if isinstance(other, UnresolvedTypeAnnot):
            return False
        return NotImplemented

    def __ne__(self, other: object) -> Comparison:
        return not self == other


TYPE_VOID = BuiltinTypeAnnot("void")
TYPE_STR = BuiltinTypeAnnot("str")
TYPE_BOOL = BuiltinTypeAnnot("bool")
TYPE_INT = BuiltinTypeAnnot("int")
TYPE_NUM = BuiltinTypeAnnot("num")
TYPE_NIL = BuiltinTypeAnnot("nil")


# Return annotations


class ReturnAnnot(enum.Enum):
    """
    Enumerates the different kinds of control flow for parts of code, either they always return,
    sometimes return, or never return.
    """

    NEVER = enum.auto()
    SOMETIMES = enum.auto()
    ALWAYS = enum.auto()
