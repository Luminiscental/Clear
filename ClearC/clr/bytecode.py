"""
Contains classes/functions for describing and assembling Clear bytecode.
"""

from typing import Union, Tuple, Sequence, Iterable, NamedTuple

import struct
import enum


class IndexTooLargeError(Exception):
    """
    Custom exception class raised when assembling code which contains indices that don't fit
    in a byte.
    """


class NegativeIndexError(Exception):
    """
    Custom exception class raised when assembling code which contains negative indices.
    """


@enum.unique
class ValueType(enum.Enum):
    """
    Enumerates the value types of the vm.
    """

    BOOL = 0
    NIL = 1
    OBJ = 2
    INT = 3
    NUM = 4
    IP = 5
    FP = 6

    def __str__(self) -> str:
        return f"VAL_{self.name}"


@enum.unique
class ObjectType(enum.Enum):
    """
    Enumerates the object types of the vm.
    """

    STRING = 0
    STRUCT = 1
    UPVALUE = 2

    def __str__(self) -> str:
        return f"OBJ_{self.name}"


@enum.unique
class ConstantType(enum.Enum):
    """
    Enumerates all constant types for the constant header. The value is the byte that
    represents them.

    __str__ mirrors the naming convention used in the vm.
    """

    INT = 0
    NUM = 1
    STR = 2

    def __str__(self) -> str:
        return f"CONST_{self.name}"


PackedConstant = Tuple[ConstantType, bytearray]


class ClrInt(NamedTuple):
    """
    Wrapper class for an int constant to have type strict equality.
    """

    unboxed: int

    def __eq__(self, other: object) -> bool:
        if isinstance(other, (ClrNum, ClrStr)):
            return False
        if isinstance(other, ClrInt):
            return self.unboxed == other.unboxed
        return NotImplemented

    def pack(self) -> PackedConstant:
        """
        Pack the constant into its assembly.
        """
        return ConstantType.INT, bytearray(struct.pack("i", self.unboxed))


class ClrNum(NamedTuple):
    """
    Wrapper class for a num constant to have type strict equality.
    """

    unboxed: float

    def __eq__(self, other: object) -> bool:
        if isinstance(other, (ClrInt, ClrStr)):
            return False
        if isinstance(other, ClrNum):
            return self.unboxed == other.unboxed
        return NotImplemented

    def pack(self) -> PackedConstant:
        """
        Pack the constant into its assembly.
        """
        return ConstantType.NUM, bytearray(struct.pack("d", self.unboxed))


class ClrStr(NamedTuple):
    """
    Wrapper class for a str constant to have type strict equality.
    """

    unboxed: str

    def __eq__(self, other: object) -> bool:
        if isinstance(other, (ClrInt, ClrNum)):
            return False
        if isinstance(other, ClrStr):
            return self.unboxed == other.unboxed
        return NotImplemented

    def pack(self) -> PackedConstant:
        """
        Pack the constant into its assembly.
        """
        arr = bytearray()
        arr.append(len(self.unboxed))
        arr.extend(self.unboxed.encode())
        return ConstantType.STR, arr


Constant = Union[ClrInt, ClrNum, ClrStr]


def assemble_header(constants: Sequence[PackedConstant]) -> bytearray:
    """
    Takes a sequence of packed constants and assembles a Clear constant header from them.
    """
    if len(constants) > 255:
        raise IndexTooLargeError
    result = bytearray()
    result.append(len(constants))
    for (constant_type, constant_packed) in constants:
        result.append(constant_type.value)
        result.extend(constant_packed)
    return result


@enum.unique
class Opcode(enum.Enum):
    """
    Enumerates all opcodes, the value is the byte that represents them.

    __str__ mirrors the naming convention used in the vm.
    """

    PUSH_CONST = 0
    PUSH_TRUE = 1
    PUSH_FALSE = 2
    PUSH_NIL = 3
    SET_GLOBAL = 4
    PUSH_GLOBAL = 5
    SET_LOCAL = 6
    PUSH_LOCAL = 7
    INT = 8
    BOOL = 9
    NUM = 10
    STR = 11
    CLOCK = 12
    PRINT = 13
    POP = 14
    SQUASH = 15
    INT_NEG = 16
    NUM_NEG = 17
    INT_ADD = 18
    NUM_ADD = 19
    INT_SUB = 20
    NUM_SUB = 21
    INT_MUL = 22
    NUM_MUL = 23
    INT_DIV = 24
    NUM_DIV = 25
    STR_CAT = 26
    NOT = 27
    INT_LESS = 28
    NUM_LESS = 29
    INT_GREATER = 30
    NUM_GREATER = 31
    EQUAL = 32
    JUMP = 33
    JUMP_IF_FALSE = 34
    LOOP = 35
    FUNCTION = 36
    CALL = 37
    LOAD_IP = 38
    LOAD_FP = 39
    SET_RETURN = 40
    PUSH_RETURN = 41
    STRUCT = 42
    DESTRUCT = 43
    GET_FIELD = 44
    EXTRACT_FIELD = 45
    SET_FIELD = 46
    REF_LOCAL = 47
    DEREF = 48
    SET_REF = 49
    IS_VAL_TYPE = 50
    IS_OBJ_TYPE = 51

    def __str__(self) -> str:
        return "OP_" + self.name


Instruction = Union[Opcode, int]


def size(instructions: Iterable[Instruction]) -> int:
    """
    Returns the size in bytes of an iterable of instructions after assembly.
    """
    # Currently redundant (equal to len) because everything is 1 byte
    result = 0
    for instruction in instructions:
        if isinstance(instruction, Opcode):
            result += 1
        else:
            result += 1
    return result


def assemble_code(
    constants: Sequence[Constant], instructions: Iterable[Instruction]
) -> bytearray:
    """
    Takes a sequence of constants and an iterable of instructions and assembles them into a
    Clear bytecode program.
    """
    result = assemble_header([constant.pack() for constant in constants])
    for instruction in instructions:
        if isinstance(instruction, Opcode):
            result.append(instruction.value)
        else:
            if instruction > 255:
                raise IndexTooLargeError
            if instruction < 0:
                raise NegativeIndexError
            result.append(instruction)
    return result
