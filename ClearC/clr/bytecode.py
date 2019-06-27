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
        return "CONST_" + self.name


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
    INT_NEG = 15
    NUM_NEG = 16
    INT_ADD = 17
    NUM_ADD = 18
    INT_SUB = 19
    NUM_SUB = 20
    INT_MUL = 21
    NUM_MUL = 22
    INT_DIV = 23
    NUM_DIV = 24
    STR_CAT = 25
    NOT = 26
    INT_LESS = 27
    NUM_LESS = 28
    INT_GREATER = 29
    NUM_GREATER = 30
    EQUAL = 31
    JUMP = 32
    JUMP_IF_FALSE = 33
    LOOP = 34
    FUNCTION = 35
    CALL = 36
    LOAD_IP = 37
    LOAD_FP = 38
    SET_RETURN = 39
    PUSH_RETURN = 40
    STRUCT = 41
    GET_FIELD = 42
    EXTRACT_FIELD = 43
    SET_FIELD = 44
    UNSTRUCT = 45
    REF_LOCAL = 46
    DEREF = 47
    SET_REF = 48

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
