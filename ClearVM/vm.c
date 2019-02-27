
#include "vm.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "common.h"
#include "obj.h"

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

Value readString(VM *vm) {

    uint8_t size = readByte(vm);

    if (size == (uint8_t) -1) {

        char *buffer = (char*) malloc(1);
        buffer[0] = '\0';
        printf("|| Creating empty string\n");
    }

    char *buffer = (char*) malloc(size + 1);
    buffer[size] = '\0';

    for (size_t i = 0; i < size; i++) {

        buffer[i] = readByte(vm);
    }

    return makeString(size, buffer);
}

#ifdef DEBUG
#define PRINT(op) printf(#op "\n")
#else
#define PRINT(op)
#endif

#define STRICT_UNARY_OP(name, predicate, op)   \
                                               \
    InterpretResult strictUnary##name(VM *vm) {\
                                               \
        Value a = pop(vm);                     \
                                               \
        if (!(predicate)) {                    \
                                               \
            return INTERPRET_ERR;              \
        }                                      \
                                               \
        Value result = op;                     \
        push(vm, result);                      \
        return INTERPRET_OK;                   \
    }

#define BINARY_OP(name, op)               \
                                          \
    InterpretResult binary##name(VM *vm) {\
                                          \
        Value b = pop(vm);                \
        Value a = pop(vm);                \
                                          \
        Value result = op;                \
        push(vm, result);                 \
        return INTERPRET_OK;              \
    }

#define STRICT_BINARY_OP(name, predicate, op)   \
                                                \
    InterpretResult strictBinary##name(VM *vm) {\
                                                \
        Value b = pop(vm);                      \
        Value a = pop(vm);                      \
                                                \
        if (!(predicate)) {                     \
                                                \
            return INTERPRET_ERR;               \
        }                                       \
                                                \
        Value result = op;                      \
        push(vm, result);                       \
        return INTERPRET_OK;                    \
    }

#define PRED_NUMBER(x) ((x).type == VAL_NUMBER)
#define PRED_BOOL(x) ((x).type == VAL_BOOL)
#define PRED_STRING(x) (isObjType(x, OBJ_STRING))

#define PRED_BOTH(predicate) predicate(a) && predicate(b)

STRICT_BINARY_OP(AddNumbersOrStrings,
    PRED_BOTH(PRED_NUMBER) || PRED_BOTH(PRED_STRING),
    (a.type == VAL_NUMBER) ? makeNumber(a.as.number + b.as.number) : concatStrings((ObjString*) a.as.obj, (ObjString*) b.as.obj))

STRICT_BINARY_OP(SubtractNumbers,
    PRED_BOTH(PRED_NUMBER),
    makeNumber(a.as.number - b.as.number))

STRICT_BINARY_OP(MultiplyNumbers,
    PRED_BOTH(PRED_NUMBER),
    makeNumber(a.as.number * b.as.number))

STRICT_BINARY_OP(DivideNumbers,
    PRED_BOTH(PRED_NUMBER),
    makeNumber(a.as.number / b.as.number))

STRICT_UNARY_OP(NegateNumber,
    a.type == VAL_NUMBER,
    makeNumber(-a.as.number))

STRICT_UNARY_OP(NegateBoolean,
    a.type == VAL_BOOL,
    makeBoolean(!a.as.boolean))

STRICT_BINARY_OP(LessNumbers,
    PRED_BOTH(PRED_NUMBER),
    makeBoolean(a.as.number < b.as.number))

STRICT_BINARY_OP(NLessNumbers,
    PRED_BOTH(PRED_NUMBER),
    makeBoolean(a.as.number >= b.as.number))

STRICT_BINARY_OP(GreaterNumbers,
    PRED_BOTH(PRED_NUMBER),
    makeBoolean(a.as.number > b.as.number))

STRICT_BINARY_OP(NGreaterNumbers,
    PRED_BOTH(PRED_NUMBER),
    makeBoolean(a.as.number <= b.as.number))

STRICT_BINARY_OP(AddStrings,
    PRED_BOTH(PRED_STRING),
    concatStrings((ObjString*) a.as.obj, (ObjString*) b.as.obj))

BINARY_OP(EqualValues,
    makeBoolean(valuesEqual(a, b)))

BINARY_OP(NEqualValues,
    makeBoolean(!valuesEqual(a, b)))

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

                Value name = readString(vm);
                ObjString *nameStr = (ObjString*) name.as.obj;

                pop(vm);
                printf("|| Defined \"");
                printValue(name, false);
                printf("\n");

                // TODO: Add to table
                free(nameStr->chars);
                free(nameStr);

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

                        value = readDouble(vm);

                    } break;

                    case OP_STRING: {

                        value = readString(vm);

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

                if (strictBinaryAddNumbersOrStrings(vm) != INTERPRET_OK) {

                    printf("|| Expected numbers or strings to add!\n");
                    return INTERPRET_ERR;
                }

            } break;

            case OP_SUBTRACT: {

                PRINT(OP_SUBTRACT);

                if (strictBinarySubtractNumbers(vm) != INTERPRET_OK) {

                    printf("Expected numbers to subtract!\n");
                    return INTERPRET_ERR;
                }

            } break;

            case OP_MULTIPLY: {

                PRINT(OP_MULTIPLY);

                if (strictBinaryMultiplyNumbers(vm) != INTERPRET_OK) {

                    printf("Expected numbers to multiply!\n");
                    return INTERPRET_ERR;
                }

            } break;

            case OP_DIVIDE: {

                PRINT(OP_DIVIDE);

                if (strictBinaryDivideNumbers(vm) != INTERPRET_OK) {

                    printf("|| Expected numbers to divide!\n");
                    return INTERPRET_ERR;
                }

            } break;

            case OP_NEGATE: {

                PRINT(OP_NEGATE);

                if (strictUnaryNegateNumber(vm) != INTERPRET_OK) {

                    printf("|| Expected number to negate!\n");
                    return INTERPRET_ERR;
                }

            } break;

            case OP_EQUAL: {

                PRINT(OP_EQUAL);

                binaryEqualValues(vm);
            
            } break;

            case OP_NEQUAL: {
            
                PRINT(OP_NEQUAL);

                binaryNEqualValues(vm);
            
            } break;

            case OP_LESS: {
            
                PRINT(OP_LESS);

                if (strictBinaryLessNumbers(vm) != INTERPRET_OK) {

                    printf("Expected numbers to compare!\n");
                    return INTERPRET_ERR;
                }
            
            } break;

            case OP_NLESS: {
            
                PRINT(OP_NLESS);

                if (strictBinaryNLessNumbers(vm) != INTERPRET_OK) {

                    printf("Expected numbers to compare!\n");
                    return INTERPRET_ERR;
                }

            } break;

            case OP_GREATER: {
            
                PRINT(OP_GREATER);

                if (strictBinaryGreaterNumbers(vm) != INTERPRET_OK) {

                    printf("Expected numbers to compare!\n");
                    return INTERPRET_ERR;
                }
            
            } break;

            case OP_NGREATER: {
            
                PRINT(OP_NGREATER);

                if (strictBinaryNGreaterNumbers(vm) != INTERPRET_OK) {

                    printf("Expected numbers to compare!\n");
                    return INTERPRET_ERR;
                }
            
            } break;

            case OP_NOT: {

                PRINT(OP_NOT);

                if (strictUnaryNegateBoolean(vm) != INTERPRET_OK) {

                    printf("Expected boolean to negate!\n");
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

#undef STRICT_BINARY_OP
#undef BINARY_OP
#undef UNARY_OP
#undef PRINT

