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
    OP_NEGATE = 21,
    OP_ADD = 22,
    OP_SUBTRACT = 23,
    OP_MULTIPLY = 24,
    OP_DIVIDE = 25,

    // Comparison operators
    OP_LESS = 26,
    OP_NLESS = 27,
    OP_GREATER = 28,
    OP_NGREATER = 29,
    OP_EQUAL = 30,
    OP_NEQUAL = 31,

    // Boolean operators
    OP_NOT = 32,

    // Scoping
    OP_PUSH_SCOPE = 33,
    OP_POP_SCOPE = 34,

    // Control flow
    OP_JUMP = 35,
    OP_JUMP_IF_NOT = 36,
    OP_LOOP = 37,

    // Functions
    OP_LOAD_PARAM = 38,
    OP_START_FUNCTION = 39,
    OP_CALL = 40,

    // Closures
    OP_CLOSURE = 41,
    OP_LOAD_UPVALUE = 42,
    OP_SET_UPVALUE = 43,

    // Structs
    OP_STRUCT = 44,
    OP_GET_FIELD = 45,
    OP_SET_FIELD = 46,

    OP_COUNT = 47

} OpCode;

Result disassembleCode(uint8_t *code, size_t length);

#endif
