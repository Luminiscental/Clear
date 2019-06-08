#ifndef clearvm_vm_h
#define clearvm_vm_h

#include "common.h"
#include "value.h"

#define DEFN_STACK(T, N)                                                       \
                                                                               \
    typedef struct {                                                           \
                                                                               \
        T values[N];                                                           \
        T *next;                                                               \
                                                                               \
    } T##Stack##N;                                                             \
                                                                               \
    Result push##T##Stack##N(T##Stack##N *stack, T value);                     \
    Result pop##T##Stack##N(T##Stack##N *stack, T *popped);

DEFN_STACK(Value, 256)
DEFN_STACK(Value, 64)

typedef struct {

    ValueStack256 stack;
    ValueStack64 locals;
    size_t paramCount;

} Frame;

DEFN_STACK(Frame, 64)

#undef DEFN_STACK

typedef struct {

    FrameStack64 frames;
    ValueList globals;

} VM;

void initVM(VM *vm);
Result executeCode(VM *vm, uint8_t *code, size_t length);
void freeVM(VM *vm);

#endif
