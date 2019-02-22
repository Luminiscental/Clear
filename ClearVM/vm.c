
#include "vm.h"

#include <stdio.h>

#include "common.h"

VM initVM() {

    VM result;
    return result;
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

Value readConstant(VM *vm) {

    return vm->chunk->constants.values[readByte(vm)];
}

InterpretResult run(VM *vm) {

    while (true) {

        uint8_t instruction = readByte(vm);

        switch (instruction) {

            case OP_PRINT: {

                printf("Pop: print\n");
                return INTERPRET_OK;

            } break;

            case OP_LOAD_CONST: {

                Value constant = readConstant(vm);
                printf("Push: %f\n", constant);

            } break;
                
            case OP_STORE_CONST: {

                uint8_t type = readByte(vm);
                Value value;

                switch(type) {

                    case OP_NUMBER: {

                        value = readDouble(vm);

                    } break;

                    default: {

                        printf("Invalid constant type!\n");
                        return INTERPRET_ERR;

                    } break;
                }

                int index = addConstant(vm->chunk, value);
                printf("Store constant %d (%f)\n", index, value);

            } break;

            default: {

                printf("Invalid op code!\n");
                return INTERPRET_ERR;

            } break;
        }
    }

#undef READ_CONSTANT
#undef READ_BYTE
}

void freeVM(VM *vm) {

}
