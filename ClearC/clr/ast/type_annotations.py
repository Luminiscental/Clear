from enum import Enum
from collections import namedtuple
from clr.values import OpCode


class TypeAnnotationType(Enum):
    INT = "int"
    NUM = "num"
    STR = "str"
    BOOL = "bool"
    FUNCTION = "<function>"
    UNRESOLVED = "<unresolved>"

    def __str__(self):
        return self.value


class TypeAnnotation:
    def __init__(self, kind=TypeAnnotationType.UNRESOLVED):
        self.kind = kind

    def __str__(self):
        return str(self.kind)

    def __eq__(self, other):
        if not isinstance(other, TypeAnnotation):
            return False
        return self.kind == other.kind


class FunctionTypeAnnotation(TypeAnnotation):
    def __init__(self, return_type, signature):
        super().__init__(TypeAnnotationType.FUNCTION)
        self.return_type = return_type
        self.signature = signature

    def __str__(self):
        return (
            "func(" + ", ".join(map(str, self.signature)) + ") " + str(self.return_type)
        )

    def __eq__(self, other):
        return (
            isinstance(other, FunctionTypeAnnotation)
            and self.return_type == other.return_type
            and self.signature == other.signature
        )


class AnyType:
    def __contains__(self, item):
        return isinstance(item, TypeAnnotation)


ANY_TYPE = AnyType()


INT_TYPE = TypeAnnotation(TypeAnnotationType.INT)
NUM_TYPE = TypeAnnotation(TypeAnnotationType.NUM)
STR_TYPE = TypeAnnotation(TypeAnnotationType.STR)
BOOL_TYPE = TypeAnnotation(TypeAnnotationType.BOOL)

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
