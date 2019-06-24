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


@enum.unique
class BuiltinTypeAnnot(enum.Enum):
    """
    Enumerates the built in type annotations.
    """

    VOID = "void"
    INT = "int"
    NUM = "num"
    STR = "str"
    BOOL = "bool"
    NIL = "nil"

    def __str__(self) -> str:
        return str(self.value)

    def __eq__(self, other: object) -> Comparison:
        if isinstance(other, BuiltinTypeAnnot):
            return self.value == other.value
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


ARITH_TYPES = [BuiltinTypeAnnot.INT, BuiltinTypeAnnot.NUM]

# Return annotations


@enum.unique
class ReturnAnnot(enum.Enum):
    """
    Enumerates the different kinds of control flow for parts of code, either they always return,
    sometimes return, or never return.
    """

    NEVER = enum.auto()
    SOMETIMES = enum.auto()
    ALWAYS = enum.auto()

    def __str__(self) -> str:
        return self.name


# Index annotations


@enum.unique
class IndexAnnotType(enum.Enum):
    """
    Enumerates the possible types of index.
    """

    GLOBAL = enum.auto()
    LOCAL = enum.auto()
    UPVALUE = enum.auto()
    PARAM = enum.auto()
    UNRESOLVED = enum.auto()

    def __str__(self) -> str:
        return self.name


class IndexAnnot:
    """
    Annotation for the index and type of a value reference.
    """

    def __init__(self, value: int, kind: IndexAnnotType) -> None:
        self.value = value
        self.kind = kind

    def __eq__(self, other: object) -> Comparison:
        if isinstance(other, IndexAnnot):
            return self.kind == other.kind and self.value == other.value
        return NotImplemented

    def __ne__(self, other: object) -> Comparison:
        return not self == other

    def __str__(self) -> str:
        return f"{self.kind}:{self.value}"
