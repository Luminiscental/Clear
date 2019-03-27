#ifndef clearvm_chunk_h
#define clearvm_chunk_h

#include "common.h"
#include "value.h"

typedef struct sVM VM;

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

    // Variables
    OP_DEFINE_GLOBAL = 7,
    OP_LOAD_GLOBAL = 8,
    OP_DEFINE_LOCAL = 9,
    OP_LOAD_LOCAL = 10,

    // Built-ins
    OP_INT = 11,
    OP_BOOL = 12,
    OP_NUM = 13,
    OP_STR = 14,

    // Statements
    OP_PRINT = 15,
    OP_PRINT_BLANK = 16,
    OP_RETURN = 17,
    OP_POP = 18,

    // Arithmetic operators
    OP_NEGATE = 19,
    OP_ADD = 20,
    OP_SUBTRACT = 21,
    OP_MULTIPLY = 22,
    OP_DIVIDE = 23,

    // Comparison operators
    OP_LESS = 24,
    OP_NLESS = 25,
    OP_GREATER = 26,
    OP_NGREATER = 27,
    OP_EQUAL = 28,
    OP_NEQUAL = 29,

    // Boolean operators
    OP_NOT = 30,

    // Scoping
    OP_PUSH_SCOPE = 31,
    OP_POP_SCOPE = 32,

    // Control flow
    OP_JUMP = 33,
    OP_JUMP_IF_NOT = 34,
    OP_LOOP = 35,

    // Functions
    OP_LOAD_PARAM = 36,
    OP_START_FUNCTION = 37,
    OP_CALL = 38,

    // Closures
    OP_CLOSURE = 39,
    OP_LOAD_UPVALUE = 40,
    OP_SET_UPVALUE = 41

} OpCode;

typedef struct {

    uint32_t count;
    uint32_t capacity;
    uint32_t start;
    uint8_t *code;
    ValueArray constants;

} Chunk;

void initChunk(Chunk *chunk);
void writeChunk(Chunk *chunk, uint8_t byte);
int addConstant(Chunk *chunk, Value value);
void freeChunk(Chunk *chunk);

void loadConstants(VM *vm, Chunk *chunk);
void disassembleChunk(Chunk *chunk, const char *name);
uint32_t disassembleInstruction(Chunk *chunk, uint32_t offset);

#endif
