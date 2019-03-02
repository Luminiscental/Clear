#ifndef clearvm_chunk_h
#define clearvm_chunk_h

#include "common.h"
#include "value.h"

typedef struct sVM VM;

typedef enum {

    OP_STORE_CONST = 0,
    OP_NUMBER = 1,
    OP_STRING = 2,
    OP_PRINT = 3,
    OP_LOAD_CONST = 4,
    OP_NEGATE = 5,
    OP_ADD = 6,
    OP_SUBTRACT = 7,
    OP_MULTIPLY = 8,
    OP_DIVIDE = 9,
    OP_RETURN = 10,
    OP_POP = 11,
    OP_DEFINE_GLOBAL = 12,
    OP_TRUE = 13,
    OP_FALSE = 14,
    OP_NOT = 15,
    OP_LESS = 16,
    OP_NLESS = 17,
    OP_GREATER = 18,
    OP_NGREATER = 19,
    OP_EQUAL = 20,
    OP_NEQUAL = 21,
    OP_LOAD_GLOBAL = 22,
    OP_PRINT_BLANK = 23,
    OP_TYPE = 24,
    OP_INTEGER = 25,
    OP_INT = 26,
    OP_BOOL = 27,
    OP_NUM = 28,
    OP_STR = 29

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
