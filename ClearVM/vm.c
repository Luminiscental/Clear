
#include "vm.h"

#define IMPL_STACK(T)                                                          \
                                                                               \
    Result push##T##Stack(T##Stack *stack, T value) {                          \
                                                                               \
        if (stack->next - stack->values == STACK_MAX) {                        \
                                                                               \
            return RESULT_ERR;                                                 \
        }                                                                      \
                                                                               \
        *stack->next = value;                                                  \
        stack->next++;                                                         \
                                                                               \
        return RESULT_OK;                                                      \
    }                                                                          \
                                                                               \
    Result pop##T##Stack(T##Stack *stack, T *popped) {                         \
                                                                               \
        if (stack->next == stack->values) {                                    \
                                                                               \
            return RESULT_ERR;                                                 \
        }                                                                      \
                                                                               \
        stack->next--;                                                         \
                                                                               \
        if (popped != NULL) {                                                  \
                                                                               \
            *popped = *stack->next;                                            \
        }                                                                      \
                                                                               \
        return RESULT_OK;                                                      \
    }

IMPL_STACK(Value)
IMPL_STACK(Frame)

void initVM(VM *vm) {}

Result executeCode(VM *vm, uint8_t *code, size_t length) { return RESULT_OK; }

void freeVM(VM *vm) {}
