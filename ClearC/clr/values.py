"""
This module provides clr module scope constants such as debug flags
or file format specification values.
"""
from enum import Enum

DEBUG = False
DEBUG_ASSEMBLE = False


class OpCode(Enum):
    """
    This class enumerates the possible opcodes for .clr.b files
    along with their byte values as ints.
    """

    # Constant storage
    STORE_CONST = 0
    INTEGER = 1
    NUMBER = 2
    STRING = 3
    # Constant generation
    LOAD_CONST = 4
    TRUE = 5
    FALSE = 6
    NIL = 7
    # Variables
    DEFINE_GLOBAL = 8
    LOAD_GLOBAL = 9
    DEFINE_LOCAL = 10
    LOAD_LOCAL = 11
    # Built-ins
    INT = 12
    BOOL = 13
    NUM = 14
    STR = 15
    CLOCK = 16
    # Statements
    PRINT = 17
    RETURN = 18
    RETURN_VOID = 19
    POP = 20
    # Arithmetic operators
    INT_NEG = 21
    NUM_NEG = 22
    INT_ADD = 23
    NUM_ADD = 24
    INT_SUB = 25
    NUM_SUB = 26
    INT_MUL = 27
    NUM_MUL = 28
    INT_DIV = 29
    NUM_DIV = 30
    # Comparison operators
    LESS = 31
    NLESS = 32
    GREATER = 33
    NGREATER = 34
    EQUAL = 35
    NEQUAL = 36
    # Boolean operators
    NOT = 37
    # Scoping
    PUSH_SCOPE = 38
    POP_SCOPE = 39
    # Control flow
    JUMP = 40
    JUMP_IF_NOT = 41
    LOOP = 42
    # Functions
    LOAD_PARAM = 43
    START_FUNCTION = 44
    CALL = 45
    # Closures
    CLOSURE = 46
    LOAD_UPVALUE = 47
    SET_UPVALUE = 48
    # Structs
    STRUCT = 49
    GET_FIELD = 50
    SET_FIELD = 51

    def __str__(self):
        return "OP_" + self.name
