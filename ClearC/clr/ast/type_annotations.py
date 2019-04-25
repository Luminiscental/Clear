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
    VOID = "<void>"
    NIL = "<nil>"
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

    def matches(self, other):
        return union_type(self, other) == other


def union_type(a, b):
    # equal types match
    if a == b:
        return a
    # optional types match nil
    if isinstance(a, OptionalTypeAnnotation):
        if b in [a.target, NIL_TYPE]:
            return a
    if isinstance(b, OptionalTypeAnnotation):
        if a in [b.target, NIL_TYPE]:
            return b
    # nil makes things optional
    if a == NIL_TYPE and b != VOID_TYPE:
        return OptionalTypeAnnotation(b)
    if b == NIL_TYPE and a != VOID_TYPE:
        return OptionalTypeAnnotation(a)
    return None


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


class OptionalTypeAnnotation(TypeAnnotation):
    def __init__(self, target):
        super().__init__(TypeAnnotationType.OPTIONAL)
        self.target = target

    def __repr__(self):
        return str(self.target) + "?"

    def __eq__(self, other):
        return isinstance(other, OptionalTypeAnnotation) and self.target == other.target


class FunctionTypeAnnotation(TypeAnnotation):
    def __init__(self, return_type, signature):
        super().__init__(TypeAnnotationType.FUNCTION)
        self.return_type = return_type
        self.signature = signature

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
