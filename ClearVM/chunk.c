
#include "chunk.h"

#include <stdlib.h>
#include <stdio.h>
#include <memory.h>

#include "memory.h"

void initChunk(Chunk *chunk) {

    chunk->count = 0;
    chunk->capacity = 0;
    chunk->code = NULL;
    initValueArray(&chunk->constants);
}

void writeChunk(Chunk *chunk, uint8_t byte) {

    if (chunk->capacity < chunk->count + 1) {

        int oldCapacity = chunk->capacity;
        chunk->capacity = GROW_CAPACITY(oldCapacity);
        chunk->code = GROW_ARRAY(chunk->code, uint8_t, oldCapacity,
                chunk->capacity);
    }

    chunk->code[chunk->count] = byte;
    chunk->count++;
}

int addConstant(Chunk *chunk, Value value) {

    writeValueArray(&chunk->constants, value);
    return chunk->constants.count - 1;
}

static uint32_t storeConstant(VM *vm, Chunk *chunk, uint32_t offset) {

#ifdef DEBUG_DIS

    printf("%04d %-16s ", offset, "OP_STORE_CONST");

#endif

    uint32_t result = offset + 2;

    if (result > chunk->count) {

        printf("|| EOF reached during constant value!\n");
        return chunk->count;
    }

    uint8_t type = chunk->code[offset + 1];

    switch (type) {

         case OP_INTEGER: {

            int32_t *value = (int32_t*)(chunk->code + result);

            if (result + sizeof(int32_t) > chunk->count) {

                printf("|| EOF reached during constant value!\n");
                return chunk->count;
            }

            printf("OP_INTEGER '%d'\n", *value);

            addConstant(chunk, makeInteger(*value));
            return result + sizeof(int32_t);
    
        } break;
   
        case OP_NUMBER: {
    
            double *value = (double*)(chunk->code + result);

            if (result + sizeof(double) > chunk->count) {

                printf("|| EOF reached during constant value!\n");
                return chunk->count;
            }

            printf("OP_NUMBER '%g'\n", *value);

            addConstant(chunk, makeNumber(*value));
            return result + sizeof(double);
    
        } break;

        case OP_STRING: {

            if (result + 1 > chunk->count) {

                printf("|| EOF reached during constant value!\n");
                return chunk->count;
            }
        
            uint8_t size = chunk->code[result];

            if (result + 1 + size > chunk->count) {

                printf("|| EOF reached during constant value!\n");
                return chunk->count;
            }

            char *string = ALLOCATE(char, size + 1);
            string[size] = '\0';
            memcpy(string, chunk->code + result + 1, size);

            printf("OP_STRING '%s'\n", string);

            addConstant(chunk, makeString(vm, size, string));
            return result + 1 + size;
        
        } break;

        default: {

            printf("|| Unrecognized constant type %d\n", type);
            return result;

        } break;
    }
}

void loadConstants(VM *vm, Chunk *chunk) {

    for (uint32_t offset = 0; offset < chunk->count;) {

        uint8_t instruction = chunk->code[offset];

        if (instruction != OP_STORE_CONST) {

            chunk->start = offset;
            return;
        }

        offset = storeConstant(vm, chunk, offset);
    }
}

void freeChunk(Chunk *chunk) {

    freeValueArray(&chunk->constants);
    FREE_ARRAY(uint8_t, chunk->code, chunk->capacity);
    initChunk(chunk);
}

void disassembleChunk(Chunk *chunk, const char *name) {

    printf("== %s ==\n", name);

    for (uint32_t offset = chunk->start; offset < chunk->count;) {

        offset = disassembleInstruction(chunk, offset);
    }
}

static uint32_t simpleInstruction(const char *name, uint32_t offset) {

    printf("%s\n", name);
    return offset + 1;
}

static uint32_t constantInstruction(const char *name, Chunk *chunk, uint32_t offset) {

    if (offset + 2 > chunk->count) {

        printf("|| EOF reached during constant instruction!\n");
        return chunk->count;
    }

    uint8_t constant = chunk->code[offset + 1];

    printf("%-16s %4d '", name, constant);
    printValue(chunk->constants.values[constant], false);
    printf("'\n");
    return offset + 2;
}

static uint32_t indexInstruction(const char *name, Chunk *chunk, uint32_t offset) {

    if (offset + 2 > chunk->count) {

        printf("|| EOF reached during index instruction!\n");
        return chunk->count;
    }

    uint8_t index = chunk->code[offset + 1];

    printf("%-16s %4d\n", name, index);
    return offset + 2;
}

uint32_t disassembleInstruction(Chunk *chunk, uint32_t offset) {
    
    printf("%04d ", offset);

    if (offset >= chunk->count) {

        printf("|| EOF reached during instruction!\n");
        return chunk->count;
    }

    uint8_t instruction = *(chunk->code + offset);

    switch (instruction) {

        case OP_TYPE: {

            return simpleInstruction("OP_TYPE", offset);

        } break;

        case OP_PRINT: {
        
            return simpleInstruction("OP_PRINT", offset);
        
        } break;

        case OP_PRINT_BLANK: {

            return simpleInstruction("OP_PRINT_BLANK", offset);

        } break;

        case OP_LOAD_CONST: {
        
            return constantInstruction("OP_LOAD_CONST", chunk, offset);
        
        } break;

        case OP_NEGATE: {
        
            return simpleInstruction("OP_NEGATE", offset);
        
        } break;

        case OP_ADD: {
        
            return simpleInstruction("OP_ADD", offset);
        
        } break;

        case OP_SUBTRACT: {
        
            return simpleInstruction("OP_SUBTRACT", offset);
        
        } break;

        case OP_MULTIPLY: {
        
            return simpleInstruction("OP_MULTIPLY", offset);
        
        } break;

        case OP_DIVIDE: {
        
            return simpleInstruction("OP_DIVIDE", offset);
        
        } break;
    
        case OP_RETURN: {
    
            return simpleInstruction("OP_RETURN", offset);
    
        } break;

        case OP_POP: {
        
            return simpleInstruction("OP_POP", offset);
        
        } break;

        case OP_DEFINE_GLOBAL: {
        
            return indexInstruction("OP_DEFINE_GLOBAL", chunk, offset);
        
        } break;

        case OP_TRUE: {
        
            return simpleInstruction("OP_TRUE", offset);
        
        } break;

        case OP_FALSE: {
        
            return simpleInstruction("OP_FALSE", offset);
        
        } break;

        case OP_NOT: {
        
            return simpleInstruction("OP_NOT", offset);
        
        } break;

        case OP_LESS: {
        
            return simpleInstruction("OP_LESS", offset);
        
        } break;

        case OP_NLESS: {
        
            return simpleInstruction("OP_NLESS", offset);
        
        } break;

        case OP_GREATER: {
        
            return simpleInstruction("OP_GREATER", offset);
        
        } break;

        case OP_NGREATER: {
        
            return simpleInstruction("OP_NGREATER", offset);
        
        } break;

        case OP_EQUAL: {
        
            return simpleInstruction("OP_EQUAL", offset);
        
        } break;

        case OP_NEQUAL: {
        
            return simpleInstruction("OP_NEQUAL", offset);
        
        } break;

        case OP_LOAD_GLOBAL: {
        
            return indexInstruction("OP_LOAD_GLOBAL", chunk, offset);
        
        } break;

        default: {
        
            printf("\nUnknown opcode %d\n", instruction);
            return offset + 1;
        
        } break;
    }
}

