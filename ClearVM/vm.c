
#include "vm.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "common.h"
#include "obj.h"
#include "memory.h"

void initVM(VM *vm) {

    resetStack(vm);
    vm->objects = NULL;
    initTable(&vm->strings);
    initTable(&vm->globals);
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

    freeTable(&vm->strings);
    freeTable(&vm->globals);
    freeObjects(vm);
}

InterpretResult interpret(VM *vm, Chunk *chunk) {

    vm->chunk = chunk;
    vm->ip = vm->chunk->code + vm->chunk->start;

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

Value readBoolean(VM *vm) {

    return makeBoolean((bool) readByte(vm));
}

Value readDouble(VM *vm) {

    if (8 + vm->ip - vm->chunk->code > vm->chunk->count) {

        // TODO: Error handling
        printf("|| Ran out of bytes!\n");
        return makeNumber(0.0);

    } else {

        double *read = (double*) vm->ip;

        vm->ip += 8;

        return makeNumber(*read);
    }
}

Value readStringRaw(VM *vm) {

    uint8_t size = readByte(vm);

    if (size == (uint8_t) -1) {

        char *buffer = ALLOCATE(char, 1);
        buffer[0] = '\0';
        printf("|| Creating empty string\n");
    }

    char *buffer = ALLOCATE(char, size + 1);
    buffer[size] = '\0';

    for (size_t i = 0; i < size; i++) {

        buffer[i] = readByte(vm);
    }

    return makeString(vm, size, buffer);
}

#define UNARY_OP \
    Value a = pop(vm);

#define ANY_UNARY(op) \
    push(vm, op);

#define TYPED_UNARY(expected, op) \
    if (a.type == expected) { \
        ANY_UNARY(op) \
    }

#define BINARY_OP \
    Value b = pop(vm); \
    Value a = pop(vm);

#define ANY_BINARY(op) \
    push(vm, op);

#define TYPED_BINARY(expected, op) \
    if (a.type == expected && b.type == expected) { \
        ANY_BINARY(op) \
    }

#define OBJ_TYPED_BINARY(expected, op) \
    if (isObjType(a, expected) && isObjType(b, expected)) { \
        ANY_BINARY(op) \
    }

static void printStack(VM *vm) {

    printf("          ");

    for (Value *slot = vm->stack; slot < vm->stackTop; slot++) {

        printf("[ ");
        printValue(*slot, false);
        printf(" ]");
    }

    printf("\n");
}

InterpretResult run(VM *vm) {

    while (true) {

#ifdef DEBUG_STACK

        printStack(vm);

#endif

#ifdef DEBUG_TRACE

        disassembleInstruction(vm->chunk, vm->ip - vm->chunk->code);

#endif

        uint8_t instruction = readByte(vm);

        switch (instruction) {

            case OP_TYPE: {

                UNARY_OP

                    ANY_UNARY(typeString(vm, a))
                
            } break;

            case OP_TRUE: {

                Value val = makeBoolean(true);

                push(vm, val);

            } break;

            case OP_FALSE: {

                Value val = makeBoolean(false);

                push(vm, val);

            } break;

            case OP_DEFINE_GLOBAL: {

                uint8_t index = readByte(vm);

                tableSet(&vm->globals, makeInteger(index), pop(vm));

            } break;

            case OP_LOAD_GLOBAL: {
            
                uint8_t index = readByte(vm);

                Value value;
                if (!tableGet(&vm->globals, makeInteger(index), &value)) {

                    printf("|| Undefined identifier!\n");
                    return INTERPRET_ERR;
                }

                push(vm, value);
            
            } break;

            case OP_POP: {

                pop(vm);

            } break;

            case OP_RETURN: {

                return INTERPRET_OK;

            } break;

            case OP_PRINT_BLANK: {

                printf("\n");

            } break;

            case OP_PRINT: {

                Value value = pop(vm);

                printValue(value, true);

            } break;

            case OP_LOAD_CONST: {

                uint8_t index = readByte(vm);

                if (index >= vm->chunk->constants.count) {

                    printf("|| Constant out of index!\n");
                    return INTERPRET_ERR;
                }

                Value constant = vm->chunk->constants.values[index];

                push(vm, constant);

            } break;
                
            case OP_ADD: {

                BINARY_OP

                    TYPED_BINARY(VAL_NUMBER, makeNumber(a.as.number + b.as.number))

                else

                    OBJ_TYPED_BINARY(OBJ_STRING, concatStrings(vm, (ObjString*) a.as.obj, (ObjString*) b.as.obj))

                else {

                    printf("|| Expected numbers or strings to add!\n");
                    return INTERPRET_ERR;
                }

            } break;

            case OP_SUBTRACT: {

                BINARY_OP

                    TYPED_BINARY(VAL_NUMBER, makeNumber(a.as.number - b.as.number))

                else {

                    printf("|| Expected numbers to subtract!\n");
                    return INTERPRET_ERR;
                }

            } break;

            case OP_MULTIPLY: {

                BINARY_OP

                    TYPED_BINARY(VAL_NUMBER, makeNumber(a.as.number * b.as.number))

                else {

                    printf("|| Expected numbers to multiply!\n");
                    return INTERPRET_ERR;
                }

            } break;

            case OP_DIVIDE: {

                BINARY_OP

                    TYPED_BINARY(VAL_NUMBER, makeNumber(a.as.number / b.as.number))

                else {

                    printf("|| Expected numbers to divide!\n");
                    return INTERPRET_ERR;
                }

            } break;

            case OP_NEGATE: {

                UNARY_OP

                    TYPED_UNARY(VAL_NUMBER, makeNumber(-a.as.number))

                else {

                    printf("|| Expected number to negate!\n");
                    return INTERPRET_ERR;
                }

            } break;

            case OP_EQUAL: {

                BINARY_OP

                    ANY_BINARY(makeBoolean(valuesEqual(a, b)))
            
            } break;

            case OP_NEQUAL: {
            
                BINARY_OP

                    ANY_BINARY(makeBoolean(!valuesEqual(a, b)))
            
            } break;

            case OP_LESS: {
            
                BINARY_OP

                    TYPED_BINARY(VAL_NUMBER, makeBoolean(a.as.number < b.as.number))

                else {

                    printf("|| Expected numbers to compare!\n");
                    return INTERPRET_ERR;
                }
            
            } break;

            case OP_NLESS: {
            
                BINARY_OP

                    TYPED_BINARY(VAL_NUMBER, makeBoolean(a.as.number >= b.as.number))

                else {

                    printf("|| Expected numbers to compare!\n");
                    return INTERPRET_ERR;
                }

            } break;

            case OP_GREATER: {
            
                BINARY_OP

                    TYPED_BINARY(VAL_NUMBER, makeBoolean(a.as.number > b.as.number))

                else {

                    printf("|| Expected numbers to compare!\n");
                    return INTERPRET_ERR;
                }
            
            } break;

            case OP_NGREATER: {
            
                BINARY_OP

                    TYPED_BINARY(VAL_NUMBER, makeBoolean(a.as.number <= b.as.number))

                else {

                    printf("|| Expected numbers to compare!\n");
                    return INTERPRET_ERR;
                }
            
            } break;

            case OP_NOT: {

                UNARY_OP

                    TYPED_UNARY(VAL_BOOL, makeBoolean(!a.as.boolean))

                else {

                    printf("|| Expected boolean to negate!\n");
                    return INTERPRET_ERR;
                }

            } break;

            default: {

                printf("|| Invalid op code!\n");
                return INTERPRET_ERR;

            } break;
        }
    }
}

#undef OBJ_TYPED_BINARY
#undef TYPED_BINARY
#undef ANY_BINARY
#undef BINARY_OP
#undef TYPED_UNARY
#undef ANY_UNARY
#undef UNARY_OP

