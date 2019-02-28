#ifndef clearvm_chunk_h
#define clearvm_chunk_h

#include "common.h"
#include "value.h"

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
    OP_DEFINE = 12,
    OP_TRUE = 13,
    OP_FALSE = 14,
    OP_NOT = 15,
    OP_LESS = 16,
    OP_NLESS = 17,
    OP_GREATER = 18,
    OP_NGREATER = 19,
    OP_EQUAL = 20,
    OP_NEQUAL = 21,
    OP_LOAD = 22

} OpCode;

typedef struct {

    int count;
    int capacity;
    uint8_t *code;
    ValueArray constants;

} Chunk;

void initChunk(Chunk *chunk);
void writeChunk(Chunk *chunk, uint8_t byte);
int addConstant(Chunk *chunk, Value value);
void freeChunk(Chunk *chunk);

#endif
