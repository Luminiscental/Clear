#ifndef clearvm_vm_h
#define clearvm_vm_h

#include "bytecode.h"
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
    void init##T##Stack##N(T##Stack##N *stack);                                \
    Result push##T##Stack##N(T##Stack##N *stack, T value);                     \
    Result pop##T##Stack##N(T##Stack##N *stack, T *popped);                    \
    Result peek##T##Stack##N(T##Stack##N *stack, T **peeked, size_t offset);

DEFN_STACK(Value, 256)
DEFN_STACK(Value, 64)

typedef struct {

    ValueStack256 stack;
    ValueStack64 locals;
    size_t paramCount;

} Frame;

void initFrame(Frame *frame);

DEFN_STACK(Frame, 64)

#undef DEFN_STACK

typedef struct sVM VM;

typedef Result (*Instruction)(VM *vm, uint8_t **ip, uint8_t *code,
                              size_t codeLength);

typedef struct sVM {

    FrameStack64 frames;

    ObjectValue *objects;

    ValueList globals;

    Value *constants;
    size_t constantCount;

    Instruction instructions[OP_COUNT];

} VM;

Result initVM(VM *vm);
Result executeCode(VM *vm, uint8_t *code, size_t length);
void freeVM(VM *vm);

#endif
