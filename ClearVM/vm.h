#ifndef clearvm_vm_h
#define clearvm_vm_h

#include "chunk.h"
#include "value.h"

#define STACK_MAX 256

typedef struct {

    Chunk *chunk;
    uint8_t *ip;
    Value stack[STACK_MAX];
    Value *stackTop;

} VM;

typedef enum {

    INTERPRET_OK,
    INTERPRET_ERR

} InterpretResult;

void initVM(VM *vm);
void resetStack(VM *vm);
void push(VM *vm, Value value);
Value pop(VM *vm);
void freeVM(VM *vm);

InterpretResult interpret(VM *vm, Chunk *chunk);
InterpretResult run(VM *vm);

#endif
