#ifndef clearvm_bytecode_h
#define clearvm_bytecode_h

#include "common.h"

typedef enum {

    // Constant storage
    OP_STORE_CONST = 0,
    OP_INTEGER = 1,
    OP_NUMBER = 2,
    OP_STRING = 3,

    // Constant generation
    OP_LOAD_CONST = 4,
    OP_TRUE = 5,
    OP_FALSE = 6,
    OP_NIL = 7,

    // Variables
    OP_DEFINE_GLOBAL = 8,
    OP_LOAD_GLOBAL = 9,
    OP_DEFINE_LOCAL = 10,
    OP_LOAD_LOCAL = 11,

    // Built-ins
    OP_INT = 12,
    OP_BOOL = 13,
    OP_NUM = 14,
    OP_STR = 15,
    OP_CLOCK = 16,

    // Statements
    OP_PRINT = 17,
    OP_RETURN = 18,
    OP_RETURN_VOID = 19,
    OP_POP = 20,

    // Arithmetic operators
    OP_INT_NEG = 21,
    OP_NUM_NEG = 22,
    OP_INT_ADD = 23,
    OP_NUM_ADD = 24,
    OP_INT_SUB = 25,
    OP_NUM_SUB = 26,
    OP_INT_MUL = 27,
    OP_NUM_MUL = 28,
    OP_INT_DIV = 29,
    OP_NUM_DIV = 30,

    // Comparison operators
    OP_LESS = 31,
    OP_NLESS = 32,
    OP_GREATER = 33,
    OP_NGREATER = 34,
    OP_EQUAL = 35,
    OP_NEQUAL = 36,

    // Boolean operators
    OP_NOT = 37,

    // Scoping
    OP_PUSH_SCOPE = 38,
    OP_POP_SCOPE = 39,

    // Control flow
    OP_JUMP = 40,
    OP_JUMP_IF_NOT = 41,
    OP_LOOP = 42,

    // Functions
    OP_LOAD_PARAM = 43,
    OP_START_FUNCTION = 44,
    OP_CALL = 45,

    // Closures
    OP_CLOSURE = 46,
    OP_LOAD_UPVALUE = 47,
    OP_SET_UPVALUE = 48,

    // Structs
    OP_STRUCT = 49,
    OP_GET_FIELD = 50,
    OP_SET_FIELD = 51,

    OP_COUNT = 52

} OpCode;

Result disassembleCode(uint8_t *code, size_t length);

#endif
