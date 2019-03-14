"""
This module provides clr module scope constants such as debug flags
or file format specification values.
"""
from enum import Enum

DEBUG = False
DEBUG_ASSEMBLE = False
DEBUG_PPRINT = False
DEBUG_REPR = False
DONT_COMPILE = False
DONT_RESOLVE = False


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
    TYPE = 11
    INT = 12
    BOOL = 13
    NUM = 14
    STR = 15
    # Statements
    PRINT = 16
    PRINT_BLANK = 17
    RETURN = 18
    POP = 19
    # Arithmetic operators
    NEGATE = 20
    ADD = 21
    SUBTRACT = 22
    MULTIPLY = 23
    DIVIDE = 24
    # Comparison operators
    LESS = 25
    NLESS = 26
    GREATER = 27
    NGREATER = 28
    EQUAL = 29
    NEQUAL = 30
    # Boolean operators
    NOT = 31
    # Scoping
    PUSH_SCOPE = 32
    POP_SCOPE = 33
    # Control flow
    JUMP = 34
    JUMP_IF_NOT = 35
    LOOP = 36
    # Functions
    LOAD_PARAM = 37
    START_FUNCTION = 38
    CALL = 39

    def __str__(self):
        return "OP_" + self.name
