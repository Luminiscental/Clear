from enum import Enum
from collections import namedtuple
from clr.values import OpCode


class TypeAnnotationType(Enum):
    INT = "int"
    NUM = "num"
    STR = "str"
    BOOL = "bool"
    FUNCTION = "<function>"
    OPTIONAL = "<optional>"
    IDENTIFIER = "<identifier>"
    VOID = "void"
    NIL = "nil"
    UNRESOLVED = "<unresolved>"

    def __repr__(self):
        return self.value

    def __str__(self):
        return repr(self)


class TypeAnnotation:
    def __init__(self, kind=TypeAnnotationType.UNRESOLVED):
        self.kind = kind

    def __repr__(self):
        return str(self.kind)

    def __eq__(self, other):
        if not isinstance(other, TypeAnnotation):
            return False
        return self.kind == other.kind

    def __hash__(self):
        return hash(str(self.kind))

    def matches(self, other):
        return union_type(self, other) == other


def symmetric(func):
    def wrapper(first, second):
        return func(first, second) or func(second, first)

    return wrapper


def union_type(first_type, second_type):
    @symmetric
    def get_equal_union(first_type, second_type):
        if first_type == second_type:
            return first_type
        return None

    @symmetric
    def coerce_from_nil(first_type, second_type):
        if isinstance(first_type, OptionalTypeAnnotation):
            if second_type in [first_type.target, NIL_TYPE]:
                return first_type
        return None

    @symmetric
    def coerce_to_optional(first_type, second_type):
        if first_type == NIL_TYPE:
            return OptionalTypeAnnotation(second_type)
        return None

    return (
        get_equal_union(first_type, second_type)
        or coerce_from_nil(first_type, second_type)
        or coerce_to_optional(first_type, second_type)
    )


class IdentifierTypeAnnotation(TypeAnnotation):
    def __init__(self, identifier):
        super().__init__(TypeAnnotationType.IDENTIFIER)
        self.identifier = identifier

    def __repr__(self):
        return str(self.identifier)

    def __eq__(self, other):
        return (
            isinstance(other, IdentifierTypeAnnotation)
            and self.identifier == other.identifier
        )

    def __hash__(self):
        return hash(super()) ^ hash(self.identifier)


class OptionalTypeAnnotation(TypeAnnotation):
    def __init__(self, target):
        super().__init__(TypeAnnotationType.OPTIONAL)
        self.target = target

    def __repr__(self):
        return str(self.target) + "?"

    def __eq__(self, other):
        return isinstance(other, OptionalTypeAnnotation) and self.target == other.target

    def __hash__(self):
        return hash(super()) ^ hash(self.target)


class FunctionTypeAnnotation(TypeAnnotation):
    def __init__(self, return_type, signature, ref):
        super().__init__(TypeAnnotationType.FUNCTION)
        self.return_type = return_type
        self.signature = signature
        self.ref = ref

    def __repr__(self):
        return (
            "func(" + ", ".join(map(str, self.signature)) + ") " + str(self.return_type)
        )

    def __eq__(self, other):
        return (
            isinstance(other, FunctionTypeAnnotation)
            and self.return_type == other.return_type
            and self.signature == other.signature
        )

    def __hash__(self):
        return hash(super()) ^ hash(self.return_type) + 13 * hash(self.signature)


INT_TYPE = TypeAnnotation(TypeAnnotationType.INT)
NUM_TYPE = TypeAnnotation(TypeAnnotationType.NUM)
STR_TYPE = TypeAnnotation(TypeAnnotationType.STR)
BOOL_TYPE = TypeAnnotation(TypeAnnotationType.BOOL)
NIL_TYPE = TypeAnnotation(TypeAnnotationType.NIL)
VOID_TYPE = TypeAnnotation(TypeAnnotationType.VOID)

SIMPLE_TYPES = {"int": INT_TYPE, "num": NUM_TYPE, "str": STR_TYPE, "bool": BOOL_TYPE}

Builtin = namedtuple("Builtin", ("signatures", "opcode", "return_type"))

BUILTINS = {
    "clock": Builtin(signatures=[[]], opcode=OpCode.CLOCK, return_type=NUM_TYPE),
    "int": Builtin(
        signatures=[[INT_TYPE], [NUM_TYPE], [BOOL_TYPE]],
        opcode=OpCode.INT,
        return_type=INT_TYPE,
    ),
    "num": Builtin(
        signatures=[[INT_TYPE], [NUM_TYPE], [BOOL_TYPE]],
        opcode=OpCode.NUM,
        return_type=NUM_TYPE,
    ),
    "str": Builtin(
        signatures=[[INT_TYPE], [NUM_TYPE], [STR_TYPE], [BOOL_TYPE]],
        opcode=OpCode.STR,
        return_type=STR_TYPE,
    ),
    "bool": Builtin(
        signatures=[[INT_TYPE], [NUM_TYPE], [BOOL_TYPE]],
        opcode=OpCode.BOOL,
        return_type=BOOL_TYPE,
    ),
}
