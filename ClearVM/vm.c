
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

InterpretResult push(VM *vm, Value value) {

    if (vm->stackTop >= vm->stack + STACK_MAX - 1) {

        printf("|| Stack overflow!\n");
        return INTERPRET_ERR;

    } else {

        *vm->stackTop = value;
        vm->stackTop++;
        return INTERPRET_OK;
    }
}

InterpretResult pop(VM *vm, Value *out) {

    if (vm->stackTop <= vm->stack) {

        printf("|| Stack underflow!\n");
        return INTERPRET_ERR;

    } else {

        vm->stackTop--;
        *out = *vm->stackTop;
        return INTERPRET_OK;
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

static InterpretResult readByte(VM *vm, uint8_t *out) {

    if (1 + vm->ip - vm->chunk->code > vm->chunk->count) {

        printf("|| Ran out of bytes!\n");
        return INTERPRET_ERR;

    } else {

        *out = *vm->ip++;
        return INTERPRET_OK;
    }
}

static InterpretResult readBoolean(VM *vm, Value *out) {

    uint8_t val;

    if (readByte(vm, &val) != INTERPRET_OK) {

        printf("|| Could not read boolean!\n");
        return INTERPRET_ERR;
    }

    *out = makeBoolean((bool) val);
    return INTERPRET_OK;
}

static InterpretResult readDouble(VM *vm, Value *out) {

    if (8 + vm->ip - vm->chunk->code > vm->chunk->count) {

        printf("|| Ran out of bytes!\n");
        return INTERPRET_ERR;

    } else {

        double *read = (double*) vm->ip;

        vm->ip += 8;

        *out = makeNumber(*read);
        return INTERPRET_OK;
    }
}

static InterpretResult readStringRaw(VM *vm, Value *out) {

    uint8_t size;
    if(readByte(vm, &size) != INTERPRET_OK) {

        printf("|| Could not read size of string!\n");
        return INTERPRET_ERR;
    }

    char *buffer = ALLOCATE(char, size + 1);
    buffer[size] = '\0';

    for (size_t i = 0; i < size; i++) {

        uint8_t byte;
        if (readByte(vm, &byte) != INTERPRET_OK) {

            printf("|| Ran out of bytes reading string!\n");
            return INTERPRET_ERR;
        }

        buffer[i] = byte;
    }

    *out = makeString(vm, size, buffer);
    return INTERPRET_OK;
}

#define ANY_OP(op) \
    if (push(vm, op) != INTERPRET_OK) { \
        printf("|| Could not push result of unary operation!\n"); \
        return INTERPRET_ERR; \
    }

#define UNARY_OP \
    Value a; \
    if (pop(vm, &a) != INTERPRET_OK) { \
        printf("|| Expected value for unary operation!\n"); \
        return INTERPRET_ERR; \
    }

#define TYPED_UNARY(expected, op) \
    if (a.type == expected) { \
        ANY_OP(op) \
    }

#define BINARY_OP \
    Value a; \
    Value b; \
    if (pop(vm, &b) != INTERPRET_OK \
     || pop(vm, &a) != INTERPRET_OK) { \
        printf("|| Expected two values for binary operation!\n"); \
        return INTERPRET_ERR; \
    }

#define TYPED_BINARY(expected, op) \
    if (a.type == expected && b.type == expected) { \
        ANY_OP(op) \
    }

#define OBJ_TYPED_BINARY(expected, op) \
    if (isObjType(a, expected) && isObjType(b, expected)) { \
        ANY_OP(op) \
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

        uint8_t instruction;
        if (readByte(vm, &instruction) != INTERPRET_OK) {

            printf("|| Ran out of instructions!\n");
            return INTERPRET_ERR;
        }

        switch (instruction) {

            case OP_TYPE: {

                UNARY_OP

                    ANY_OP(typeString(vm, a))
                
            } break;

            case OP_TRUE: {

                Value val = makeBoolean(true);

                if (push(vm, val) != INTERPRET_OK) {

                    printf("|| Could not push boolean literal!\n");
                    return INTERPRET_ERR;
                }

            } break;

            case OP_FALSE: {

                Value val = makeBoolean(false);

                if (push(vm, val) != INTERPRET_OK) {

                    printf("|| Could not push boolean literal!\n");
                    return INTERPRET_ERR;
                }

            } break;

            case OP_DEFINE_GLOBAL: {

                uint8_t index;
                if (readByte(vm, &index) != INTERPRET_OK) {

                    printf("|| Expected index to define global!\n");
                    return INTERPRET_ERR;
                }

                Value val;
                if (pop(vm, &val) != INTERPRET_OK) {

                    printf("|| Expected value to define global!\n");
                    return INTERPRET_ERR;
                }

                tableSet(&vm->globals, makeInteger(index), val);

            } break;

            case OP_LOAD_GLOBAL: {
 
                uint8_t index;
                if (readByte(vm, &index) != INTERPRET_OK) {

                    printf("|| Expected index to load global!\n");
                    return INTERPRET_ERR;
                }

                Value value;
                if (!tableGet(&vm->globals, makeInteger(index), &value)) {

                    printf("|| Undefined identifier!\n");
                    return INTERPRET_ERR;
                }

                if (push(vm, value) != INTERPRET_OK) {

                    printf("|| Could not push global value!\n");
                    return INTERPRET_ERR;
                }
            
            } break;

            case OP_POP: {

                Value _;
                pop(vm, &_);

            } break;

            case OP_RETURN: {

                return INTERPRET_OK;

            } break;

            case OP_PRINT_BLANK: {

                printf("\n");

            } break;

            case OP_PRINT: {

                Value value;

                if (pop(vm, &value) != INTERPRET_OK) {
                    
                    printf("|| Expected value to print!\n");
                    return INTERPRET_ERR;
                }

                printValue(value, true);

            } break;

            case OP_LOAD_CONST: {

                uint8_t index;
                if (readByte(vm, &index) != INTERPRET_OK) {

                    printf("|| Expected index of constant to load!\n");
                    return INTERPRET_ERR;
                }

                if (index >= vm->chunk->constants.count) {

                    printf("|| Constant out of index!\n");
                    return INTERPRET_ERR;
                }

                Value constant = vm->chunk->constants.values[index];

                if (push(vm, constant) != INTERPRET_OK) {

                    printf("|| Could not push constant value!\n");
                    return INTERPRET_ERR;
                }

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

                    ANY_OP(makeBoolean(valuesEqual(a, b)))
            
            } break;

            case OP_NEQUAL: {
            
                BINARY_OP

                    ANY_OP(makeBoolean(!valuesEqual(a, b)))
            
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

                printf("|| Invalid op code %d!\n", instruction);
                return INTERPRET_ERR;

            } break;
        }
    }
}

#undef OBJ_TYPED_BINARY
#undef TYPED_BINARY
#undef BINARY_OP
#undef TYPED_UNARY
#undef UNARY_OP
#undef ANY_OP

