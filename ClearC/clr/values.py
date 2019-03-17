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
    # Variables
    DEFINE_GLOBAL = 7
    LOAD_GLOBAL = 8
    DEFINE_LOCAL = 9
    LOAD_LOCAL = 10
    # Built-ins
    INT = 11
    BOOL = 12
    NUM = 13
    STR = 14
    # Statements
    PRINT = 15
    PRINT_BLANK = 16
    RETURN = 17
    POP = 18
    # Arithmetic operators
    NEGATE = 19
    ADD = 20
    SUBTRACT = 21
    MULTIPLY = 22
    DIVIDE = 23
    # Comparison operators
    LESS = 24
    NLESS = 25
    GREATER = 26
    NGREATER = 27
    EQUAL = 28
    NEQUAL = 29
    # Boolean operators
    NOT = 30
    # Scoping
    PUSH_SCOPE = 31
    POP_SCOPE = 32
    # Control flow
    JUMP = 33
    JUMP_IF_NOT = 34
    LOOP = 35
    # Functions
    LOAD_PARAM = 36
    START_FUNCTION = 37
    CALL = 38

    def __str__(self):
        return "OP_" + self.name
