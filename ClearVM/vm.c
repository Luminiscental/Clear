
#include "vm.h"

#include <stdio.h>

#define IMPL_STACK(T, N)                                                       \
                                                                               \
    Result push##T##Stack##N(T##Stack##N *stack, T value) {                    \
                                                                               \
        if (stack->next - stack->values == N) {                                \
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
    Result pop##T##Stack##N(T##Stack##N *stack, T *popped) {                   \
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

IMPL_STACK(Value, 256)
IMPL_STACK(Value, 64)
IMPL_STACK(Frame, 64)

#undef IMPL_STACK

Result errorInstruction(VM *vm, uint8_t **ip, size_t codeLength) {

    printf("|| Unimplemented opcode\n");
    return RESULT_ERR;
}

void initVM(VM *vm) {

    initValueList(&vm->globals);

    for (size_t i = 0; i < OP_COUNT; i++) {

        vm->instructions[i] = errorInstruction;
    }
}

Result executeCode(VM *vm, uint8_t *code, size_t length) {

    for (uint8_t *ip = code; (size_t)(ip - code) < length; ip++) {

        uint8_t opcode = *ip;

        if (opcode >= OP_COUNT) {

            printf("|| Unknown opcode %d\n", opcode);
            return RESULT_ERR;
        }

        if (vm->instructions[opcode](vm, &ip, length) != RESULT_OK) {

            printf("|| Opcode %d failed\n", opcode);
            return RESULT_ERR;
        }
    }

    return RESULT_OK;
}

void freeVM(VM *vm) { freeValueList(&vm->globals); }
