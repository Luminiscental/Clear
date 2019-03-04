#ifndef clearvm_vm_h
#define clearvm_vm_h

#include "chunk.h"
#include "table.h"
#include "value.h"

#define STACK_MAX 256

typedef enum {

    INTERPRET_OK,
    INTERPRET_ERR

} InterpretResult;

typedef struct sScope {

    struct sScope *parent;
    size_t variables;

} Scope;

Scope *makeScope(Scope *parent);
void freeScope(Scope *scope);

typedef struct {

    Scope *currentScope;
    size_t localIndex;

} LocalState;

void initLocalState(LocalState *state);
void addLocal(LocalState *state, size_t index);
void pushScope(LocalState *state);
size_t popScope(LocalState *state);
void freeLocalState(LocalState *state);

typedef struct {

    Table globals;
    size_t globalIndex;

} GlobalState;

void initGlobalState(GlobalState *state);
void addGlobal(GlobalState *state, size_t index, Value value);
InterpretResult getGlobal(GlobalState *state, Value index, Value *out);
void freeGlobalState(GlobalState *state);

typedef struct sVM {

    Chunk *chunk;
    uint8_t *ip;
    Value stack[STACK_MAX];
    Value *stackTop;
    Table strings;
    Obj *objects;
    GlobalState globalState;
    LocalState localState;

} VM;

void initVM(VM *vm);
void resetStack(VM *vm);
InterpretResult push(VM *vm, Value value);
InterpretResult pop(VM *vm, Value *out);
void freeVM(VM *vm);

InterpretResult interpret(VM *vm, Chunk *chunk);
InterpretResult run(VM *vm);

#endif
