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

    // Built-ins
    OP_TYPE = 9,
    OP_INT = 10,
    OP_BOOL = 11,
    OP_NUM = 12,
    OP_STR = 13,

    // Statements
    OP_PRINT = 14,
    OP_PRINT_BLANK = 15,
    OP_RETURN = 16,
    OP_POP = 17,

    // Arithmetic operators
    OP_NEGATE = 18,
    OP_ADD = 19,
    OP_SUBTRACT = 20,
    OP_MULTIPLY = 21,
    OP_DIVIDE = 22,

    // Comparison operators
    OP_LESS = 23,
    OP_NLESS = 24,
    OP_GREATER = 25,
    OP_NGREATER = 26,
    OP_EQUAL = 27,
    OP_NEQUAL = 28,

    // Boolean operators
    OP_NOT = 29

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
