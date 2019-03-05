
#include "vm.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "common.h"
#include "memory.h"
#include "obj.h"
#include "value.h"

Scope *makeScope(Scope *parent) {

    Scope *result = (Scope *)malloc(sizeof(Scope));

    result->parent = parent;
    result->variables = 0;

    return result;
}

void freeScope(Scope *scope) {

    while (scope != NULL) {

        Scope *parent = scope->parent;
        free(scope);
        scope = parent;
    }
}

void initLocalState(LocalState *state) {

    state->currentScope = makeScope(NULL);
    state->localIndex = 0;
}

void addLocal(LocalState *state, size_t index) {

    if (index == state->localIndex) {

        state->currentScope->variables++;
        state->localIndex++;
    }
}

void pushScope(LocalState *state) {

    state->currentScope = makeScope(state->currentScope);
}

size_t popScope(LocalState *state) {

    Scope *popped = state->currentScope;
    state->currentScope = popped->parent;
    state->localIndex -= popped->variables;
    return popped->variables;
}

void freeLocalState(LocalState *state) { freeScope(state->currentScope); }

void initGlobalState(GlobalState *state) {
    state->globalIndex = 0;

    for (size_t i = 0; i < STACK_MAX; i++) {

        state->isSet[i] = false;
    }
}

void addGlobal(GlobalState *state, size_t index, Value value) {

    state->isSet[index] = true;
    state->values[index] = value;

    if (index == state->globalIndex) {

        state->globalIndex++;
    }
}

InterpretResult getGlobal(GlobalState *state, size_t index, Value *out) {

    if (state->isSet[index]) {

        if (out != NULL) {

            *out = state->values[index];
        }

        return INTERPRET_OK;
    }

    return INTERPRET_ERR;
}

void initVM(VM *vm) {

    resetStack(vm);

    vm->objects = NULL;
    initTable(&vm->strings);

    initGlobalState(&vm->globalState);
    initLocalState(&vm->localState);
}

void resetStack(VM *vm) { vm->stackTop = vm->stack; }

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
        if (out != NULL)
            *out = *vm->stackTop;
        return INTERPRET_OK;
    }
}

void freeVM(VM *vm) {

    freeTable(&vm->strings);
    freeLocalState(&vm->localState);
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

    *out = makeBoolean((bool)val);
    return INTERPRET_OK;
}

static InterpretResult readDouble(VM *vm, Value *out) {

    if (8 + vm->ip - vm->chunk->code > vm->chunk->count) {

        printf("|| Ran out of bytes!\n");
        return INTERPRET_ERR;

    } else {

        double *read = (double *)vm->ip;

        vm->ip += 8;

        *out = makeNumber(*read);
        return INTERPRET_OK;
    }
}

static InterpretResult readStringRaw(VM *vm, Value *out) {

    uint8_t size;
    if (readByte(vm, &size) != INTERPRET_OK) {

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

#define ANY_OP(op)                                                             \
    if (push(vm, op) != INTERPRET_OK) {                                        \
        printf("|| Could not push result of unary operation (code %d)!\n",     \
               instruction);                                                   \
        return INTERPRET_ERR;                                                  \
    }

#define UNARY_OP                                                               \
    Value a;                                                                   \
    if (pop(vm, &a) != INTERPRET_OK) {                                         \
        printf("|| Expected value for unary operation! (code %d)\n",           \
               instruction);                                                   \
        return INTERPRET_ERR;                                                  \
    }

#define TYPED_UNARY(expected, op)                                              \
    if (a.type == expected) {                                                  \
        ANY_OP(op)                                                             \
    }

#define OBJ_TYPED_UNARY(expected, op)                                          \
    if (isObjType(a, expected)) {                                              \
        ANY_OP(op)                                                             \
    }

#define BINARY_OP                                                              \
    Value a;                                                                   \
    Value b;                                                                   \
    if (pop(vm, &b) != INTERPRET_OK || pop(vm, &a) != INTERPRET_OK) {          \
        printf("|| Expected two values for binary operation! (code %d)\n",     \
               instruction);                                                   \
        return INTERPRET_ERR;                                                  \
    }

#define TYPED_BINARY(expected, op)                                             \
    if (a.type == expected && b.type == expected) {                            \
        ANY_OP(op)                                                             \
    }

#define OBJ_TYPED_BINARY(expected, op)                                         \
    if (isObjType(a, expected) && isObjType(b, expected)) {                    \
        ANY_OP(op)                                                             \
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

            case OP_PUSH_SCOPE: {

                pushScope(&vm->localState);

            } break;

            case OP_POP_SCOPE: {

                size_t popped = popScope(&vm->localState);
                for (size_t i = 0; i < popped; i++) {

                    if (pop(vm, NULL) != INTERPRET_OK) {

                        printf("|| Could not fully pop scope!\n");
                        return INTERPRET_ERR;
                    }
                }

            } break;

            case OP_TYPE: {

                UNARY_OP

                ANY_OP(typeString(

                    vm, a

                    ))

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

                addGlobal(&vm->globalState, index, val);

            } break;

            case OP_LOAD_GLOBAL: {

                uint8_t index;
                if (readByte(vm, &index) != INTERPRET_OK) {

                    printf("|| Expected index to load global!\n");
                    return INTERPRET_ERR;
                }

                Value value;
                if (getGlobal(&vm->globalState, index, &value) !=
                    INTERPRET_OK) {

                    printf("|| Undefined identifier!\n");
                    return INTERPRET_ERR;
                }

                if (push(vm, value) != INTERPRET_OK) {

                    printf("|| Could not push global value!\n");
                    return INTERPRET_ERR;
                }

            } break;

            case OP_DEFINE_LOCAL: {

                uint8_t index;
                if (readByte(vm, &index) != INTERPRET_OK) {

                    printf("|| Expected index to define local variable!\n");
                    return INTERPRET_ERR;
                }

                Value val;
                if (pop(vm, &val) != INTERPRET_OK) {

                    printf("|| Expected value to define local variable!\n");
                    return INTERPRET_ERR;
                }

                addLocal(&vm->localState, index);

                if (index == vm->stackTop - vm->stack) {

                    push(vm, val);

                } else if (index < vm->stackTop - vm->stack) {

                    vm->stack[index] = val;

                } else {

                    printf("|| Local variables indexed out of range!\n");
                    return INTERPRET_ERR;
                }

            } break;

            case OP_LOAD_LOCAL: {

                uint8_t index;
                if (readByte(vm, &index) != INTERPRET_OK) {

                    printf("|| Expected index to load local!\n");
                    return INTERPRET_ERR;
                }

                Value val = vm->stack[index];

                if (push(vm, val) != INTERPRET_OK) {

                    printf("|| Could not push local value!\n");
                    return INTERPRET_ERR;
                }

            } break;

            case OP_POP: {

                UNARY_OP

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

                TYPED_BINARY(VAL_NUMBER, makeNumber(

                                             a.as.number + b.as.number

                                             ))

                else

                    TYPED_BINARY(VAL_INTEGER, makeInteger(

                                                  a.as.integer + b.as.integer

                                                  ))

                        else

                    OBJ_TYPED_BINARY(OBJ_STRING, concatStrings(

                                                     vm, (ObjString *)a.as.obj,
                                                     (ObjString *)b.as.obj

                                                     ))

                        else {

                    printf("|| Cannot add values of type '%s' and '%s'!\n",
                           typeStringLiteral(a), typeStringLiteral(b));
                    printf("|| (Types must be the same, and either numbers, "
                           "integers or strings)\n");
                    return INTERPRET_ERR;
                }

            } break;

            case OP_SUBTRACT: {

                BINARY_OP

                TYPED_BINARY(VAL_NUMBER, makeNumber(

                                             a.as.number - b.as.number

                                             ))

                else

                    TYPED_BINARY(VAL_INTEGER, makeInteger(

                                                  a.as.integer - b.as.integer

                                                  ))

                        else {

                    printf("|| Cannot subtract values of type '%s' and '%s'!\n",
                           typeStringLiteral(a), typeStringLiteral(b));
                    printf("|| (Types must be the same, and either numbers or "
                           "integers)\n");
                    return INTERPRET_ERR;
                }

            } break;

            case OP_MULTIPLY: {

                BINARY_OP

                TYPED_BINARY(VAL_NUMBER, makeNumber(

                                             a.as.number * b.as.number

                                             ))

                else

                    TYPED_BINARY(VAL_INTEGER, makeInteger(

                                                  a.as.integer * b.as.integer

                                                  ))

                        else {

                    printf("|| Cannot multiply values of type '%s' and '%s'!\n",
                           typeStringLiteral(a), typeStringLiteral(b));
                    printf("|| (Types must be the same, and either numbers or "
                           "integers)\n");
                    return INTERPRET_ERR;
                }

            } break;

            case OP_DIVIDE: {

                BINARY_OP

                TYPED_BINARY(VAL_NUMBER, makeNumber(

                                             a.as.number / b.as.number

                                             ))

                else {

                    printf("|| Cannot divide values of type '%s' and '%s'!\n",
                           typeStringLiteral(a), typeStringLiteral(b));
                    printf("|| (Values must be both numbers)\n");
                    return INTERPRET_ERR;
                }

            } break;

            case OP_NEGATE: {

                UNARY_OP

                TYPED_UNARY(VAL_NUMBER, makeNumber(

                                            -a.as.number

                                            ))

                else

                    TYPED_UNARY(VAL_INTEGER, makeInteger(

                                                 -a.as.integer

                                                 ))

                        else {

                    printf("|| Cannot negate a value of type '%s'!\n",
                           typeStringLiteral(a));
                    printf(
                        "|| (Value must be either a number or an integer)\n");
                    return INTERPRET_ERR;
                }

            } break;

            case OP_EQUAL: {

                BINARY_OP

                ANY_OP(makeBoolean(

                    valuesEqual(a, b)

                        ))

            } break;

            case OP_NEQUAL: {

                BINARY_OP

                ANY_OP(makeBoolean(

                    !valuesEqual(a, b)

                        ))

            } break;

            case OP_LESS: {

                BINARY_OP

                TYPED_BINARY(VAL_NUMBER,
                             makeBoolean(

                                 a.as.number < b.as.number - NUMBER_PRECISION

                                 ))

                else

                    TYPED_BINARY(VAL_INTEGER, makeBoolean(

                                                  a.as.integer < b.as.integer

                                                  ))

                        else {

                    printf("|| Cannot compare values of type '%s' and '%s'!\n",
                           typeStringLiteral(a), typeStringLiteral(b));
                    printf("|| (Types must be the same, and either numbers or "
                           "integers)\n");
                    return INTERPRET_ERR;
                }

            } break;

            case OP_NLESS: {

                BINARY_OP

                TYPED_BINARY(VAL_NUMBER,
                             makeBoolean(

                                 a.as.number > b.as.number - NUMBER_PRECISION

                                 ))

                else

                    TYPED_BINARY(VAL_INTEGER, makeBoolean(

                                                  a.as.integer >= b.as.integer

                                                  ))

                        else {

                    printf("|| Cannot compare values of type '%s' and '%s'!\n",
                           typeStringLiteral(a), typeStringLiteral(b));
                    printf("|| (Types must be the same, and either numbers or "
                           "integers)\n");
                    return INTERPRET_ERR;
                }

            } break;

            case OP_GREATER: {

                BINARY_OP

                TYPED_BINARY(VAL_NUMBER,
                             makeBoolean(

                                 a.as.number > b.as.number + NUMBER_PRECISION

                                 ))

                else

                    TYPED_BINARY(VAL_INTEGER, makeBoolean(

                                                  a.as.integer > b.as.integer

                                                  ))

                        else {

                    printf("|| Cannot compare values of type '%s' and '%s'!\n",
                           typeStringLiteral(a), typeStringLiteral(b));
                    printf("|| (Types must be the same, and either numbers or "
                           "integers)\n");
                    return INTERPRET_ERR;
                }

            } break;

            case OP_NGREATER: {

                BINARY_OP

                TYPED_BINARY(VAL_NUMBER,
                             makeBoolean(

                                 a.as.number < b.as.number + NUMBER_PRECISION

                                 ))

                else

                    TYPED_BINARY(VAL_INTEGER, makeBoolean(

                                                  a.as.integer <= b.as.integer

                                                  ))

                        else {

                    printf("|| Cannot compare values of type '%s' and '%s'!\n",
                           typeStringLiteral(a), typeStringLiteral(b));
                    printf("|| (Types must be the same, and either numbers or "
                           "integers)\n");
                    return INTERPRET_ERR;
                }

            } break;

            case OP_NOT: {

                UNARY_OP

                TYPED_UNARY(VAL_BOOL, makeBoolean(

                                          !a.as.boolean

                                          ))

                else {

                    printf("|| Cannot apply ! to a value of type '%s'!\n",
                           typeStringLiteral(a));
                    printf("|| (Value must be a boolean)\n");
                    return INTERPRET_ERR;
                }

            } break;

            case OP_INT: {

                UNARY_OP

                TYPED_UNARY(VAL_INTEGER,

                            a

                )

                else

                    TYPED_UNARY(VAL_NUMBER, makeInteger(

                                                (int32_t)a.as.number

                                                ))

                        else

                    TYPED_UNARY(VAL_BOOL, makeInteger(

                                              a.as.boolean ? 1 : 0

                                              ))

                        else {

                    printf("|| Cannot convert a value of type '%s' to an "
                           "integer!\n",
                           typeStringLiteral(a));
                    printf(
                        "|| (Value must be an integer, number or boolean)\n");
                    return INTERPRET_ERR;
                }

            } break;

            case OP_BOOL: {

                UNARY_OP

                TYPED_UNARY(VAL_BOOL,

                            a

                )

                else

                    TYPED_UNARY(VAL_INTEGER, makeBoolean(

                                                 a.as.integer != 0

                                                 ))

                        else

                    TYPED_UNARY(VAL_NUMBER, makeBoolean(

                                                a.as.number != 0.0

                                                ))

                        else

                    OBJ_TYPED_UNARY(OBJ_STRING,
                                    makeBoolean(

                                        ((ObjString *)a.as.obj)->length != 0

                                        ))

                        else {

                    printf(
                        "|| Cannot convert value of type '%s' to a boolean!\n",
                        typeStringLiteral(a));
                    printf("|| (Value must be a number, integer, boolean or "
                           "string)\n");
                    return INTERPRET_ERR;
                }

            } break;

            case OP_NUM: {

                UNARY_OP

                TYPED_UNARY(VAL_NUMBER,

                            a

                )

                else

                    TYPED_UNARY(VAL_INTEGER, makeNumber(

                                                 (double)a.as.integer

                                                 ))

                        else

                    TYPED_UNARY(VAL_BOOL, makeNumber(

                                              a.as.boolean ? 1.0 : 0.0

                                              ))

                        else {

                    printf(
                        "|| Cannot convert value of type '%s' to a number!\n",
                        typeStringLiteral(a));
                    printf("|| (Value must be a number, integer or boolean)\n");
                    return INTERPRET_ERR;
                }

            } break;

            case OP_STR: {

                UNARY_OP

                OBJ_TYPED_UNARY(OBJ_STRING,

                                a

                )

                else

                    TYPED_UNARY(VAL_BOOL,
                                makeStringFromLiteral(

                                    vm, a.as.boolean ? "true" : "false"

                                    ))

                        else

                    TYPED_UNARY(VAL_INTEGER, makeStringFromInteger(

                                                 vm, a.as.integer

                                                 ))

                        else

                    TYPED_UNARY(VAL_NUMBER, makeStringFromNumber(

                                                vm, a.as.number

                                                ))

                        else {

                    printf(
                        "|| Cannot convert a value of type '%s' to a string!\n",
                        typeStringLiteral(a));
                    printf("|| (Value must be a string, boolean, integer of "
                           "number)\n");
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
