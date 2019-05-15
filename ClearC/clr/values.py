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
    PRINT_BLANK = 18
    RETURN = 19
    RETURN_VOID = 20
    POP = 21
    # Arithmetic operators
    NEGATE = 22
    ADD = 23
    SUBTRACT = 24
    MULTIPLY = 25
    DIVIDE = 26
    # Comparison operators
    LESS = 27
    NLESS = 28
    GREATER = 29
    NGREATER = 30
    EQUAL = 31
    NEQUAL = 32
    # Boolean operators
    NOT = 33
    # Scoping
    PUSH_SCOPE = 34
    POP_SCOPE = 35
    # Control flow
    JUMP = 36
    JUMP_IF_NOT = 37
    LOOP = 38
    # Functions
    LOAD_PARAM = 39
    START_FUNCTION = 40
    CALL = 41
    # Closures
    CLOSURE = 42
    LOAD_UPVALUE = 43
    SET_UPVALUE = 44
    # Structs
    STRUCT = 45
    GET_FIELD = 46
    GET_FIELDS = 47
    SET_FIELD = 48

    def __str__(self):
        return "OP_" + self.name
