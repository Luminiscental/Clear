
#include "vm.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "common.h"

void initVM(VM *vm) {

    resetStack(vm);
}

void resetStack(VM *vm) {

    vm->stackTop = vm->stack;
}

void push(VM *vm, Value value) {

    if (vm->stackTop >= vm->stack + STACK_MAX - 1) {

        // TODO: Error handling
        printf("|| Stack overflow!\n");

    } else {

        *vm->stackTop = value;
        vm->stackTop++;
    }
}

Value pop(VM *vm) {

    if (vm->stackTop <= vm->stack) {

        // TODO: Error handling
        printf("|| Stack underflow!\n");
        return makeNumber(0.0);

    } else {

        vm->stackTop--;
        return *vm->stackTop;
    }
}

void freeVM(VM *vm) {

}

InterpretResult interpret(VM *vm, Chunk *chunk) {

    vm->chunk = chunk;
    vm->ip = vm->chunk->code;

    return run(vm);
}

uint8_t readByte(VM *vm) {

    if (1 + vm->ip - vm->chunk->code > vm->chunk->count) {

        // TODO: Error handling
        printf("|| Ran out of bytes!\n");
        return (uint8_t) -1;

    } else {

        return *vm->ip++;
    }
}

bool readBoolean(VM *vm) {

    return (bool) readByte(vm);
}

double readDouble(VM *vm) {

    if (8 + vm->ip - vm->chunk->code > vm->chunk->count) {

        // TODO: Error handling
        printf("|| Ran out of bytes!\n");
        return 0.0;

    } else {

        double *read = (double*) vm->ip;

        vm->ip += 8;

        return *read;
    }
}

char *readString(VM *vm) {

    uint8_t size = readByte(vm);

    if (size == (uint8_t) -1) {

        char *buffer = (char*) malloc(1);
        buffer[0] = '\0';
        printf("|| Creating empty string\n");
        return buffer;
    }

    char *buffer = (char*) malloc(size + 1);
    buffer[size] = '\0';

    for (size_t i = 0; i < size; i++) {

        buffer[i] = readByte(vm);
    }

    return buffer;
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

#ifdef DEBUG
#define PRINT(op) printf(#op "\n")
#else
#define PRINT(op)
#endif

#define UNARY_OP(expected, op)                                      \
    do {                                                            \
                                                                    \
        Value a = pop(vm);                                          \
                                                                    \
        if (a.type != expected) {                                   \
                                                                    \
            printf("|| Expected "#expected" for unary operator!\n");\
            return INTERPRET_ERR;                                   \
        }                                                           \
                                                                    \
        Value result = op;                                          \
        push(vm, result);                                           \
                                                                    \
    } while(false)

#define BINARY_OP(expected, op)                                      \
    do {                                                             \
                                                                     \
        Value b = pop(vm);                                           \
        Value a = pop(vm);                                           \
                                                                     \
        if (a.type != expected || b.type != expected) {              \
                                                                     \
            printf("|| Expected "#expected" for binary operator!\n");\
            return INTERPRET_ERR;                                    \
        }                                                            \
                                                                     \
        Value result = op;                                           \
        push(vm, result);                                            \
                                                                     \
    } while(false)

            case OP_TRUE: {

                PRINT(OP_TRUE);

                Value val = makeBoolean(true);

                push(vm, val);

            } break;

            case OP_FALSE: {

                PRINT(OP_FALSE);

                Value val = makeBoolean(false);

                push(vm, val);

            } break;

            case OP_DEFINE: {

                PRINT(OP_DEFINE);

                Value name = makeString(readString(vm));

                pop(vm);
                printf("|| Defined \"%s\"\n", name.as.string);
                // TODO: Add to table
                free(name.as.string);

            } break;

            case OP_POP: {

                PRINT(OP_POP);

                pop(vm);

            } break;

            case OP_RETURN: {

                PRINT(OP_RETURN);

                return INTERPRET_OK;

            } break;

            case OP_PRINT: {

                PRINT(OP_PRINT);

                Value value = pop(vm);

                printf("|| print ");
                printValue(value, true);

            } break;

            case OP_LOAD_CONST: {

                uint8_t index = readByte(vm);

                if (index >= vm->chunk->constants.count) {

                    printf("|| Constant out of index!\n");
                    return INTERPRET_ERR;
                }

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

                        value = makeNumber(readDouble(vm));

                    } break;

                    case OP_STRING: {

                        value = makeString(readString(vm));

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

            case OP_ADD: {

                PRINT(OP_ADD);

                Value b = pop(vm);
                Value a = pop(vm);

                if (b.type == VAL_NUMBER && a.type == VAL_NUMBER) {

                    Value result = makeNumber(a.as.number + b.as.number);
                    push(vm, result);

                } else if (b.type == VAL_STRING && a.type == VAL_STRING) {

                    Value result = concatStrings(a.as.string, b.as.string);
                    push(vm, result);

                } else {

                    printf("|| Expected two numbers or two strings as operands for '+'!\n");
                    return INTERPRET_ERR;
                }

            } break;

            case OP_SUBTRACT: {

                PRINT(OP_SUBTRACT);
                BINARY_OP(VAL_NUMBER, makeNumber(a.as.number - b.as.number));

            } break;

            case OP_MULTIPLY: {

                PRINT(OP_MULTIPLY);
                BINARY_OP(VAL_NUMBER, makeNumber(a.as.number * b.as.number));

            } break;

            case OP_DIVIDE: {

                PRINT(OP_DIVIDE);
                BINARY_OP(VAL_NUMBER, makeNumber(a.as.number / b.as.number));

            } break;

            case OP_NEGATE: {

                PRINT(OP_NEGATE);

                UNARY_OP(VAL_NUMBER, makeNumber(-a.as.number));

            } break;

            case OP_EQUAL: {

                PRINT(OP_EQUAL);

                BINARY_OP(VAL_BOOL, makeBoolean(valuesEqual(a, b)));
            
            } break;

            case OP_NEQUAL: {
            
                PRINT(OP_NEQUAL);

                BINARY_OP(VAL_BOOL, makeBoolean(!valuesEqual(a, b)));
            
            } break;

            case OP_LESS: {
            
                PRINT(OP_LESS);

                BINARY_OP(VAL_NUMBER, makeBoolean(a.as.number < b.as.number));
            
            } break;

            case OP_NLESS: {
            
                PRINT(OP_NLESS);

                BINARY_OP(VAL_NUMBER, makeBoolean(a.as.number >= b.as.number));
            
            } break;

            case OP_GREATER: {
            
                PRINT(OP_GREATER);

                BINARY_OP(VAL_NUMBER, makeBoolean(a.as.number > b.as.number));
            
            } break;

            case OP_NGREATER: {
            
                PRINT(OP_NGREATER);

                BINARY_OP(VAL_NUMBER, makeBoolean(a.as.number <= b.as.number));
            
            } break;

            case OP_NOT: {

                PRINT(OP_NOT);

                UNARY_OP(VAL_BOOL, makeBoolean(!a.as.boolean));

            } break;

            default: {

                printf("|| Invalid op code!\n");
                return INTERPRET_ERR;

            } break;

#undef BINARY_OP
#undef UNARY_OP
#undef PRINT

        }
    }
}

