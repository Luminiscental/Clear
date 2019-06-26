#ifndef clearvm_bytecode_h
#define clearvm_bytecode_h

#include "common.h"

typedef enum {

    CONST_INT = 0,
    CONST_NUM = 1,
    CONST_STR = 2,
    CONST_COUNT = 3

} ConstantType;

typedef enum {

    // Constant generation
    OP_PUSH_CONST = 0,
    OP_PUSH_TRUE = 1,
    OP_PUSH_FALSE = 2,
    OP_PUSH_NIL = 3,

    // Variables
    OP_SET_GLOBAL = 4,
    OP_PUSH_GLOBAL = 5,
    OP_SET_LOCAL = 6,
    OP_PUSH_LOCAL = 7,

    // Built-ins
    OP_INT = 8,
    OP_BOOL = 9,
    OP_NUM = 10,
    OP_STR = 11,
    OP_CLOCK = 12,
    OP_PRINT = 13,

    // Actions
    OP_POP = 14,

    // Arithmetic operators
    OP_INT_NEG = 15,
    OP_NUM_NEG = 16,
    OP_INT_ADD = 17,
    OP_NUM_ADD = 18,
    OP_INT_SUB = 19,
    OP_NUM_SUB = 20,
    OP_INT_MUL = 21,
    OP_NUM_MUL = 22,
    OP_INT_DIV = 23,
    OP_NUM_DIV = 24,
    OP_STR_CAT = 25,
    OP_NOT = 26,

    // Comparison operators
    OP_INT_LESS = 27,
    OP_NUM_LESS = 28,
    OP_INT_GREATER = 29,
    OP_NUM_GREATER = 30,
    OP_EQUAL = 31,

    // Control flow
    OP_JUMP = 32,
    OP_JUMP_IF_FALSE = 33,
    OP_LOOP = 34,

    // Functions
    OP_FUNCTION = 35,
    OP_CALL = 36,
    OP_LOAD_IP = 37,
    OP_LOAD_FP = 38,
    OP_SET_RETURN = 39,
    OP_PUSH_RETURN = 40,

    // Structs
    OP_STRUCT = 41,
    OP_GET_FIELD = 42,
    OP_EXTRACT_FIELD = 43,
    OP_SET_FIELD = 44,
    OP_UNSTRUCT = 45,

    // Upvalues
    OP_REF_LOCAL = 46,
    OP_DEREF = 47,
    OP_SET_REF = 48,

    OP_COUNT = 49

} OpCode;

Result disassembleCode(uint8_t *code, size_t length);

#endif
