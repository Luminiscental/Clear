#ifndef clearvm_bytecode_h
#define clearvm_bytecode_h

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
    OP_PRINT_BLANK = 18,
    OP_RETURN = 19,
    OP_RETURN_VOID = 20,
    OP_POP = 21,

    // Arithmetic operators
    OP_NEGATE = 22,
    OP_ADD = 23,
    OP_SUBTRACT = 24,
    OP_MULTIPLY = 25,
    OP_DIVIDE = 26,

    // Comparison operators
    OP_LESS = 27,
    OP_NLESS = 28,
    OP_GREATER = 29,
    OP_NGREATER = 30,
    OP_EQUAL = 31,
    OP_NEQUAL = 32,

    // Boolean operators
    OP_NOT = 33,

    // Scoping
    OP_PUSH_SCOPE = 34,
    OP_POP_SCOPE = 35,

    // Control flow
    OP_JUMP = 36,
    OP_JUMP_IF_NOT = 37,
    OP_LOOP = 38,

    // Functions
    OP_LOAD_PARAM = 39,
    OP_START_FUNCTION = 40,
    OP_CALL = 41,

    // Closures
    OP_CLOSURE = 42,
    OP_LOAD_UPVALUE = 43,
    OP_SET_UPVALUE = 44,

    // Structs
    OP_STRUCT = 45,
    OP_GET_FIELD = 46,
    OP_GET_FIELDS = 47,
    OP_SET_FIELD = 48

} OpCode;

#endif
