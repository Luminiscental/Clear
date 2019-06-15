"""
Contains classes/functions for describing and assembling Clear bytecode.
"""

from typing import Union, Tuple, Sequence, Iterable

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


class StringTooLongError(Exception):
    """
    Custom exception class raised when assembling a constant header with a string constant
    whose length is too large to fit in a byte.
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


Constant = Union[int, float, str]
PackedConstant = Tuple[ConstantType, bytearray]


def pack_constant(constant: Constant) -> PackedConstant:
    """
    Takes a python object and packs it as a Clear constant.
    """
    if isinstance(constant, int):
        return (ConstantType.INT, bytearray(struct.pack("i", constant)))

    if isinstance(constant, float):
        return (ConstantType.NUM, bytearray(struct.pack("d", constant)))

    if len(constant) > 255:
        raise StringTooLongError()
    arr = bytearray()
    arr.append(len(constant))
    arr.extend(constant.encode())
    return (ConstantType.STR, arr)


def assemble_header(constants: Sequence[PackedConstant]) -> bytearray:
    """
    Takes a sequence of packed constants and assembles a Clear constant header from them.
    """
    if len(constants) > 255:
        raise IndexTooLargeError()
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
    REF_LOCAL = 45
    DEREF = 46
    SET_REF = 47

    def __str__(self) -> str:
        return "OP_" + self.name


Instruction = Union[Opcode, int]


def assemble_code(
    constants: Sequence[Constant], instructions: Iterable[Instruction]
) -> bytearray:
    """
    Takes a sequence of constants and an iterable of instructions and assembles them into a
    Clear bytecode program.
    """
    result = assemble_header([pack_constant(constant) for constant in constants])
    for instruction in instructions:
        if isinstance(instruction, Opcode):
            result.append(instruction.value)
        else:
            if instruction > 255:
                raise IndexTooLargeError()
            elif instruction < 0:
                raise NegativeIndexError()
            result.append(instruction)
    return result
