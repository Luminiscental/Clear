
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

InterpretResult popScope(LocalState *state, size_t *out) {

    Scope *popped = state->currentScope;
    if (popped == NULL) {
        printf("|| Cannot pop global scope!\n");
        return INTERPRET_ERR;
    }
    state->currentScope = popped->parent;
    state->localIndex -= popped->variables;
    if (out != NULL) {

        *out = popped->variables;
    }
    return INTERPRET_OK;
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

void initFrame(VM *vm, CallFrame *caller, size_t arity, CallFrame *frame) {

    initLocalState(&frame->localState);
    resetStack(frame);
    frame->vm = vm;
    frame->arity = arity;

    if (caller != NULL) {

        frame->params = caller->stackTop - arity;

    } else {

        frame->ip = vm->chunk->code;
    }
}

static InterpretResult call(VM *vm, ObjFunction *function, uint8_t arity) {

    if (vm->frameDepth >= FRAMES_MAX - 1) {

        printf("|| Stack overflow!\n");
        return INTERPRET_ERR;
    }

    CallFrame *caller = &vm->frames[vm->frameDepth];
    CallFrame *callee = &vm->frames[vm->frameDepth + 1];

    initFrame(vm, caller, arity, callee);
    callee->ip = function->code;

    vm->frameDepth++;

    return INTERPRET_OK;
}

void initVM(VM *vm) {
    vm->objects = NULL;
    initTable(&vm->strings);

    initGlobalState(&vm->globalState);
}

void resetStack(CallFrame *frame) { frame->stackTop = frame->stack; }

InterpretResult push(CallFrame *frame, Value value) {

    if (frame->stackTop >= frame->stack + STACK_MAX - 1) {

        printf("|| Stack overflow!\n");
        return INTERPRET_ERR;

    } else {

        *frame->stackTop = value;
        frame->stackTop++;
        return INTERPRET_OK;
    }
}

InterpretResult pop(CallFrame *frame, Value *out) {

    if (frame->stackTop <= frame->stack) {

        printf("|| Stack underflow!\n");
        return INTERPRET_ERR;

    } else {

        frame->stackTop--;

        if (out != NULL)
            *out = *frame->stackTop;

        return INTERPRET_OK;
    }
}

InterpretResult peekDistance(CallFrame *frame, int32_t lookback, Value *out) {

    if (frame->stackTop - lookback <= frame->stack) {

        printf("|| Stack underflow!\n");
        return INTERPRET_ERR;

    } else {

        if (out != NULL)
            *out = frame->stackTop[-lookback - 1];

        return INTERPRET_OK;
    }
}

InterpretResult peek(CallFrame *frame, Value *out) {

    return peekDistance(frame, 0, out);
}

void freeFrame(CallFrame *frame) { freeLocalState(&frame->localState); }

void freeVM(VM *vm) {

    freeTable(&vm->strings);
    freeObjects(vm);
}

InterpretResult interpret(VM *vm, Chunk *chunk) {

    vm->chunk = chunk;

    return run(vm);
}

static InterpretResult readByte(VM *vm, CallFrame *frame, uint8_t *out) {

    if (1 + frame->ip - vm->chunk->code > vm->chunk->count) {

        printf("|| Ran out of bytes!\n");
        return INTERPRET_ERR;

    } else {

        *out = *frame->ip++;
        return INTERPRET_OK;
    }
}

static InterpretResult readUint(VM *vm, CallFrame *frame, uint32_t *out) {

    if (sizeof(uint32_t) + frame->ip - vm->chunk->code > vm->chunk->count) {

        printf("|| Ran out of bytes!\n");
        return INTERPRET_ERR;
    }

    uint32_t *read = (uint32_t *)frame->ip;

    frame->ip += sizeof(uint32_t);

    if (out != NULL)
        *out = *read;
    return INTERPRET_OK;
}

#define ANY_OP(op)                                                             \
    if (push(frame, op) != INTERPRET_OK) {                                     \
        printf("|| Could not push result of unary operation (code %d)!\n",     \
               instruction);                                                   \
        return INTERPRET_ERR;                                                  \
    }

#define UNARY_OP                                                               \
    Value a;                                                                   \
    if (pop(frame, &a) != INTERPRET_OK) {                                      \
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
    if (pop(frame, &b) != INTERPRET_OK || pop(frame, &a) != INTERPRET_OK) {    \
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

static void printStack(CallFrame *frame) {

    printf("          ");

    for (Value *slot = frame->stack; slot < frame->stackTop; slot++) {

        printf("[ ");
        printValue(*slot, false);
        printf(" ]");
    }

    printf("\n");
}

static InterpretResult loop(VM *vm, CallFrame *frame) {

    uint32_t offset;
    if (readUint(vm, frame, &offset) != INTERPRET_OK) {

        printf("|| Could not read offset to loop by!\n");
        return INTERPRET_ERR;
    }

    frame->ip -= offset;

    return INTERPRET_OK;
}

static InterpretResult jump(VM *vm, CallFrame *frame) {

    uint32_t offset;
    if (readUint(vm, frame, &offset) != INTERPRET_OK) {

        printf("|| Could not read offset to jump by!\n");
        return INTERPRET_ERR;
    }

    frame->ip += offset;

    return INTERPRET_OK;
}

static InterpretResult jumpIfFalse(VM *vm, CallFrame *frame, bool condition) {

    uint32_t offset;
    if (readUint(vm, frame, &offset) != INTERPRET_OK) {

        printf("|| Could not read offset to jump by!\n");
        return INTERPRET_ERR;
    }

    if (!condition) {

        frame->ip += offset;
    }

    return INTERPRET_OK;
}

InterpretResult run(VM *vm) {

    initFrame(vm, NULL, 0, vm->frames);
    vm->frameDepth = 0;
    vm->frames->ip = vm->chunk->code + vm->chunk->start;

    for (CallFrame *frame = &vm->frames[vm->frameDepth];
         frame->ip - vm->chunk->code < vm->chunk->count;
         frame = &vm->frames[vm->frameDepth]) {

#ifdef DEBUG_STACK

        printStack(frame);

#endif

#ifdef DEBUG_TRACE

        disassembleInstruction(vm->chunk, frame->ip - vm->chunk->code);

#endif

        uint8_t instruction;
        if (readByte(vm, frame, &instruction) != INTERPRET_OK) {

            printf("|| Ran out of instructions!\n");
            return INTERPRET_ERR;
        }

        switch (instruction) {

            case OP_LOOP: {

                if (loop(vm, frame) != INTERPRET_OK) {

                    printf("|| Could not loop!\n");
                    return INTERPRET_ERR;
                }

            } break;

            case OP_JUMP: {

                if (jump(vm, frame) != INTERPRET_OK) {

                    printf("|| Could not jump!\n");
                    return INTERPRET_ERR;
                }

            } break;

            case OP_JUMP_IF_NOT: {

                Value condition;
                if (peek(frame, &condition) != INTERPRET_OK) {

                    printf("|| Could not read jump condition!\n");
                    return INTERPRET_ERR;
                }

                if (condition.type != VAL_BOOL) {

                    printf("|| Expected boolean as jump condition!\n");
                    return INTERPRET_ERR;
                }

                if (jumpIfFalse(vm, frame, condition.as.boolean) !=
                    INTERPRET_OK) {

                    printf("|| Could not jump!\n");
                    return INTERPRET_ERR;
                }

            } break;

            case OP_PUSH_SCOPE: {

                pushScope(&frame->localState);

            } break;

            case OP_POP_SCOPE: {

                size_t popped;
                if (popScope(&frame->localState, &popped) != INTERPRET_OK) {

                    printf("|| Scope popping failed!\n");
                    return INTERPRET_ERR;
                }

                for (size_t i = 0; i < popped; i++) {

                    if (pop(frame, NULL) != INTERPRET_OK) {

                        printf("|| Could not fully pop scope!\n");
                        return INTERPRET_ERR;
                    }
                }

            } break;

            case OP_TRUE: {

                Value val = makeBoolean(true);

                if (push(frame, val) != INTERPRET_OK) {

                    printf("|| Could not push boolean literal!\n");
                    return INTERPRET_ERR;
                }

            } break;

            case OP_FALSE: {

                Value val = makeBoolean(false);

                if (push(frame, val) != INTERPRET_OK) {

                    printf("|| Could not push boolean literal!\n");
                    return INTERPRET_ERR;
                }

            } break;

            case OP_DEFINE_GLOBAL: {

                uint8_t index;
                if (readByte(vm, frame, &index) != INTERPRET_OK) {

                    printf("|| Expected index to define global!\n");
                    return INTERPRET_ERR;
                }

                Value val;
                if (pop(frame, &val) != INTERPRET_OK) {

                    printf("|| Expected value to define global!\n");
                    return INTERPRET_ERR;
                }

                addGlobal(&vm->globalState, index, val);

            } break;

            case OP_LOAD_GLOBAL: {

                uint8_t index;
                if (readByte(vm, frame, &index) != INTERPRET_OK) {

                    printf("|| Expected index to load global!\n");
                    return INTERPRET_ERR;
                }

                Value value;
                if (getGlobal(&vm->globalState, index, &value) !=
                    INTERPRET_OK) {

                    printf("|| Undefined identifier!\n");
                    return INTERPRET_ERR;
                }

                if (push(frame, value) != INTERPRET_OK) {

                    printf("|| Could not push global value!\n");
                    return INTERPRET_ERR;
                }

            } break;

            case OP_DEFINE_LOCAL: {

                uint8_t index;
                if (readByte(vm, frame, &index) != INTERPRET_OK) {

                    printf("|| Expected index to define local variable!\n");
                    return INTERPRET_ERR;
                }

                Value val;
                if (pop(frame, &val) != INTERPRET_OK) {

                    printf("|| Expected value to define local variable!\n");
                    return INTERPRET_ERR;
                }

                addLocal(&frame->localState, index);

                if (index == frame->stackTop - frame->stack) {

                    push(frame, val);

                } else if (index < frame->stackTop - frame->stack) {

                    frame->stack[index] = val;

                } else {

                    printf("|| Local variables indexed out of range!\n");
                    return INTERPRET_ERR;
                }

            } break;

            case OP_LOAD_LOCAL: {

                uint8_t index;
                if (readByte(vm, frame, &index) != INTERPRET_OK) {

                    printf("|| Expected index to load local!\n");
                    return INTERPRET_ERR;
                }

                Value val = frame->stack[index];

                if (push(frame, val) != INTERPRET_OK) {

                    printf("|| Could not push local value!\n");
                    return INTERPRET_ERR;
                }

            } break;

            case OP_POP: {

                UNARY_OP

            } break;

            case OP_RETURN: {

                Value result;
                if (pop(frame, &result) != INTERPRET_OK) {

                    printf("|| Could not pop value to return!\n");
                    return INTERPRET_ERR;
                }

                if (vm->frameDepth == 0) {

                    printf("|| Stack underflow! Cannot return from global "
                           "scope\n");
                    return INTERPRET_ERR;
                }

                CallFrame *caller = &vm->frames[vm->frameDepth - 1];

                for (size_t index = 0; index <= frame->arity; index++) {

                    if (pop(caller, NULL) != INTERPRET_OK) {

                        printf("|| Could not pop call context!\n");
                        return INTERPRET_ERR;
                    }
                }

                push(caller, result);

                freeFrame(frame);
                vm->frameDepth--;

            } break;

            case OP_PRINT_BLANK: {

                printf("\n");

            } break;

            case OP_PRINT: {

                Value value;

                if (pop(frame, &value) != INTERPRET_OK) {

                    printf("|| Expected value to print!\n");
                    return INTERPRET_ERR;
                }

                printValue(value, true);

            } break;

            case OP_LOAD_CONST: {

                uint8_t index;
                if (readByte(vm, frame, &index) != INTERPRET_OK) {

                    printf("|| Expected index of constant to load!\n");
                    return INTERPRET_ERR;
                }

                if (index >= vm->chunk->constants.count) {

                    printf("|| Constant out of index!\n");
                    return INTERPRET_ERR;
                }

                Value constant = vm->chunk->constants.values[index];

                if (push(frame, constant) != INTERPRET_OK) {

                    printf("|| Could not push constant value!\n");
                    return INTERPRET_ERR;
                }

            } break;

            case OP_LOAD_PARAM: {

                uint8_t index;
                if (readByte(vm, frame, &index) != INTERPRET_OK) {

                    printf("|| Expected index of constant to load!\n");
                    return INTERPRET_ERR;
                }

                if (frame->params == NULL) {

                    printf("|| Cannot load parameter in global scope!\n");
                    return INTERPRET_ERR;
                }

                Value param = frame->params[index];
                if (push(frame, param) != INTERPRET_OK) {

                    printf("|| Could not push parameter!\n");
                    return INTERPRET_ERR;
                }

            } break;

            case OP_START_FUNCTION: {

                uint32_t size;
                if (readUint(vm, frame, &size) != INTERPRET_OK) {

                    printf("|| Expected function size!\n");
                    return INTERPRET_ERR;
                }

                Value function = makeFunction(vm, frame->ip, (size_t)size);
                frame->ip += size;
                push(frame, function);

            } break;

            case OP_CALL: {

                uint8_t arity;
                if (readByte(vm, frame, &arity) != INTERPRET_OK) {

                    printf("|| Expected arity for function call!\n");
                    return INTERPRET_ERR;
                }

                Value function;
                if (peekDistance(frame, arity, &function) != INTERPRET_OK) {

                    printf("|| Could not load function to call!\n");
                    return INTERPRET_ERR;
                }

                if (!isObjType(function, OBJ_FUNCTION)) {

                    printf("|| Cannot call non-function!\n");
                    return INTERPRET_ERR;
                }

                ObjFunction *functionObj = (ObjFunction *)function.as.obj;
                if (call(vm, functionObj, arity) != INTERPRET_OK) {

                    printf("|| Could not call function!\n");
                    return INTERPRET_ERR;
                }

            } break;

                // clang can't appreciate artistic preproc defs smh
                /* clang-format off */

            case OP_ADD: {

                BINARY_OP

                    TYPED_BINARY(VAL_NUMBER, makeNumber(
                        a.as.number + b.as.number))

                else

                    TYPED_BINARY(VAL_INTEGER, makeInteger(
                        a.as.integer + b.as.integer))

                else

                    OBJ_TYPED_BINARY(OBJ_STRING, concatStrings(vm,
                        (ObjString *)a.as.obj, (ObjString *)b.as.obj))

                else {

                    printf("|| Invalid types passed to binary operator '+'!\n");
                    return INTERPRET_ERR;
                }

            } break;

            case OP_SUBTRACT: {

                BINARY_OP

                    TYPED_BINARY(VAL_NUMBER, makeNumber(
                        a.as.number - b.as.number))

                else

                    TYPED_BINARY(VAL_INTEGER, makeInteger(
                        a.as.integer - b.as.integer))

                else {

                    printf("|| Invalid types passed to binary operator '-'!\n");
                    return INTERPRET_ERR;
                }

            } break;

            case OP_MULTIPLY: {

                BINARY_OP

                    TYPED_BINARY(VAL_NUMBER, makeNumber(
                        a.as.number * b.as.number))

                else

                    TYPED_BINARY(VAL_INTEGER, makeInteger(
                        a.as.integer * b.as.integer))

                else {

                    printf("|| Invalid types passed to binary operator '*'!\n");
                    return INTERPRET_ERR;
                }

            } break;

            case OP_DIVIDE: {

                BINARY_OP

                    TYPED_BINARY(VAL_NUMBER, makeNumber(
                        a.as.number / b.as.number))

                else {

                    printf("|| Invalid types passed to binary operator '/'!\n");
                    return INTERPRET_ERR;
                }

            } break;

            case OP_NEGATE: {

                UNARY_OP

                    TYPED_UNARY(VAL_NUMBER, makeNumber(
                        -a.as.number))

                else

                    TYPED_UNARY(VAL_INTEGER, makeInteger(
                        -a.as.integer))

                else {

                    printf("|| Invalid types passed to unary operator '-'!\n");
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

                    TYPED_BINARY(VAL_NUMBER, makeBoolean(
                        a.as.number < b.as.number - NUMBER_PRECISION))

                else

                    TYPED_BINARY(VAL_INTEGER, makeBoolean(
                        a.as.integer < b.as.integer))

                else {

                    printf("|| Invalid types passed to comparison operator '<'!\n");
                    return INTERPRET_ERR;
                }

            } break;

            case OP_NLESS: {

                BINARY_OP

                    TYPED_BINARY(VAL_NUMBER, makeBoolean(
                        a.as.number > b.as.number - NUMBER_PRECISION))

                else

                    TYPED_BINARY(VAL_INTEGER, makeBoolean(
                        a.as.integer >= b.as.integer))

                else {

                    printf("|| Invalid types passed to comparison operator '>='!\n");
                    return INTERPRET_ERR;
                }

            } break;

            case OP_GREATER: {

                BINARY_OP

                    TYPED_BINARY(VAL_NUMBER, makeBoolean(
                        a.as.number > b.as.number + NUMBER_PRECISION))

                else

                    TYPED_BINARY(VAL_INTEGER, makeBoolean(
                        a.as.integer > b.as.integer))

                else {

                    printf("|| Invalid types passed to comparison operator '>'!\n");
                    return INTERPRET_ERR;
                }

            } break;

            case OP_NGREATER: {

                BINARY_OP

                    TYPED_BINARY(VAL_NUMBER, makeBoolean(
                        a.as.number < b.as.number + NUMBER_PRECISION))

                else

                    TYPED_BINARY(VAL_INTEGER, makeBoolean(
                        a.as.integer <= b.as.integer))

                else {

                    printf("|| Invalid types passed to comparison operator '<='!\n");
                    return INTERPRET_ERR;
                }

            } break;

            case OP_NOT: {

                UNARY_OP

                    TYPED_UNARY(VAL_BOOL, makeBoolean(
                        !a.as.boolean))

                else {

                    printf("|| Invalid types passed to unary operator '!'!\n");
                    return INTERPRET_ERR;
                }

            } break;

            case OP_INT: {

                UNARY_OP

                    TYPED_UNARY(VAL_INTEGER, a)

                else

                    TYPED_UNARY(VAL_NUMBER, makeInteger(
                        (int32_t)a.as.number))

                else

                    TYPED_UNARY(VAL_BOOL, makeInteger(
                        a.as.boolean ? 1 : 0))

                else {

                    printf("|| Invalid type passed to built-in function 'int'!\n");
                    return INTERPRET_ERR;
                }

            } break;

            case OP_BOOL: {

                UNARY_OP

                    TYPED_UNARY(VAL_BOOL, a)

                else

                    TYPED_UNARY(VAL_INTEGER, makeBoolean(
                        a.as.integer != 0))

                else

                    TYPED_UNARY(VAL_NUMBER, makeBoolean(
                        a.as.number != 0.0))

                else

                    OBJ_TYPED_UNARY(OBJ_STRING, makeBoolean(
                        ((ObjString *)a.as.obj)->length != 0))

                else {

                    printf("|| Invalid type passed to built-in function 'bool'!\n");
                    return INTERPRET_ERR;
                }

            } break;

            case OP_NUM: {

                UNARY_OP

                    TYPED_UNARY(VAL_NUMBER, a)

                else

                    TYPED_UNARY(VAL_INTEGER, makeNumber(
                        (double)a.as.integer))

                else

                    TYPED_UNARY(VAL_BOOL, makeNumber(
                        a.as.boolean ? 1.0 : 0.0))

                else {

                    printf("|| Invalid type passed to built-in function 'num'!\n");
                    return INTERPRET_ERR;
                }

            } break;

            case OP_STR: {

                UNARY_OP

                    OBJ_TYPED_UNARY(OBJ_STRING, a)

                else

                    TYPED_UNARY(VAL_BOOL, makeStringFromLiteral(vm,
                        a.as.boolean ? "true" : "false"))

                else

                    TYPED_UNARY(VAL_INTEGER, makeStringFromInteger(vm,
                        a.as.integer))

                else

                    TYPED_UNARY(VAL_NUMBER, makeStringFromNumber(vm,
                        a.as.number))

                else {

                    printf("|| Invalid type passed to built-in function 'str'!\n");
                    return INTERPRET_ERR;
                }

            } break;

                /* clang-format on */
                // smh

            default: {

                printf("|| Invalid op code %d!\n", instruction);
                return INTERPRET_ERR;

            } break;
        }
    }

    if (vm->frameDepth > 0) {

        printf("|| Call stack failed to unwind!\n");
        return INTERPRET_ERR;
    }

    freeFrame(vm->frames);

    return INTERPRET_OK;
}

#undef OBJ_TYPED_BINARY
#undef TYPED_BINARY
#undef BINARY_OP
#undef TYPED_UNARY
#undef UNARY_OP
#undef ANY_OP
