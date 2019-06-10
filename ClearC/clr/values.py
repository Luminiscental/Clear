from enum import Enum

DEBUG = False
DEBUG_ASSEMBLE = False


class ConstantType(Enum):
    INT = 0
    NUM = 1
    STR = 2

    def __str__(self):
        return "CONST_" + self.value


class OpCode(Enum):
    # Constant generation
    PUSH_CONST = 0
    PUSH_TRUE = 1
    PUSH_FALSE = 2
    PUSH_NIL = 3
    # Variables
    SET_GLOBAL = 4
    PUSH_GLOBAL = 5
    SET_LOCAL = 6
    PUSH_LOCAL = 7
    # Built-ins
    INT = 8
    BOOL = 9
    NUM = 10
    STR = 11
    CLOCK = 12
    PRINT = 13
    # Actions
    POP = 14
    # Arithmetic operators
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
    # Comparison operators
    INT_LESS = 27
    NUM_LESS = 28
    INT_GREATER = 29
    NUM_GREATER = 30
    EQUAL = 31
    # Control flow
    JUMP = 32
    JUMP_IF_FALSE = 33
    LOOP = 34
    # Functions
    FUNCTION = 35
    CALL = 36
    LOAD_IP = 37
    LOAD_FP = 38
    RETURN = 39
    # Structs
    STRUCT = 40
    GET_FIELD = 41
    SET_FIELD = 42

    def __str__(self):
        return "OP_" + self.name
