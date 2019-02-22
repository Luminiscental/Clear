#ifndef clearvm_vm_h
#define clearvm_vm_h

#include "chunk.h"

typedef struct {

    Chunk *chunk;
    uint8_t *ip;

} VM;

typedef enum {

    INTERPRET_OK,
    INTERPRET_ERR

} InterpretResult;

VM initVM();
InterpretResult interpret(VM *vm, Chunk *chunk);
InterpretResult run(VM *vm);
void freeVM(VM *vm);

#endif
