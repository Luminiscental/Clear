
#include "vm.h"

#include <stdio.h>

#include "common.h"

void initVM(VM *vm) {

    resetStack(vm);
}

void resetStack(VM *vm) {

    vm->stackTop = vm->stack;
}

void push(VM *vm, Value value) {

    *vm->stackTop = value;
    vm->stackTop++;
}

Value pop(VM *vm) {

    vm->stackTop--;
    return *vm->stackTop;
}

void freeVM(VM *vm) {

}

InterpretResult interpret(VM *vm, Chunk *chunk) {

    vm->chunk = chunk;
    vm->ip = vm->chunk->code;

    return run(vm);
}

uint8_t readByte(VM *vm) {

    return *vm->ip++;
}

double readDouble(VM *vm) {

    double *read = (double*) vm->ip;

    vm->ip += 8;

    return *read;
}

InterpretResult run(VM *vm) {

    while (true) {

        uint8_t instruction = readByte(vm);

#ifdef DEBUG

        printf("          ");

        for (Value *slot = vm->stack; slot < vm->stackTop; slot++) {

            printf("[ ");
            printValue(*slot, false);
            printf(" ]");
        }
        printf("\n");

#endif

        switch (instruction) {

            case OP_PRINT: {

                Value value = pop(vm);

#ifdef DEBUG

                printf("OP_PRINT\n");

#endif

                printf("|| print %f\n", value);
                return INTERPRET_OK;

            } break;

            case OP_LOAD_CONST: {

                uint8_t index = readByte(vm);
                Value constant = vm->chunk->constants.values[index];

#ifdef DEBUG

                printf("%-16s %4d '", "OP_LOAD_CONST", index);
                printValue(constant, false);
                printf("'\n");

#endif

                push(vm, constant);

            } break;
                
            case OP_STORE_CONST: {

                uint8_t type = readByte(vm);
                Value value;

                switch(type) {

                    case OP_NUMBER: {

                        value = readDouble(vm);

                    } break;

                    default: {

                        printf("|| Invalid constant type!\n");
                        return INTERPRET_ERR;

                    } break;
                }

#ifdef DEBUG

                printf("%-19s ", "OP_STORE_CONST");
                printValue(value, true);

#endif

                int index = addConstant(vm->chunk, value);

            } break;

            case OP_NEGATE: {

#ifdef DEBUG

                printf("OP_NEGATE\n");

#endif

                push(vm, -pop(vm));

            } break;

            case OP_ADD: {

#ifdef DEBUG

                printf("OP_ADD\n");

#endif

                double b = pop(vm);
                double a = pop(vm);

                push(vm, a + b);

            } break;

            case OP_SUBTRACT: {

#ifdef DEBUG

                printf("OP_SUBTRACT\n");

#endif

                double b = pop(vm);
                double a = pop(vm);

                push(vm, a - b);

            } break;

            case OP_MULTIPLY: {

#ifdef DEBUG

                printf("OP_MULTIPLY\n");

#endif

                double b = pop(vm);
                double a = pop(vm);

                push(vm, a * b);

            } break;

            case OP_DIVIDE: {

#ifdef DEBUG

                printf("OP_DIVIDE\n");

#endif

                double b = pop(vm);
                double a = pop(vm);

                push(vm, a / b);

            } break;

#undef BINARY_OP

            default: {

                printf("|| Invalid op code!\n");
                return INTERPRET_ERR;

            } break;
        }
    }
}

