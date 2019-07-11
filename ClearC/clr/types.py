"""
Module defining the type system.
"""

from typing import NamedTuple, Set, List, Iterable, Optional, Any, Dict

import enum
import dataclasses as dc

# Module import for type annotations
from clr import ast  # pylint: disable=unused-import

import clr.util as util
import clr.bytecode as bc


class UnitType:
    """
    Base class for a unit type.
    """

    def valid(self) -> bool:
        """
        Returns true if this is a valid type for a value.
        """
        raise NotImplementedError


class UnresolvedType(UnitType):
    """
    Represents an unresolved type.
    """

    def __str__(self) -> str:
        return "<unresolved>"

    def __hash__(self) -> int:
        return 37

    def __eq__(self, other: object) -> bool:
        if isinstance(other, UnresolvedType):
            return True
        if isinstance(other, (BuiltinType, StructType, FunctionType, TupleType)):
            return False
        return NotImplemented

    def __ne__(self, other: object) -> bool:
        if isinstance(
            other, (UnresolvedType, BuiltinType, StructType, FunctionType, TupleType)
        ):
            return not self == other
        return NotImplemented

    def valid(self) -> bool:
        return False


@enum.unique
class BuiltinType(UnitType, enum.Enum):
    """
    Enumerates the builtin unit types.
    """

    NIL = "nil"
    VOID = "void"
    INT = "int"
    BOOL = "bool"
    NUM = "num"
    STR = "str"

    @staticmethod
    def get(name: str) -> "Type":
        """
        Get a builtin type by name.
        """
        return Type({BuiltinType(name)})

    def __str__(self) -> str:
        return str(self.value)

    def __hash__(self) -> int:
        return hash(self.value)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, BuiltinType):
            return super().__eq__(other)
        if isinstance(other, (UnresolvedType, StructType, FunctionType, TupleType)):
            return False
        return NotImplemented

    def __ne__(self, other: object) -> bool:
        if isinstance(
            other, (UnresolvedType, BuiltinType, StructType, FunctionType, TupleType)
        ):
            return not self == other
        return NotImplemented

    def valid(self) -> bool:
        return self != BuiltinType.VOID


@dc.dataclass
class StructType(UnitType):
    """
    Represents a struct type.
    """

    ref: "ast.AstStructDecl"

    @staticmethod
    def make(ref: "ast.AstStructDecl") -> "Type":
        """
        Make a struct type. Wraps the constructor.
        """
        return Type({StructType(ref)})

    def __str__(self) -> str:
        return self.ref.name

    def __hash__(self) -> int:
        return hash(str(self.ref))

    def __eq__(self, other: object) -> bool:
        if isinstance(other, StructType):
            return self.ref == other.ref
        if isinstance(other, (UnresolvedType, BuiltinType, FunctionType, TupleType)):
            return False
        return NotImplemented

    def __ne__(self, other: object) -> bool:
        if isinstance(
            other, (UnresolvedType, BuiltinType, StructType, FunctionType, TupleType)
        ):
            return not self == other
        return NotImplemented

    def valid(self) -> bool:
        return True


@dc.dataclass
class FunctionType(UnitType):
    """
    Represents a function type.
    """

    parameters: List["Type"]
    return_type: "Type"

    @staticmethod
    def make(parameters: List["Type"], return_type: "Type") -> "Type":
        """
        Make a function type. Wraps the constructor.
        """
        return Type({FunctionType(parameters, return_type)})

    def __str__(self) -> str:
        params = ", ".join(str(param) for param in self.parameters)
        return f"func({params}) {self.return_type}"

    def __hash__(self) -> int:
        return hash(tuple(self.parameters)) ^ hash(self.return_type)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, FunctionType):
            return (
                self.parameters == other.parameters
                and self.return_type == other.return_type
            )
        if isinstance(other, (UnresolvedType, BuiltinType, StructType, TupleType)):
            return False
        return NotImplemented

    def __ne__(self, other: object) -> bool:
        if isinstance(
            other, (UnresolvedType, BuiltinType, StructType, FunctionType, TupleType)
        ):
            return not self == other
        return NotImplemented

    def valid(self) -> bool:
        return all(valid(param) for param in self.parameters) and (
            valid(self.return_type) or self.return_type == BuiltinType.VOID
        )


@dc.dataclass
class TupleType(UnitType):
    """
    Represents a tuple type.
    """

    elements: List["Type"]

    @staticmethod
    def make(elements: List["Type"]) -> "Type":
        """
        Make a tuple type. Wraps the constructor.
        """
        return Type({TupleType(elements)})

    def __str__(self) -> str:
        inner = ", ".join(str(elem) for elem in self.elements)
        return f"({inner})"

    def __hash__(self) -> int:
        return hash(tuple(self.elements))

    def __eq__(self, other: object) -> bool:
        if isinstance(other, TupleType):
            return self.elements == other.elements
        if isinstance(other, (UnresolvedType, BuiltinType, StructType, FunctionType)):
            return False
        return NotImplemented

    def __ne__(self, other: object) -> bool:
        if isinstance(
            other, (UnresolvedType, BuiltinType, StructType, FunctionType, TupleType)
        ):
            return not self == other
        return NotImplemented

    def valid(self) -> bool:
        return all(valid(elem) for elem in self.elements)


class Type:
    """
    Class representing the type of a value, with a set of subtypes.
    """

    def __init__(self, units: Set[UnitType], is_any: bool = False) -> None:
        self.units = units
        self.contract()
        self.is_any = is_any

    def __str__(self) -> str:
        if self.is_any:
            return "anything"
        if BuiltinType.NIL in self.units:
            target = " | ".join(
                str(unit) for unit in self.units if unit != BuiltinType.NIL
            )
            return f"({target})?"
        return " | ".join(f"({unit})" for unit in self.units)

    def __hash__(self) -> int:
        return hash(tuple(self.units))

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Type):
            return self.is_any or self.units == other.units
        if isinstance(
            other, (UnresolvedType, BuiltinType, StructType, FunctionType, TupleType)
        ):
            return self.is_any or len(self.units) == 1 and other in self.units
        return NotImplemented

    def __ne__(self, other: object) -> bool:
        if isinstance(
            other,
            (Type, UnresolvedType, BuiltinType, StructType, FunctionType, TupleType),
        ):
            return not self == other
        return NotImplemented

    def _get_as(self, kind: type) -> Optional[Any]:
        if len(self.units) != 1:
            return None
        unit = next(iter(self.units))
        if isinstance(unit, kind):
            return unit
        return None

    def get_struct(self) -> Optional[StructType]:
        """
        Returns a unit struct type if this is a unit struct type.
        """
        return self._get_as(StructType)

    def get_tuple(self) -> Optional[TupleType]:
        """
        Returns a unit tuple type if this is a unit tuple type.
        """
        return self._get_as(TupleType)

    def get_function(self) -> Optional[FunctionType]:
        """
        Returns a unit function type if this is a unit function type.
        """
        return self._get_as(FunctionType)

    def contract(self) -> None:
        """
        Simplify the union type.
        """
        if len(self.units) <= 1:
            return
        rest = self.units
        # Take out functions and tuples
        functions, rest = util.split_instances(FunctionType, rest)
        tuples, rest = util.split_instances(TupleType, rest)
        # Contract functions
        function_groups = util.group_by(
            lambda function: len(function.parameters), functions
        )
        for param_count, function_group in function_groups.items():
            union_return = union(function.return_type for function in function_group)
            union_params = [
                intersection(function.parameters[i] for function in function_group)
                for i in range(param_count)
            ]
            rest.add(FunctionType(union_params, union_return))
        # Contract tuples
        tuple_groups = util.group_by(
            lambda tuple_type: len(tuple_type.elements), tuples
        )
        for element_count, tuple_group in tuple_groups.items():
            union_elements = [
                union(tuple_type.elements[i] for tuple_type in tuple_group)
                for i in range(element_count)
            ]
            rest.add(TupleType(union_elements))
        # Apply the contractions
        self.units = rest


def union(types: Iterable[Type]) -> Type:
    """
    Returns the union of an iterable of types.
    """
    types = list(types)
    if any(subtype.is_any for subtype in types):
        return ANY
    return Type(set.union(*(subtype.units for subtype in types if not subtype.is_any)))


def intersection(types: Iterable[Type]) -> Type:
    """
    Returns the intersection of an iterable of types.
    """
    types = list(types)
    if all(subtype.is_any for subtype in types):
        return ANY
    return Type(
        set.intersection(*(subtype.units for subtype in types if not subtype.is_any))
    )


def difference(lhs: Type, rhs: Type) -> Type:
    """
    Returns the difference between two types.
    """
    if rhs == ANY:
        return Type(set())
    if not rhs.units:
        return lhs
    return Type(set.difference(lhs.units, rhs.units))


def contains(inner: Type, outer: Type) -> bool:
    """
    Returns whether the inner type is a subtype of the outer type.
    """
    return union((inner, outer)) == outer


def valid(check_type: Type) -> bool:
    """
    Checks whether a type is a valid type for a value.
    """
    if not check_type.units:
        return False
    return all(
        not isinstance(unit, UnresolvedType) and unit.valid()
        for unit in check_type.units
    )


NIL = Type({BuiltinType.NIL})
VOID = Type({BuiltinType.VOID})
INT = Type({BuiltinType.INT})
BOOL = Type({BuiltinType.BOOL})
NUM = Type({BuiltinType.NUM})
STR = Type({BuiltinType.STR})
UNRESOLVED = Type({UnresolvedType()})
ANY = Type(set(), is_any=True)


class Builtin(NamedTuple):
    """
    Object for a builtin function specification.
    """

    opcode: bc.Opcode
    type_annot: Type


BUILTINS = {
    "int": Builtin(
        opcode=bc.Opcode.INT,
        type_annot=FunctionType.make(
            parameters=[union((BOOL, INT, NIL, NUM))], return_type=INT
        ),
    ),
    "bool": Builtin(
        opcode=bc.Opcode.BOOL,
        type_annot=FunctionType.make(
            parameters=[union((BOOL, INT, NIL, NUM))], return_type=BOOL
        ),
    ),
    "num": Builtin(
        opcode=bc.Opcode.NUM,
        type_annot=FunctionType.make(
            parameters=[union((BOOL, INT, NIL, NUM))], return_type=NUM
        ),
    ),
    "str": Builtin(
        opcode=bc.Opcode.STR,
        type_annot=FunctionType.make(
            parameters=[union((BOOL, INT, NIL, NUM))], return_type=STR
        ),
    ),
    "clock": Builtin(
        opcode=bc.Opcode.CLOCK,
        type_annot=FunctionType.make(parameters=[], return_type=NUM),
    ),
}


class TypedOperatorInfo(NamedTuple):
    """
    Named tuple for information about an operator with strict operand typing.
    """

    overloads: Dict[FunctionType, List[bc.Instruction]]


class UntypedOperatorInfo(NamedTuple):
    """
    Named tuple for information about an operator with non-strict operand typing.
    """

    return_type: Type
    opcodes: List[bc.Instruction]


TYPED_OPERATORS: Dict[str, TypedOperatorInfo] = {
    "+": TypedOperatorInfo(
        overloads={
            FunctionType([INT, INT], INT): [bc.Opcode.INT_ADD],
            FunctionType([NUM, NUM], NUM): [bc.Opcode.NUM_ADD],
            FunctionType([STR, STR], STR): [bc.Opcode.STR_CAT],
        }
    ),
    "-": TypedOperatorInfo(
        overloads={
            FunctionType([INT, INT], INT): [bc.Opcode.INT_SUB],
            FunctionType([NUM, NUM], NUM): [bc.Opcode.NUM_SUB],
            FunctionType([INT], INT): [bc.Opcode.INT_NEG],
            FunctionType([NUM], NUM): [bc.Opcode.NUM_NEG],
        }
    ),
    "*": TypedOperatorInfo(
        overloads={
            FunctionType([INT, INT], INT): [bc.Opcode.INT_MUL],
            FunctionType([NUM, NUM], NUM): [bc.Opcode.NUM_MUL],
        }
    ),
    "/": TypedOperatorInfo(
        overloads={
            FunctionType([INT, INT], INT): [bc.Opcode.INT_DIV],
            FunctionType([NUM, NUM], NUM): [bc.Opcode.NUM_DIV],
        }
    ),
    "<": TypedOperatorInfo(
        overloads={
            FunctionType([INT, INT], BOOL): [bc.Opcode.INT_LESS],
            FunctionType([NUM, NUM], BOOL): [bc.Opcode.NUM_LESS],
        }
    ),
    ">": TypedOperatorInfo(
        overloads={
            FunctionType([INT, INT], BOOL): [bc.Opcode.INT_GREATER],
            FunctionType([NUM, NUM], BOOL): [bc.Opcode.NUM_GREATER],
        }
    ),
    "<=": TypedOperatorInfo(
        overloads={
            FunctionType([INT, INT], BOOL): [bc.Opcode.INT_GREATER, bc.Opcode.NOT],
            FunctionType([NUM, NUM], BOOL): [bc.Opcode.NUM_GREATER, bc.Opcode.NOT],
        }
    ),
    ">=": TypedOperatorInfo(
        overloads={
            FunctionType([INT, INT], BOOL): [bc.Opcode.INT_LESS, bc.Opcode.NOT],
            FunctionType([NUM, NUM], BOOL): [bc.Opcode.NUM_LESS, bc.Opcode.NOT],
        }
    ),
}
UNTYPED_OPERATORS: Dict[str, UntypedOperatorInfo] = {
    "==": UntypedOperatorInfo(return_type=BOOL, opcodes=[bc.Opcode.EQUAL]),
    "!=": UntypedOperatorInfo(
        return_type=BOOL, opcodes=[bc.Opcode.EQUAL, bc.Opcode.NOT]
    ),
}
