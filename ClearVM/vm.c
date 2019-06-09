
#include "vm.h"

#include "memory.h"
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define IMPL_STACK(T, N)                                                       \
                                                                               \
    void init##T##Stack##N(T##Stack##N *stack) {                               \
                                                                               \
        stack->next = stack->values;                                           \
    }                                                                          \
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
    }                                                                          \
                                                                               \
    Result peek##T##Stack##N(T##Stack##N *stack, T **peeked, size_t offset) {  \
                                                                               \
        if ((size_t)(stack->next - stack->values) <= offset) {                 \
                                                                               \
            return RESULT_ERR;                                                 \
        }                                                                      \
                                                                               \
        if (peeked != NULL) {                                                  \
                                                                               \
            *peeked = (stack->next - offset - 1);                              \
        }                                                                      \
                                                                               \
        return RESULT_OK;                                                      \
    }

IMPL_STACK(Value, 256)
IMPL_STACK(Value, 64)
IMPL_STACK(Frame, 64)

#undef IMPL_STACK

void initFrame(Frame *frame) {

    frame->paramCount = 0;
    initValueStack256(&frame->stack);
    initValueStack64(&frame->locals);
}

#define GET_FRAME                                                              \
    Frame *frame;                                                              \
    if (peekFrameStack64(&vm->frames, &frame, 0) != RESULT_OK) {               \
                                                                               \
        printf("|| Could not get current frame\n");                            \
        return RESULT_ERR;                                                     \
    }

static Result errorInstruction(VM *vm, uint8_t **ip, uint8_t *code,
                               size_t codeLength) {

    UNUSED(vm);
    UNUSED(ip);
    UNUSED(code);
    UNUSED(codeLength);

    printf("|| Unimplemented opcode\n");
    return RESULT_ERR;
}

#define DEFN_READ(name, type)                                                  \
    static Result read##name(uint8_t **ip, uint8_t *code, size_t codeLength,   \
                             type *out) {                                      \
                                                                               \
        if ((size_t)(sizeof(type) + *ip - code) > codeLength) {                \
                                                                               \
            printf("|| Ran out of bytes reading instruction\n");               \
            return RESULT_ERR;                                                 \
        }                                                                      \
                                                                               \
        if (out != NULL) {                                                     \
                                                                               \
            *out = *(type *)(*ip);                                             \
        }                                                                      \
                                                                               \
        *ip += sizeof(type);                                                   \
        return RESULT_OK;                                                      \
    }

DEFN_READ(U8, uint8_t)

#undef DEFN_READ

static Result op_loadConst(VM *vm, uint8_t **ip, uint8_t *code,
                           size_t codeLength) {

    GET_FRAME

    uint8_t index;
    if (readU8(ip, code, codeLength, &index) != RESULT_OK) {

        printf("|| Couldn't read constant index\n");
        return RESULT_ERR;
    }

    if (index >= vm->constantCount) {

        printf("|| Constant index %d out of range\n", index);
        return RESULT_ERR;
    }

    Value value = vm->constants[index];

    if (pushValueStack256(&frame->stack, value) != RESULT_OK) {

        printf("|| Could not push constant value\n");
        return RESULT_ERR;
    }

    return RESULT_OK;
}

static Result op_true(VM *vm, uint8_t **ip, uint8_t *code, size_t codeLength) {

    UNUSED(ip);
    UNUSED(code);
    UNUSED(codeLength);

    GET_FRAME

    Value truthValue;
    truthValue.type = VAL_BOOL;
    truthValue.as.b = true;

    return pushValueStack256(&frame->stack, truthValue);
}

static Result op_false(VM *vm, uint8_t **ip, uint8_t *code, size_t codeLength) {

    UNUSED(ip);
    UNUSED(code);
    UNUSED(codeLength);

    GET_FRAME

    Value falseValue;
    falseValue.type = VAL_BOOL;
    falseValue.as.b = false;

    return pushValueStack256(&frame->stack, falseValue);
}

static Result op_nil(VM *vm, uint8_t **ip, uint8_t *code, size_t codeLength) {

    UNUSED(ip);
    UNUSED(code);
    UNUSED(codeLength);

    GET_FRAME

    Value nilValue;
    nilValue.type = VAL_NIL;

    return pushValueStack256(&frame->stack, nilValue);
}

static Result op_defineGlobal(VM *vm, uint8_t **ip, uint8_t *code,
                              size_t codeLength) {

    GET_FRAME

    uint8_t index;
    if (readU8(ip, code, codeLength, &index) != RESULT_OK) {

        printf("|| Could not read global index\n");
        return RESULT_ERR;
    }

    Value value;
    if (popValueStack256(&frame->stack, &value) != RESULT_OK) {

        printf("|| Could not pop global value\n");
        return RESULT_ERR;
    }

    Value nilValue;
    nilValue.type = VAL_NIL;

    // TODO: This probably shouldn't be a ValueList
    while (setValueList(&vm->globals, index, value) != RESULT_OK) {

        appendValueList(&vm->globals, nilValue);
    }

    return RESULT_OK;
}

static Result op_loadGlobal(VM *vm, uint8_t **ip, uint8_t *code,
                            size_t codeLength) {

    GET_FRAME

    uint8_t index;
    if (readU8(ip, code, codeLength, &index) != RESULT_OK) {

        printf("|| Could not read global index\n");
        return RESULT_ERR;
    }

    Value global;
    if (getValueList(&vm->globals, index, &global) != RESULT_OK) {

        printf("|| Undefined global %d\n", index);
        return RESULT_ERR;
    }

    return pushValueStack256(&frame->stack, global);
}

#undef GET_FRAME

Result initVM(VM *vm) {

    vm->constants = NULL;
    vm->constantCount = 0;

    vm->objects = NULL;

    initValueList(&vm->globals);
    initFrameStack64(&vm->frames);

    Frame globalFrame;

    if (pushFrameStack64(&vm->frames, globalFrame) != RESULT_OK) {

        printf("|| Could not push global frame\n");
        return RESULT_ERR;
    }

    Frame *globalPtr;
    if (peekFrameStack64(&vm->frames, &globalPtr, 0) != RESULT_OK) {

        printf("|| Could not peek global frame\n");
        return RESULT_ERR;
    }

    initFrame(globalPtr);

    for (size_t i = 0; i < OP_COUNT; i++) {

        vm->instructions[i] = errorInstruction;
    }

#define INSTR(opcode, instr)                                                   \
    do {                                                                       \
        vm->instructions[opcode] = instr;                                      \
    } while (0)

    INSTR(OP_LOAD_CONST, op_loadConst);
    INSTR(OP_TRUE, op_true);
    INSTR(OP_FALSE, op_false);
    INSTR(OP_NIL, op_nil);

    INSTR(OP_DEFINE_GLOBAL, op_defineGlobal);
    INSTR(OP_LOAD_GLOBAL, op_loadGlobal);

#undef INSTR

    return RESULT_OK;
}

static Value makeObject(VM *vm, size_t size, ObjectType type) {

    void *ptr = reallocate(NULL, size);

    ObjectValue *obj = ALLOCATE(ObjectValue);
    obj->type = type;
    obj->next = vm->objects;
    obj->ptr = ptr;

    vm->objects = obj;

    Value result;
    result.type = VAL_OBJ;
    result.as.obj = obj;

    return result;
}

static Value makeString(VM *vm, char *data, size_t length) {

    Value result = makeObject(vm, sizeof(StringObject), OBJ_STRING);

    StringObject *strObj = (StringObject *)result.as.obj->ptr;
    strObj->length = length;
    strObj->data = data;

    return result;
}

static Result loadConstants(VM *vm, uint8_t *code, size_t length,
                            size_t *outIndex) {

    size_t index = 0;

    size_t constantCount = *(uint32_t *)code;
    index = index + sizeof(uint32_t);

    vm->constants =
        GROW_ARRAY(vm->constants, Value, vm->constantCount, constantCount);
    vm->constantCount = constantCount;

    for (size_t i = 0; i < constantCount; i++) {

        switch (code[index]) {

            case OP_INTEGER: {

                if (index >= length - sizeof(int32_t)) {

                    printf("|| EOF reached while parsing constant integer\n");
                    return RESULT_ERR;
                }

                index++;

                int32_t value = *(int32_t *)(code + index);
                vm->constants[i].as.s32 = value;

                index += sizeof(int32_t);

            } break;

            case OP_NUMBER: {

                if (index >= length - sizeof(double)) {

                    printf("|| EOF reached while parsing constant number\n");
                    return RESULT_ERR;
                }

                index++;

                double value = *(double *)(code + index);
                vm->constants[i].as.f64 = value;

                index += sizeof(double);

            } break;

            case OP_STRING: {

                index++;

                if (index > length - sizeof(uint8_t)) {

                    printf(
                        "\n|| EOF reached instead of constant string length\n");
                    return RESULT_ERR;
                }

                uint8_t strLength = *(uint8_t *)(code + index);
                index += sizeof(uint8_t);

                if (index > length - strLength) {

                    printf("\n|| Reached EOF while parsing constant string\n");
                    return RESULT_ERR;
                }

                char *str = ALLOCATE_ARRAY(char, strLength + 1);
                str[strLength] = '\0';

                memcpy(str, code + index, strLength);
                index += strLength;

                vm->constants[i] = makeString(vm, str, strLength);

            } break;

            default: {

                printf("\n|| Unknown constant type %d\n", code[index]);
                return RESULT_ERR;

            } break;
        }
    }

    *outIndex = index;
    return RESULT_OK;
}

Result executeCode(VM *vm, uint8_t *code, size_t length) {

    size_t index;
    if (loadConstants(vm, code, length, &index) != RESULT_OK) {

        printf("|| Could not load constants\n");
        return RESULT_ERR;
    }

    uint8_t *ip = code + index;

    while ((size_t)(ip - code) < length) {

        uint8_t opcode = *ip++;

        if (opcode >= OP_COUNT) {

            printf("|| Unknown opcode %d\n", opcode);
            return RESULT_ERR;
        }

        if (vm->instructions[opcode](vm, &ip, code, length) != RESULT_OK) {

            printf("|| Opcode %d failed\n", opcode);
            return RESULT_ERR;
        }
    }

    return RESULT_OK;
}

static void freeObjects(VM *vm) {

    ObjectValue *obj = vm->objects;

    while (obj != NULL) {

        ObjectValue *next = obj->next;
        freeObject(obj);
        obj = next;
    }
}

void freeVM(VM *vm) {

    freeObjects(vm);

    if (vm->constantCount > 0) {

        FREE_ARRAY(Value, vm->constants, vm->constantCount);
    }

    freeValueList(&vm->globals);
}
