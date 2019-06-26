"""
Contains definitions for annotations of the ast.
"""

from typing import Union, List, NamedTuple, Set, Dict, Tuple

import enum

import clr.bytecode as bc

# Type Annotations:

UnitType = Union[
    "UnresolvedTypeAnnot", "BuiltinTypeAnnot", "FuncTypeAnnot", "TupleTypeAnnot"
]


class TypeAnnot:
    """
    Base class for type annotations.
    """

    def expand(self) -> Set[UnitType]:
        """
        Expand the type into a set of contained unit types.
        """
        raise NotImplementedError


class UnresolvedTypeAnnot(TypeAnnot):
    """
    Type annotation for an unresolved node.
    """

    def __str__(self) -> str:
        return "<unresolved>"

    def __hash__(self) -> int:
        return 73

    def __eq__(self, other: object) -> bool:
        if isinstance(other, UnresolvedTypeAnnot):
            return True
        if isinstance(
            other, (BuiltinTypeAnnot, FuncTypeAnnot, OptionalTypeAnnot, TupleTypeAnnot)
        ):
            return False
        return NotImplemented

    def __ne__(self, other: object) -> bool:
        eq_result = self == other
        if eq_result == NotImplemented:
            return NotImplemented
        return not eq_result

    def expand(self) -> Set[UnitType]:
        return {self}


@enum.unique
class BuiltinTypeAnnot(TypeAnnot, enum.Enum):
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
        if isinstance(other, BuiltinTypeAnnot):
            return str(self.value) == str(other.value)
        if isinstance(
            other,
            (UnresolvedTypeAnnot, FuncTypeAnnot, OptionalTypeAnnot, TupleTypeAnnot),
        ):
            return False
        return NotImplemented

    def __ne__(self, other: object) -> bool:
        eq_result = self == other
        if eq_result == NotImplemented:
            return NotImplemented
        return not eq_result

    def expand(self) -> Set[UnitType]:
        return {self}


class FuncTypeAnnot(TypeAnnot):
    """
    Type annotation for a function type.
    """

    def __init__(self, params: List[TypeAnnot], return_type: TypeAnnot) -> None:
        self.params = params
        self.return_type = return_type

    def __str__(self) -> str:
        param_str = ", ".join(str(param) for param in self.params)
        return f"func({param_str}) {self.return_type}"

    def __hash__(self) -> int:
        return hash((*self.params, self.return_type)) * 41

    def __eq__(self, other: object) -> bool:
        if isinstance(other, FuncTypeAnnot):
            return self.params == other.params and self.return_type == other.return_type
        if isinstance(
            other,
            (UnresolvedTypeAnnot, BuiltinTypeAnnot, OptionalTypeAnnot, TupleTypeAnnot),
        ):
            return False
        return NotImplemented

    def __ne__(self, other: object) -> bool:
        eq_result = self == other
        if eq_result == NotImplemented:
            return NotImplemented
        return not eq_result

    def expand(self) -> Set[UnitType]:
        return {self}


class OptionalTypeAnnot(TypeAnnot):
    """
    Type annotation for an optional type.
    """

    def __init__(self, target: TypeAnnot) -> None:
        self.target = target

    def __str__(self) -> str:
        return f"({self.target})?"

    def __hash__(self) -> int:
        return hash(self.target) * 17

    def __eq__(self, other: object) -> bool:
        if isinstance(other, OptionalTypeAnnot):
            return self.target == other.target
        if isinstance(
            other,
            (UnresolvedTypeAnnot, BuiltinTypeAnnot, FuncTypeAnnot, TupleTypeAnnot),
        ):
            return False
        return NotImplemented

    def __ne__(self, other: object) -> bool:
        eq_result = self == other
        if eq_result == NotImplemented:
            return NotImplemented
        return not eq_result

    def expand(self) -> Set[UnitType]:
        result = self.target.expand()
        result.add(BuiltinTypeAnnot.NIL)
        return result


class UnionTypeAnnot(TypeAnnot):
    """
    Type annotation for a sum type.
    """

    def __init__(self, types: Set[TypeAnnot]) -> None:
        self.types = types

    def __str__(self) -> str:
        return " | ".join(str(elem) for elem in self.types)

    def __hash__(self) -> int:
        return hash(tuple(self.types)) * 23

    def __eq__(self, other: object) -> bool:
        if isinstance(
            other,
            (
                UnresolvedTypeAnnot,
                BuiltinTypeAnnot,
                FuncTypeAnnot,
                OptionalTypeAnnot,
                TupleTypeAnnot,
            ),
        ):
            return self.types == {other}
        if isinstance(other, UnionTypeAnnot):
            return self.types == other.types
        return NotImplemented

    def __ne__(self, other: object) -> bool:
        eq_result = self == other
        if eq_result == NotImplemented:
            return NotImplemented
        return not eq_result

    def expand(self) -> Set[UnitType]:
        return {subsubtype for subtype in self.types for subsubtype in subtype.expand()}


class TupleTypeAnnot(TypeAnnot):
    """
    Type annotation for a tuple type.
    """

    def __init__(self, types: Tuple[TypeAnnot, ...]) -> None:
        self.types = types

    def __str__(self) -> str:
        inner = ", ".join(str(elem) for elem in self.types)
        return f"({inner})"

    def __hash__(self) -> int:
        return hash(self.types) * 73

    def __eq__(self, other: object) -> bool:
        if isinstance(other, TupleTypeAnnot):
            return self.types == other.types
        if isinstance(
            other,
            (UnresolvedTypeAnnot, BuiltinTypeAnnot, FuncTypeAnnot, OptionalTypeAnnot),
        ):
            return False
        return NotImplemented

    def __ne__(self, other: object) -> bool:
        eq_result = self == other
        if eq_result == NotImplemented:
            return NotImplemented
        return not eq_result

    def expand(self) -> Set[UnitType]:
        return {self}


class Builtin(NamedTuple):
    """
    Object for a builtin function specification.
    """

    opcode: bc.Opcode
    type_annot: TypeAnnot


BOOL = BuiltinTypeAnnot.BOOL
INT = BuiltinTypeAnnot.INT
NIL = BuiltinTypeAnnot.NIL
NUM = BuiltinTypeAnnot.NUM
VOID = BuiltinTypeAnnot.VOID
STR = BuiltinTypeAnnot.STR


BUILTINS = {
    "int": Builtin(
        opcode=bc.Opcode.INT,
        type_annot=FuncTypeAnnot(
            params=[UnionTypeAnnot({BOOL, INT, NIL, NUM})], return_type=INT
        ),
    ),
    "bool": Builtin(
        opcode=bc.Opcode.BOOL,
        type_annot=FuncTypeAnnot(
            params=[UnionTypeAnnot({BOOL, INT, NIL, NUM})], return_type=BOOL
        ),
    ),
    "num": Builtin(
        opcode=bc.Opcode.NUM,
        type_annot=FuncTypeAnnot(
            params=[UnionTypeAnnot({BOOL, INT, NIL, NUM})], return_type=NUM
        ),
    ),
    "str": Builtin(
        opcode=bc.Opcode.STR,
        type_annot=FuncTypeAnnot(
            params=[UnionTypeAnnot({BOOL, INT, NIL, NUM})], return_type=STR
        ),
    ),
    "clock": Builtin(
        opcode=bc.Opcode.CLOCK, type_annot=FuncTypeAnnot(params=[], return_type=NUM)
    ),
}


class TypedOperatorInfo(NamedTuple):
    """
    Named tuple for information about an operator with strict operand typing.
    """

    overloads: Dict[FuncTypeAnnot, List[bc.Instruction]]


class UntypedOperatorInfo(NamedTuple):
    """
    Named tuple for information about an operator with non-strict operand typing.
    """

    return_type: TypeAnnot
    opcodes: List[bc.Instruction]


TYPED_BINARY: Dict[str, TypedOperatorInfo] = {
    "+": TypedOperatorInfo(
        overloads={
            FuncTypeAnnot([INT, INT], INT): [bc.Opcode.INT_ADD],
            FuncTypeAnnot([NUM, NUM], NUM): [bc.Opcode.NUM_ADD],
            FuncTypeAnnot([STR, STR], STR): [bc.Opcode.STR_CAT],
        }
    ),
    "-": TypedOperatorInfo(
        overloads={
            FuncTypeAnnot([INT, INT], INT): [bc.Opcode.INT_SUB],
            FuncTypeAnnot([NUM, NUM], NUM): [bc.Opcode.NUM_SUB],
        }
    ),
    "*": TypedOperatorInfo(
        overloads={
            FuncTypeAnnot([INT, INT], INT): [bc.Opcode.INT_MUL],
            FuncTypeAnnot([NUM, NUM], NUM): [bc.Opcode.NUM_MUL],
        }
    ),
    "/": TypedOperatorInfo(
        overloads={
            FuncTypeAnnot([INT, INT], INT): [bc.Opcode.INT_DIV],
            FuncTypeAnnot([NUM, NUM], NUM): [bc.Opcode.NUM_DIV],
        }
    ),
    "<": TypedOperatorInfo(
        overloads={
            FuncTypeAnnot([INT, INT], BOOL): [bc.Opcode.INT_LESS],
            FuncTypeAnnot([NUM, NUM], BOOL): [bc.Opcode.NUM_LESS],
        }
    ),
    ">": TypedOperatorInfo(
        overloads={
            FuncTypeAnnot([INT, INT], BOOL): [bc.Opcode.INT_GREATER],
            FuncTypeAnnot([NUM, NUM], BOOL): [bc.Opcode.NUM_GREATER],
        }
    ),
    "<=": TypedOperatorInfo(
        overloads={
            FuncTypeAnnot([INT, INT], BOOL): [bc.Opcode.INT_GREATER, bc.Opcode.NOT],
            FuncTypeAnnot([NUM, NUM], BOOL): [bc.Opcode.NUM_GREATER, bc.Opcode.NOT],
        }
    ),
    ">=": TypedOperatorInfo(
        overloads={
            FuncTypeAnnot([INT, INT], BOOL): [bc.Opcode.INT_LESS, bc.Opcode.NOT],
            FuncTypeAnnot([NUM, NUM], BOOL): [bc.Opcode.NUM_LESS, bc.Opcode.NOT],
        }
    ),
}
UNTYPED_BINARY: Dict[str, UntypedOperatorInfo] = {
    "==": UntypedOperatorInfo(return_type=BOOL, opcodes=[bc.Opcode.EQUAL]),
    "!=": UntypedOperatorInfo(
        return_type=BOOL, opcodes=[bc.Opcode.EQUAL, bc.Opcode.NOT]
    ),
}
TYPED_UNARY: Dict[str, TypedOperatorInfo] = {
    "-": TypedOperatorInfo(
        overloads={
            FuncTypeAnnot([INT], INT): [bc.Opcode.INT_NEG],
            FuncTypeAnnot([NUM], NUM): [bc.Opcode.NUM_NEG],
        }
    )
}
UNTYPED_UNARY: Dict[str, UntypedOperatorInfo] = {}

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
