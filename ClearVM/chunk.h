#ifndef clearvm_chunk_h
#define clearvm_chunk_h

#include "common.h"
#include "value.h"

typedef enum {

    OP_STORE_CONST = 0,
    OP_NUMBER = 1,
    OP_PRINT = 2,
    OP_LOAD_CONST = 3

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
