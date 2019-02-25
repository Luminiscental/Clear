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
    OP_POP = 11

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
