"""
Contains definitions for annotations of the ast.
"""

from typing import Union, List, NamedTuple

import enum

import clr.bytecode as bc

# Type Annotations:

TypeAnnot = Union[
    "UnresolvedTypeAnnot",
    "BuiltinTypeAnnot",
    "FuncTypeAnnot",
    "OptionalTypeAnnot",
    "UnionTypeAnnot",
]


class UnresolvedTypeAnnot:
    """
    Type annotation for an unresolved node.
    """

    def __init__(self) -> None:
        self.unresolved = True

    def __str__(self) -> str:
        return "<unresolved>"

    def __eq__(self, other: object) -> bool:
        if isinstance(other, UnresolvedTypeAnnot):
            return False
        if isinstance(other, BuiltinTypeAnnot):
            return False
        if isinstance(other, FuncTypeAnnot):
            return False
        if isinstance(other, OptionalTypeAnnot):
            return False
        return NotImplemented

    def __ne__(self, other: object) -> bool:
        eq_result = self == other
        if eq_result == NotImplemented:
            return NotImplemented
        return not eq_result


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

    def __hash__(self) -> int:
        return hash(self.value) * 31

    def __eq__(self, other: object) -> bool:
        if isinstance(other, UnresolvedTypeAnnot):
            return False
        if isinstance(other, BuiltinTypeAnnot):
            return str(self.value) == str(other.value)
        if isinstance(other, FuncTypeAnnot):
            return False
        if isinstance(other, OptionalTypeAnnot):
            return False
        return NotImplemented

    def __ne__(self, other: object) -> bool:
        eq_result = self == other
        if eq_result == NotImplemented:
            return NotImplemented
        return not eq_result


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

    def __hash__(self) -> int:
        return hash((*self.params, self.return_type)) * 41

    def __eq__(self, other: object) -> bool:
        if isinstance(other, UnresolvedTypeAnnot):
            return False
        if isinstance(other, BuiltinTypeAnnot):
            return False
        if isinstance(other, FuncTypeAnnot):
            return self.params == other.params and self.return_type == other.return_type
        if isinstance(other, OptionalTypeAnnot):
            return False
        return NotImplemented

    def __ne__(self, other: object) -> bool:
        eq_result = self == other
        if eq_result == NotImplemented:
            return NotImplemented
        return not eq_result


class OptionalTypeAnnot:
    """
    Type annotation for an optional type.
    """

    def __init__(self, target: TypeAnnot) -> None:
        self.target = target
        self.unresolved = False

    def __str__(self) -> str:
        return f"({self.target})?"

    def __hash__(self) -> int:
        return hash(self.target) * 17

    def __eq__(self, other: object) -> bool:
        if isinstance(other, UnresolvedTypeAnnot):
            return False
        if isinstance(other, BuiltinTypeAnnot):
            return False
        if isinstance(other, FuncTypeAnnot):
            return False
        if isinstance(other, OptionalTypeAnnot):
            return self.target == other.target
        return NotImplemented

    def __ne__(self, other: object) -> bool:
        eq_result = self == other
        if eq_result == NotImplemented:
            return NotImplemented
        return not eq_result


# TODO: Support union types externally, e.g. val x int|num = 2i;


class UnionTypeAnnot:
    """
    Type annotation for a sum type.
    """

    def __init__(self, *types: TypeAnnot) -> None:
        self.types = types

    def __str__(self) -> str:
        return " | ".join(str(elem) for elem in self.types)

    def __hash__(self) -> int:
        return hash(self.types) * 23

    def __eq__(self, other: object) -> bool:
        if isinstance(
            other,
            (UnresolvedTypeAnnot, BuiltinTypeAnnot, FuncTypeAnnot, OptionalTypeAnnot),
        ):
            return len(self.types) == 1 and self.types[0] == other
        if isinstance(other, UnionTypeAnnot):
            return self.types == other.types
        return NotImplemented

    def __ne__(self, other: object) -> bool:
        eq_result = self == other
        if eq_result == NotImplemented:
            return NotImplemented
        return not eq_result


class Builtin(NamedTuple):
    """
    Object for a builtin function specification.
    """

    opcode: bc.Opcode
    type_annot: TypeAnnot


ARITH_TYPES = [BuiltinTypeAnnot.INT, BuiltinTypeAnnot.NUM]
BUILTINS = {
    "int": Builtin(
        opcode=bc.Opcode.INT,
        type_annot=FuncTypeAnnot(
            params=[
                UnionTypeAnnot(
                    BuiltinTypeAnnot.BOOL,
                    BuiltinTypeAnnot.INT,
                    BuiltinTypeAnnot.NIL,
                    BuiltinTypeAnnot.NUM,
                )
            ],
            return_type=BuiltinTypeAnnot.INT,
        ),
    ),
    "bool": Builtin(
        opcode=bc.Opcode.BOOL,
        type_annot=FuncTypeAnnot(
            params=[
                UnionTypeAnnot(
                    BuiltinTypeAnnot.BOOL,
                    BuiltinTypeAnnot.INT,
                    BuiltinTypeAnnot.NIL,
                    BuiltinTypeAnnot.NUM,
                )
            ],
            return_type=BuiltinTypeAnnot.BOOL,
        ),
    ),
    "num": Builtin(
        opcode=bc.Opcode.NUM,
        type_annot=FuncTypeAnnot(
            params=[
                UnionTypeAnnot(
                    BuiltinTypeAnnot.BOOL,
                    BuiltinTypeAnnot.INT,
                    BuiltinTypeAnnot.NIL,
                    BuiltinTypeAnnot.NUM,
                )
            ],
            return_type=BuiltinTypeAnnot.NUM,
        ),
    ),
    "str": Builtin(
        opcode=bc.Opcode.STR,
        type_annot=FuncTypeAnnot(
            params=[
                UnionTypeAnnot(
                    BuiltinTypeAnnot.BOOL,
                    BuiltinTypeAnnot.INT,
                    BuiltinTypeAnnot.NIL,
                    BuiltinTypeAnnot.NUM,
                )
            ],
            return_type=BuiltinTypeAnnot.STR,
        ),
    ),
    "clock": Builtin(
        opcode=bc.Opcode.CLOCK,
        type_annot=FuncTypeAnnot(params=[], return_type=BuiltinTypeAnnot.NUM),
    ),
}

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

    def __eq__(self, other: object) -> bool:
        if isinstance(other, IndexAnnot):
            return self.kind == other.kind and self.value == other.value
        return NotImplemented

    def __ne__(self, other: object) -> bool:
        eq_result = self == other
        if eq_result == NotImplemented:
            return NotImplemented
        return not eq_result

    def __str__(self) -> str:
        return f"{self.kind}:{self.value}"
