#ifndef clearvm_vm_h
#define clearvm_vm_h

#include "chunk.h"
#include "table.h"
#include "value.h"

#define FRAMES_MAX 64
// TODO: Multiple-byte indices
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

    bool isSet[STACK_MAX];
    Value values[STACK_MAX];
    size_t globalIndex;

} GlobalState;

void initGlobalState(GlobalState *state);
void addGlobal(GlobalState *state, size_t index, Value value);
InterpretResult getGlobal(GlobalState *state, size_t index, Value *out);

typedef struct sCallFrame {

    // TODO: Params

    uint8_t *ip;
    Value stack[STACK_MAX];
    Value *stackTop;
    LocalState localState;

    VM *vm;

} CallFrame;

typedef struct sVM {

    Chunk *chunk;
    Table strings;
    Obj *objects;
    GlobalState globalState;
    LocalState localState;

    CallFrame frames[FRAMES_MAX];
    size_t frameDepth;

} VM;

void initVM(VM *vm);
void resetStack(CallFrame *frame);
InterpretResult push(VM *vm, Value value);
InterpretResult pop(VM *vm, Value *out);
InterpretResult peek(VM *vm, Value *out);
void freeVM(VM *vm);

InterpretResult interpret(VM *vm, Chunk *chunk);
InterpretResult run(VM *vm);

#endif
