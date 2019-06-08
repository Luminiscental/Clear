#ifndef clearvm_vm_h
#define clearvm_vm_h

#include "common.h"
#include "value.h"

#define STACK_MAX 256

#define DEFN_STACK(T)                                                          \
                                                                               \
    typedef struct {                                                           \
                                                                               \
        T values[STACK_MAX];                                                   \
        T *next;                                                               \
                                                                               \
    } T##Stack;                                                                \
                                                                               \
    Result push##T##Stack(T##Stack *stack, T value);                           \
    Result pop##T##Stack(T##Stack *stack, T *popped);

DEFN_STACK(Value)

typedef struct {

    ValueStack stack;

} Frame;

DEFN_STACK(Frame)

typedef struct {

    FrameStack frames;

} VM;

void initVM(VM *vm);
Result executeCode(VM *vm, uint8_t *code, size_t length);
void freeVM(VM *vm);

#endif
