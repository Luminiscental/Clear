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
    OP_TYPE = 11,
    OP_INT = 12,
    OP_BOOL = 13,
    OP_NUM = 14,
    OP_STR = 15,

    // Statements
    OP_PRINT = 16,
    OP_PRINT_BLANK = 17,
    OP_RETURN = 18,
    OP_POP = 19,

    // Arithmetic operators
    OP_NEGATE = 20,
    OP_ADD = 21,
    OP_SUBTRACT = 22,
    OP_MULTIPLY = 23,
    OP_DIVIDE = 24,

    // Comparison operators
    OP_LESS = 25,
    OP_NLESS = 26,
    OP_GREATER = 27,
    OP_NGREATER = 28,
    OP_EQUAL = 29,
    OP_NEQUAL = 30,

    // Boolean operators
    OP_NOT = 31,

    // Scoping
    OP_PUSH_SCOPE = 32,
    OP_POP_SCOPE = 33,

    // Control flow
    OP_JUMP = 34,
    OP_JUMP_IF_NOT = 35,

    // Functions
    OP_LOAD_PARAM = 36,
    OP_BIND_PARAM = 37,
    OP_START_FUNCTION = 38,

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
