
#include "vm.h"

#include "memory.h"
#include "value.h"
#include <stdio.h>
#include <string.h>
#include <time.h>

void initGlobalArray(GlobalArray *array) {

    for (size_t i = 0; i < GLOBAL_MAX; i++) {

        array->isSet[i] = false;
    }
}

Result getGlobal(GlobalArray *array, size_t index, Value *out) {

    if (index >= GLOBAL_MAX) {

        return RESULT_ERR;
    }

    if (!array->isSet[index]) {

        return RESULT_ERR;
    }

    if (out != NULL) {

        *out = array->data[index];
    }

    return RESULT_OK;
}

Result setGlobal(GlobalArray *array, size_t index, Value in) {

    if (index >= GLOBAL_MAX) {

        return RESULT_ERR;
    }

    array->data[index] = in;
    array->isSet[index] = true;

    return RESULT_OK;
}

static Result readU8(VM *vm, uint8_t *out) {

    if ((long)sizeof(uint8_t) > vm->end - vm->ip) {

        printf("|| Ran out of bytes reading instruction\n");
        return RESULT_ERR;
    }

    if (out != NULL) {

        *out = *(uint8_t *)(vm->ip);
    }

    vm->ip += sizeof(uint8_t);
    return RESULT_OK;
}

#define POP(name)                                                              \
    if (vm->sp - vm->stack == 0) {                                             \
                                                                               \
        printf("|| Stack underflow\n");                                        \
        return RESULT_ERR;                                                     \
    }                                                                          \
    Value name = *--vm->sp;

#define PUSH(name)                                                             \
    if (vm->sp - vm->stack == STACK_MAX) {                                     \
                                                                               \
        printf("|| Stack overflow\n");                                         \
        return RESULT_ERR;                                                     \
    } else {                                                                   \
        *vm->sp++ = name;                                                      \
    }

#define PEEK(name, offset)                                                     \
    if (vm->sp - vm->stack <= offset) {                                        \
                                                                               \
        printf("|| Peek under-range\n");                                       \
        return RESULT_ERR;                                                     \
    }                                                                          \
    Value *name = vm->sp - offset - 1;

#define READ(name)                                                             \
    uint8_t name;                                                              \
    if (readU8(vm, &name) != RESULT_OK) {                                      \
        printf("|| Could not read byte\n");                                    \
        return RESULT_ERR;                                                     \
    }

static Result errorInstruction(VM *vm) {

    UNUSED(vm);

    printf("|| Unimplemented opcode\n");
    return RESULT_ERR;
}

// TODO: Make this consistent with disassembly
#ifdef DEBUG_TRACE
#define TRACE(x) x
#else
#define TRACE(x)
#endif

#define UNARY_OP(name, op)                                                     \
    static Result op_##name(VM *vm) {                                          \
        TRACE(printf("op_" #name "\n");)                                       \
        PEEK(value, 0)                                                         \
        Value a = *value;                                                      \
        *value = op;                                                           \
        return RESULT_OK;                                                      \
    }

#define BINARY_OP(name, op)                                                    \
    static Result op_##name(VM *vm) {                                          \
        TRACE(printf("op_" #name "\n");)                                       \
        POP(second)                                                            \
        PEEK(first, 0)                                                         \
        Value a = *first;                                                      \
        Value b = second;                                                      \
        *first = op;                                                           \
        return RESULT_OK;                                                      \
    }

static Result op_pushConst(VM *vm) {

    TRACE(printf("op_pushConst\n");)

    READ(index)

    if (index >= vm->constantCount) {

        printf("|| Constant index %d out of range\n", index);
        return RESULT_ERR;
    }

    PUSH(vm->constants[index])

    return RESULT_OK;
}

static Result op_pushTrue(VM *vm) {

    TRACE(printf("op_pushTrue\n");)

    PUSH(makeBool(true))

    return RESULT_OK;
}

static Result op_pushFalse(VM *vm) {

    TRACE(printf("op_pushFalse\n");)

    PUSH(makeBool(false))

    return RESULT_OK;
}

static Result op_pushNil(VM *vm) {

    TRACE(printf("op_pushNil\n");)

    Value nilValue;
    nilValue.type = VAL_NIL;

    PUSH(nilValue);

    return RESULT_OK;
}

static Result op_setGlobal(VM *vm) {

    TRACE(printf("op_setGlobal\n");)

    READ(index)

    POP(value)

    if (setGlobal(&vm->globals, index, value) != RESULT_OK) {

        printf("|| Invalid global index %d\n", index);
        return RESULT_ERR;
    }

    return RESULT_OK;
}

static Result op_pushGlobal(VM *vm) {

    TRACE(printf("op_pushGlobal\n");)

    READ(index)

    Value global;
    if (getGlobal(&vm->globals, index, &global) != RESULT_OK) {

        printf("|| Undefined global %d\n", index);
        return RESULT_ERR;
    }

    PUSH(global)

    return RESULT_OK;
}

static Result op_setLocal(VM *vm) {

    TRACE(printf("op_setLocal\n");)

    READ(index)

    POP(value)

    if (index >= vm->sp - vm->fp) {

        printf("|| Local %d out of range\n", index);
        return RESULT_ERR;
    }

    vm->fp[index] = value;

    return RESULT_OK;
}

static Result op_getLocal(VM *vm) {

    TRACE(printf("op_getLocal\n");)

    READ(index)

    if (index >= vm->sp - vm->fp) {

        printf("|| Local %d out of range\n", index);
        return RESULT_ERR;
    }

    PUSH(vm->fp[index])

    return RESULT_OK;
}

static Result op_int(VM *vm) {

    TRACE(printf("op_int\n");)

    PEEK(value, 0)

    switch (value->type) {

        case VAL_BOOL: {

            *value = makeInt(value->as.b ? 1 : 0);

        } break;

        case VAL_INT:
            break;

        case VAL_NIL: {

            *value = makeInt(0);

        } break;

        case VAL_NUM: {

            *value = makeInt((int)value->as.f64);

        } break;

        case VAL_OBJ: {

            printf("|| Cannot cast object types\n");
            return RESULT_ERR;

        } break;

        default: {

            printf("|| Unknown value type %d\n", value->type);
            return RESULT_ERR;

        } break;
    }

    return RESULT_OK;
}

static Result op_bool(VM *vm) {

    TRACE(printf("op_bool\n");)

    PEEK(value, 0)

    switch (value->type) {

        case VAL_BOOL:
            break;

        case VAL_INT: {

            *value = makeBool(value->as.s32 != 0);

        } break;

        case VAL_NIL: {

            *value = makeBool(false);

        } break;

        case VAL_NUM: {

            *value = makeBool(value->as.f64 != 0);

        } break;

        case VAL_OBJ: {

            printf("|| Cannot cast object types\n");
            return RESULT_ERR;

        } break;

        default: {

            printf("|| Unknown value type %d\n", value->type);
            return RESULT_ERR;

        } break;
    }

    return RESULT_OK;
}

static Result op_num(VM *vm) {

    TRACE(printf("op_num\n");)

    PEEK(value, 0)

    switch (value->type) {

        case VAL_BOOL: {

            *value = makeNum(value->as.b ? 1.0 : 0.0);

        } break;

        case VAL_INT: {

            *value = makeNum((double)value->as.s32);

        } break;

        case VAL_NIL: {

            *value = makeNum(0.0);

        } break;

        case VAL_NUM:
            break;

        case VAL_OBJ: {

            printf("|| Cannot cast object types\n");
            return RESULT_ERR;

        } break;

        default: {

            printf("|| Unknown value type %d\n", value->type);
            return RESULT_ERR;

        } break;
    }

    return RESULT_OK;
}

static Result op_str(VM *vm) {

    TRACE(printf("op_str\n");)

    PEEK(value, 0)

    return stringifyValue(vm, *value, value);
}

static Result op_clock(VM *vm) {

    TRACE(printf("op_clock\n");)

    PUSH(makeNum((double)clock() / CLOCKS_PER_SEC))

    return RESULT_OK;
}

static Result op_print(VM *vm) {

    TRACE(printf("op_print\n");)

    POP(str)

    if (str.type != VAL_OBJ || str.as.obj->type != OBJ_STRING) {

        printf("|| Cannot print non-string value\n");
        return RESULT_ERR;
    }

    StringObject *strObj = (StringObject *)str.as.obj->ptr;
    printf("%s\n", strObj->data);

    return RESULT_OK;
}

static Result op_pop(VM *vm) {

    TRACE(printf("op_pop\n");)

    POP(_)
    UNUSED(_);

    return RESULT_OK;
}

UNARY_OP(intNeg, makeInt(-a.as.s32))
UNARY_OP(numNeg, makeNum(-a.as.f64))

BINARY_OP(intAdd, makeInt(a.as.s32 + b.as.s32))
BINARY_OP(numAdd, makeNum(a.as.f64 + b.as.f64))

BINARY_OP(intSub, makeInt(a.as.s32 - b.as.s32))
BINARY_OP(numSub, makeNum(a.as.f64 - b.as.f64))

BINARY_OP(intMul, makeInt(a.as.s32 *b.as.s32))
BINARY_OP(numMul, makeNum(a.as.f64 *b.as.f64))

BINARY_OP(intDiv, makeInt(a.as.s32 / b.as.s32))
BINARY_OP(numDiv, makeNum(a.as.f64 / b.as.f64))

BINARY_OP(strCat, concatStrings(vm, *(StringObject *)a.as.obj->ptr,
                                *(StringObject *)b.as.obj->ptr))

UNARY_OP(not, makeBool(!a.as.b))

BINARY_OP(intLess, makeBool(a.as.s32 < b.as.s32))
BINARY_OP(numLess, makeBool(a.as.f64 < b.as.f64))

BINARY_OP(intGreater, makeBool(a.as.s32 > b.as.s32))
BINARY_OP(numGreater, makeBool(a.as.f64 > b.as.f64))

BINARY_OP(equal, makeBool(valuesEqual(a, b)))

static Result op_jump(VM *vm) {

    TRACE(printf("op_jump\n");)

    READ(offset)

    vm->ip += offset;
    if (vm->ip > vm->end) {

        printf("|| Jumped out of range\n");
        return RESULT_ERR;
    }

    return RESULT_OK;
}

static Result op_jumpIfFalse(VM *vm) {

    TRACE(printf("op_jumpIfFalse\n");)

    READ(offset)
    POP(cond)

    if (!cond.as.b) {

        vm->ip += offset;
        if (vm->ip > vm->end) {

            printf("|| Jumped out of range\n");
            return RESULT_ERR;
        }
    }

    return RESULT_OK;
}

static Result op_loop(VM *vm) {

    TRACE(printf("op_loop\n");)

    READ(offset)

    vm->ip -= offset;
    if (vm->ip < vm->start) {

        printf("|| Looped out of range\n");
        return RESULT_ERR;
    }

    return RESULT_OK;
}

static Result op_function(VM *vm) {

    TRACE(printf("op_function\n");)

    READ(offset)

    uint8_t *ip = vm->ip;
    PUSH(makePointer(ip))
    vm->ip += offset;

    return RESULT_OK;
}

static Result op_call(VM *vm) {

    TRACE(printf("op_call\n");)

    READ(paramCount)

    POP(function)

    Value *params = ALLOCATE_ARRAY(Value, paramCount);

    // TODO: POPN and PUSHN

    for (int i = paramCount - 1; i >= 0; i--) {

        POP(param)

        params[i] = param;
    }

    PUSH(makePointer(vm->ip))
    PUSH(makePointer(vm->fp))

    vm->fp = vm->sp;
    vm->ip = function.as.ptr;

    for (size_t i = 0; i < paramCount; i++) {

        PUSH(params[i])
    }

    FREE_ARRAY(Value, params, paramCount);

    return RESULT_OK;
}

static Result op_load_ip(VM *vm) {

    TRACE(printf("op_load_ip\n");)

    POP(ipValue)

    vm->ip = ipValue.as.ptr;

    return RESULT_OK;
}

static Result op_load_fp(VM *vm) {

    TRACE(printf("op_load_fp\n");)

    POP(fpValue)

    vm->fp = (Value *)fpValue.as.ptr;

    return RESULT_OK;
}

static Result op_setReturn(VM *vm) {

    TRACE(printf("op_setReturn\n");)

    POP(returnValue)
    vm->returnStore = returnValue;

    return RESULT_OK;
}

static Result op_pushReturn(VM *vm) {

    TRACE(printf("op_pushReturn\n");)

    PUSH(vm->returnStore)

    return RESULT_OK;
}

#undef BINARY_OP
#undef UNARY_OP
#undef READ
#undef PEEK
#undef PUSH
#undef POP

Result initVM(VM *vm) {

    vm->start = NULL;
    vm->end = NULL;

    vm->ip = NULL;
    vm->fp = vm->stack;
    vm->sp = vm->stack;

    initGlobalArray(&vm->globals);

    vm->objects = NULL;

    vm->constants = NULL;
    vm->constantCount = 0;

    for (size_t i = 0; i < OP_COUNT; i++) {

        vm->instructions[i] = errorInstruction;
    }

#define INSTR(opcode, instr)                                                   \
    do {                                                                       \
        vm->instructions[opcode] = instr;                                      \
    } while (0)

    INSTR(OP_PUSH_CONST, op_pushConst);
    INSTR(OP_PUSH_TRUE, op_pushTrue);
    INSTR(OP_PUSH_FALSE, op_pushFalse);
    INSTR(OP_PUSH_NIL, op_pushNil);

    INSTR(OP_SET_GLOBAL, op_setGlobal);
    INSTR(OP_PUSH_GLOBAL, op_pushGlobal);
    INSTR(OP_SET_LOCAL, op_setLocal);
    INSTR(OP_PUSH_LOCAL, op_getLocal);

    INSTR(OP_INT, op_int);
    INSTR(OP_BOOL, op_bool);
    INSTR(OP_NUM, op_num);
    INSTR(OP_STR, op_str);
    INSTR(OP_CLOCK, op_clock);

    INSTR(OP_PRINT, op_print);
    INSTR(OP_POP, op_pop);

    INSTR(OP_INT_NEG, op_intNeg);
    INSTR(OP_NUM_NEG, op_numNeg);
    INSTR(OP_INT_ADD, op_intAdd);
    INSTR(OP_NUM_ADD, op_numAdd);
    INSTR(OP_INT_SUB, op_intSub);
    INSTR(OP_NUM_SUB, op_numSub);
    INSTR(OP_INT_MUL, op_intMul);
    INSTR(OP_NUM_MUL, op_numMul);
    INSTR(OP_INT_DIV, op_intDiv);
    INSTR(OP_NUM_DIV, op_numDiv);
    INSTR(OP_STR_CAT, op_strCat);
    INSTR(OP_NOT, op_not);

    INSTR(OP_INT_LESS, op_intLess);
    INSTR(OP_NUM_LESS, op_numLess);
    INSTR(OP_INT_GREATER, op_intGreater);
    INSTR(OP_NUM_GREATER, op_numGreater);
    INSTR(OP_EQUAL, op_equal);

    INSTR(OP_JUMP, op_jump);
    INSTR(OP_JUMP_IF_FALSE, op_jumpIfFalse);
    INSTR(OP_LOOP, op_loop);

    INSTR(OP_FUNCTION, op_function);
    INSTR(OP_CALL, op_call);
    INSTR(OP_LOAD_IP, op_load_ip);
    INSTR(OP_LOAD_FP, op_load_fp);
    INSTR(OP_SET_RETURN, op_setReturn);
    INSTR(OP_PUSH_RETURN, op_pushReturn);

#undef INSTR

    return RESULT_OK;
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

            case CONST_INT: {

                if (index >= length - sizeof(int32_t)) {

                    printf("|| EOF reached while parsing constant integer\n");
                    return RESULT_ERR;
                }

                index++;

                int32_t value = *(int32_t *)(code + index);
                vm->constants[i] = makeInt(value);

                index += sizeof(int32_t);

            } break;

            case CONST_NUM: {

                if (index >= length - sizeof(double)) {

                    printf("|| EOF reached while parsing constant number\n");
                    return RESULT_ERR;
                }

                index++;

                double value = *(double *)(code + index);
                vm->constants[i] = makeNum(value);

                index += sizeof(double);

            } break;

            case CONST_STR: {

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

static Result runVM(VM *vm) {

    while (vm->end - vm->ip > 0) {

        uint8_t opcode = *vm->ip++;

        if (opcode >= OP_COUNT) {

            printf("|| Unknown opcode %d\n", opcode);
            return RESULT_ERR;
        }

        if (vm->instructions[opcode](vm) != RESULT_OK) {

            printf("|| Opcode %d failed\n", opcode);
            return RESULT_ERR;
        }

#ifdef DEBUG_STACK

        printf("\t\t\t");
        for (Value *value = vm->stack; value < vm->sp; value++) {

            printf("[");
            printValue(*value);
            printf("] ");

            if (value == vm->fp - 1) {

                printf(" | ");
            }
        }
        printf("\n");

#endif
    }

    return RESULT_OK;
}

Result executeCode(VM *vm, uint8_t *code, size_t length) {

    size_t index;
    if (loadConstants(vm, code, length, &index) != RESULT_OK) {

        printf("|| Could not load constants\n");
        return RESULT_ERR;
    }

    vm->start = code;
    vm->end = code + length;
    vm->ip = code + index;

    return runVM(vm);
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
}
