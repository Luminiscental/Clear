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
    OP_SQUASH = 15,

    // Arithmetic operators
    OP_INT_NEG = 16,
    OP_NUM_NEG = 17,
    OP_INT_ADD = 18,
    OP_NUM_ADD = 19,
    OP_INT_SUB = 20,
    OP_NUM_SUB = 21,
    OP_INT_MUL = 22,
    OP_NUM_MUL = 23,
    OP_INT_DIV = 24,
    OP_NUM_DIV = 25,
    OP_STR_CAT = 26,
    OP_NOT = 27,

    // Comparison operators
    OP_INT_LESS = 28,
    OP_NUM_LESS = 29,
    OP_INT_GREATER = 30,
    OP_NUM_GREATER = 31,
    OP_EQUAL = 32,

    // Control flow
    OP_JUMP = 33,
    OP_JUMP_IF_FALSE = 34,
    OP_LOOP = 35,

    // Functions
    OP_FUNCTION = 36,
    OP_CALL = 37,
    OP_LOAD_IP = 38,
    OP_LOAD_FP = 39,
    OP_SET_RETURN = 40,
    OP_PUSH_RETURN = 41,

    // Structs
    OP_STRUCT = 42,
    OP_DESTRUCT = 43,
    OP_GET_FIELD = 44,
    OP_EXTRACT_FIELD = 45,
    OP_SET_FIELD = 46,
    OP_INSERT_FIELD = 47,

    // Upvalues
    OP_REF_LOCAL = 48,
    OP_DEREF = 49,
    OP_SET_REF = 50,

    // Types
    OP_IS_VAL_TYPE = 51,
    OP_IS_OBJ_TYPE = 52,

    OP_COUNT = 53

} OpCode;

Result disassembleCode(uint8_t *code, size_t length);

#endif
