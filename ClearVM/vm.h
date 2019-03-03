#ifndef clearvm_vm_h
#define clearvm_vm_h

#include "chunk.h"
#include "table.h"
#include "value.h"

#define STACK_MAX 256

typedef struct sVM {

    Chunk *chunk;
    uint8_t *ip;
    Value stack[STACK_MAX];
    Value *stackTop;
    Table strings;
    Obj *objects;
    Table globals;

} VM;

typedef enum {

    INTERPRET_OK,
    INTERPRET_ERR

} InterpretResult;

void initVM(VM *vm);
void resetStack(VM *vm);
InterpretResult push(VM *vm, Value value);
InterpretResult pop(VM *vm, Value *out);
void freeVM(VM *vm);

InterpretResult interpret(VM *vm, Chunk *chunk);
InterpretResult run(VM *vm);

#endif
