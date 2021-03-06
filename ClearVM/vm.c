
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

#define POPN(arr, n)                                                           \
    if (vm->sp - vm->stack <= (n)-1) {                                         \
                                                                               \
        printf("|| Stack underflow\n");                                        \
        return RESULT_ERR;                                                     \
    }                                                                          \
    vm->sp -= (n);                                                             \
    if (arr) {                                                                 \
                                                                               \
        memcpy((arr), vm->sp, (n) * sizeof(Value));                            \
    }

#define PUSH(name)                                                             \
    if (vm->sp - vm->stack == STACK_MAX) {                                     \
                                                                               \
        printf("|| Stack overflow\n");                                         \
        return RESULT_ERR;                                                     \
    }                                                                          \
    *vm->sp++ = name;

#define PUSHN(arr, n)                                                          \
    if (vm->sp - vm->stack >= (long)(STACK_MAX + (n)-1)) {                     \
                                                                               \
        printf("|| Stack overflow\n");                                         \
        return RESULT_ERR;                                                     \
    }                                                                          \
    memcpy(vm->sp, (arr), (n) * sizeof(Value));                                \
    vm->sp += n;

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

static void traceOpcode(VM *vm, const char *name, bool endLine) {

#ifdef DEBUG_TRACE

    size_t offset = vm->ip - vm->start;
    printf("%04zu %-18s", offset, name);

    if (endLine) {

        printf("\n");

    } else {

        printf(" ");
    }

#else

    UNUSED(vm);
    UNUSED(name);
    UNUSED(endLine);

#endif
}

static void traceU8(uint8_t value, bool endLine) {

#ifdef DEBUG_TRACE

    printf("%d", value);

    if (endLine) {

        printf("\n");

    } else {

        printf(" ");
    }

#else

    UNUSED(value);
    UNUSED(endLine);

#endif
}

#define UNARY_OP(name, op)                                                     \
    static Result op_##name(VM *vm) {                                          \
        traceOpcode(vm, "OP_" #name, true);                                    \
        PEEK(value, 0)                                                         \
        Value a = *value;                                                      \
        *value = op;                                                           \
        return RESULT_OK;                                                      \
    }

#define BINARY_OP(name, op)                                                    \
    static Result op_##name(VM *vm) {                                          \
        traceOpcode(vm, "OP_" #name, true);                                    \
        POP(second)                                                            \
        PEEK(first, 0)                                                         \
        Value a = *first;                                                      \
        Value b = second;                                                      \
        *first = op;                                                           \
        return RESULT_OK;                                                      \
    }

static Result op_pushConst(VM *vm) {

    READ(index)

    traceOpcode(vm, "OP_PUSH_CONST", false);
    traceU8(index, true);

    if (index >= vm->constantCount) {

        printf("|| Constant index %d out of range\n", index);
        return RESULT_ERR;
    }

    PUSH(vm->constants[index])

    return RESULT_OK;
}

static Result op_pushTrue(VM *vm) {

    traceOpcode(vm, "OP_PUSH_TRUE", true);

    PUSH(makeBool(true))

    return RESULT_OK;
}

static Result op_pushFalse(VM *vm) {

    traceOpcode(vm, "OP_PUSH_FALSE", true);

    PUSH(makeBool(false))

    return RESULT_OK;
}

static Result op_pushNil(VM *vm) {

    traceOpcode(vm, "OP_PUSH_NIL", true);

    PUSH(makeNil());

    return RESULT_OK;
}

static Result op_setGlobal(VM *vm) {

    READ(index)

    traceOpcode(vm, "OP_SET_GLOBAL", false);
    traceU8(index, true);

    POP(value)

    if (setGlobal(&vm->globals, index, value) != RESULT_OK) {

        printf("|| Invalid global index %d\n", index);
        return RESULT_ERR;
    }

    return RESULT_OK;
}

static Result op_pushGlobal(VM *vm) {

    READ(index)

    traceOpcode(vm, "OP_PUSH_GLOBAL", false);
    traceU8(index, true);

    Value global;
    if (getGlobal(&vm->globals, index, &global) != RESULT_OK) {

        printf("|| Undefined global %d\n", index);
        return RESULT_ERR;
    }

    PUSH(global)

    return RESULT_OK;
}

static Result op_setLocal(VM *vm) {

    READ(index)

    traceOpcode(vm, "OP_SET_LOCAL", false);
    traceU8(index, true);

    POP(value)

    if (index >= vm->sp - vm->fp) {

        printf("|| Local %d out of range\n", index);
        return RESULT_ERR;
    }

    value.references = vm->fp[index].references;
    vm->fp[index] = value;

    return RESULT_OK;
}

static Result op_pushLocal(VM *vm) {

    READ(index)

    traceOpcode(vm, "OP_PUSH_LOCAL", false);
    traceU8(index, true);

    if (index >= vm->sp - vm->fp) {

        printf("|| Local %d out of range\n", index);
        return RESULT_ERR;
    }

    PUSH(vm->fp[index])

    return RESULT_OK;
}

static Result op_int(VM *vm) {

    traceOpcode(vm, "OP_INT", true);

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

        case VAL_IP:
        case VAL_FP:
        case VAL_OBJ: {

            printf("|| Cannot cast pointer types\n");
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

    traceOpcode(vm, "OP_BOOL", true);

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

            double x = value->as.f64;

            if (x > 0.0) {

                *value = makeBool(x < NUM_PRECISION);

            } else {

                *value = makeBool(-x < NUM_PRECISION);
            }

        } break;

        case VAL_IP:
        case VAL_FP:
        case VAL_OBJ: {

            printf("|| Cannot cast pointer types\n");
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

    traceOpcode(vm, "OP_NUM", true);

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

        case VAL_IP:
        case VAL_FP:
        case VAL_OBJ: {

            printf("|| Cannot cast pointer types\n");
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

    traceOpcode(vm, "OP_STR", true);

    PEEK(value, 0)

    return stringifyValue(vm, *value, value);
}

static Result op_clock(VM *vm) {

    traceOpcode(vm, "OP_CLOCK", true);

    PUSH(makeNum((double)clock() / CLOCKS_PER_SEC))

    return RESULT_OK;
}

static Result op_print(VM *vm) {

    traceOpcode(vm, "OP_PRINT", true);

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

    traceOpcode(vm, "OP_POP", true);

    POP(value)

    while (value.references != NULL) {

        closeUpvalue(value.references);
        value.references = value.references->next;
    }

    return RESULT_OK;
}

static Result op_squash(VM *vm) {

    traceOpcode(vm, "OP_SQUASH", true);

    POP(value)

    PEEK(replaced, 0)

    *replaced = value;

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

static Result op_strCat(VM *vm) {

    traceOpcode(vm, "OP_STR_CAT", true);

    POP(b)

    PEEK(a, 0)

    if (b.type != VAL_OBJ || b.as.obj->type != OBJ_STRING) {

        printf("|| Cannot concatenate non-string values\n");
        return RESULT_ERR;
    }

    if (a->type != VAL_OBJ || a->as.obj->type != OBJ_STRING) {

        printf("|| Cannot concatenate non-string values\n");
        return RESULT_ERR;
    }

    *a = concatStrings(vm, *(StringObject *)a->as.obj->ptr,
                       *(StringObject *)b.as.obj->ptr);

    return RESULT_OK;
}

UNARY_OP(not, makeBool(!a.as.b))

BINARY_OP(intLess, makeBool(a.as.s32 < b.as.s32))
BINARY_OP(numLess, makeBool(a.as.f64 < b.as.f64 - NUM_PRECISION))

BINARY_OP(intGreater, makeBool(a.as.s32 > b.as.s32))
BINARY_OP(numGreater, makeBool(a.as.f64 > b.as.f64 + NUM_PRECISION))

BINARY_OP(equal, makeBool(valuesEqual(a, b)))

static Result op_jump(VM *vm) {

    READ(offset)

    traceOpcode(vm, "OP_JUMP", false);
    traceU8(offset, true);

    vm->ip += offset;
    if (vm->ip > vm->end) {

        printf("|| Jumped out of range\n");
        return RESULT_ERR;
    }

    return RESULT_OK;
}

static Result op_jumpIfFalse(VM *vm) {

    READ(offset)

    traceOpcode(vm, "OP_JUMP_IF_FALSE", false);
    traceU8(offset, true);

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

    READ(offset)

    traceOpcode(vm, "OP_LOOP", false);
    traceU8(offset, true);

    vm->ip -= offset;
    if (vm->ip < vm->start) {

        printf("|| Looped out of range\n");
        return RESULT_ERR;
    }

    return RESULT_OK;
}

static Result op_function(VM *vm) {

    READ(offset)

    traceOpcode(vm, "OP_FUNCTION", false);
    traceU8(offset, true);

    uint8_t *ip = vm->ip;
    PUSH(makeIP(ip))
    vm->ip += offset;

    return RESULT_OK;
}

static Result op_call(VM *vm) {

    READ(paramCount)

    traceOpcode(vm, "OP_CALL", false);
    traceU8(paramCount, true);

    POP(function)

    if (function.type != VAL_IP) {

        printf("|| Cannot call to a non-ip value\n");
        return RESULT_ERR;
    }

    Value *params = ALLOCATE_ARRAY(Value, paramCount);

#define POPN_(arr, n)                                                          \
    if (vm->sp - vm->stack <= (n)-1) {                                         \
                                                                               \
        printf("|| Stack underflow\n");                                        \
        FREE_ARRAY(Value, params, paramCount);                                 \
        return RESULT_ERR;                                                     \
    }                                                                          \
    vm->sp -= (n);                                                             \
    if (arr) {                                                                 \
                                                                               \
        memcpy((arr), vm->sp, (n) * sizeof(Value));                            \
    }

#define PUSH_(name)                                                            \
    if (vm->sp - vm->stack == STACK_MAX) {                                     \
                                                                               \
        printf("|| Stack overflow\n");                                         \
        FREE_ARRAY(Value, params, paramCount);                                 \
        return RESULT_ERR;                                                     \
    }                                                                          \
    *vm->sp++ = name;

#define PUSHN_(arr, n)                                                         \
    if (vm->sp - vm->stack >= (long)(STACK_MAX + (n)-1)) {                     \
                                                                               \
        printf("|| Stack overflow\n");                                         \
        FREE_ARRAY(Value, params, paramCount);                                 \
        return RESULT_ERR;                                                     \
    }                                                                          \
    memcpy(vm->sp, (arr), (n) * sizeof(Value));                                \
    vm->sp += n;

    POPN_(params, paramCount)

    PUSH_(makeIP(vm->ip))
    PUSH_(makeFP(vm->fp))

    vm->fp = vm->sp;
    vm->ip = function.as.ptr;

    PUSHN_(params, paramCount)

#undef PUSHN_
#undef PUSH_
#undef POPN_

    FREE_ARRAY(Value, params, paramCount);

    return RESULT_OK;
}

static Result op_loadIp(VM *vm) {

    traceOpcode(vm, "OP_LOAD_IP", true);

    POP(ipValue)

    if (ipValue.type != VAL_IP) {

        printf("|| Cannot load non-code pointer to ip\n");
        return RESULT_ERR;
    }

    vm->ip = ipValue.as.ptr;

    return RESULT_OK;
}

static Result op_loadFp(VM *vm) {

    traceOpcode(vm, "OP_LOAD_FP", true);

    POP(fpValue)

    if (fpValue.type != VAL_FP) {

        printf("|| Cannot load non-value pointer to fp\n");
        return RESULT_ERR;
    }

    vm->fp = (Value *)fpValue.as.ptr;

    return RESULT_OK;
}

static Result op_setReturn(VM *vm) {

    traceOpcode(vm, "OP_SET_RETURN", true);

    POP(returnValue)
    vm->returnStore = returnValue;

    return RESULT_OK;
}

static Result op_pushReturn(VM *vm) {

    traceOpcode(vm, "OP_PUSH_RETURN", true);

    PUSH(vm->returnStore)

    return RESULT_OK;
}

static Result op_struct(VM *vm) {

    READ(fieldCount)

    traceOpcode(vm, "OP_STRUCT", false);
    traceU8(fieldCount, true);

    Value result = makeStruct(vm, fieldCount);
    StructObject *structObj = (StructObject *)result.as.obj->ptr;

    POPN(structObj->fields, fieldCount)

    PUSH(result)

    return RESULT_OK;
}

static Result op_destruct(VM *vm) {

    READ(dropCount)

    traceOpcode(vm, "OP_DESTRUCT", false);
    traceU8(dropCount, true);

    POP(structValue)

    if (structValue.type != VAL_OBJ || structValue.as.obj->type != OBJ_STRUCT) {

        printf("|| Popped value isn't a struct\n");
        return RESULT_ERR;
    }

    StructObject *structObj = (StructObject *)structValue.as.obj->ptr;

    PUSHN(structObj->fields + dropCount, structObj->fieldCount - dropCount)

    return RESULT_OK;
}

static Result op_getField(VM *vm) {

    READ(index)

    traceOpcode(vm, "OP_GET_FIELD", false);
    traceU8(index, true);

    POP(structValue)

    if (structValue.type != VAL_OBJ || structValue.as.obj->type != OBJ_STRUCT) {

        printf("|| Cannot get field from non-struct value\n");
        return RESULT_ERR;
    }

    StructObject *structObj = (StructObject *)structValue.as.obj->ptr;

    if (index >= structObj->fieldCount) {

        printf("|| Field %d is out of range\n", index);
        return RESULT_ERR;
    }

    PUSH(structObj->fields[index])

    return RESULT_OK;
}

static Result op_extractField(VM *vm) {

    READ(offset)
    READ(index)

    traceOpcode(vm, "OP_EXTRACT_FIELD", false);
    traceU8(offset, false);
    traceU8(index, true);

    PEEK(structValue, offset)

    if (structValue->type != VAL_OBJ ||
        structValue->as.obj->type != OBJ_STRUCT) {

        printf("|| Cannot get field from non-struct value\n");
        return RESULT_ERR;
    }

    StructObject *structObj = (StructObject *)structValue->as.obj->ptr;

    if (index >= structObj->fieldCount) {

        printf("|| Field %d is out of range\n", index);
        return RESULT_ERR;
    }

    PUSH(structObj->fields[index])

    return RESULT_OK;
}

static Result op_setField(VM *vm) {

    READ(index)

    traceOpcode(vm, "OP_SET_FIELD", false);
    traceU8(index, true);

    POP(field)

    PEEK(structValue, 0)

    if (structValue->type != VAL_OBJ ||
        structValue->as.obj->type != OBJ_STRUCT) {

        printf("|| Cannot set field on non-struct value\n");
        return RESULT_ERR;
    }

    StructObject *structObj = (StructObject *)structValue->as.obj->ptr;

    if (index >= structObj->fieldCount) {

        printf("|| Field %d out of range\n", index);
        return RESULT_ERR;
    }

    structObj->fields[index] = field;

    return RESULT_OK;
}

static Result op_insertField(VM *vm) {

    READ(offset)
    READ(index)

    traceOpcode(vm, "OP_INSERT_FIELD", false);
    traceU8(offset, false);
    traceU8(index, true);

    POP(fieldValue)
    PEEK(structValue, offset)

    if (structValue->type != VAL_OBJ ||
        structValue->as.obj->type != OBJ_STRUCT) {

        printf("|| Cannot set field into non-struct value\n");
        return RESULT_ERR;
    }

    StructObject *structObj = (StructObject *)structValue->as.obj->ptr;

    if (index >= structObj->fieldCount) {

        printf("|| Field %d is out of range\n", index);
        return RESULT_ERR;
    }

    structObj->fields[index] = fieldValue;

    return RESULT_OK;
}

static Result op_refLocal(VM *vm) {

    READ(index)

    traceOpcode(vm, "OP_REF_LOCAL", false);
    traceU8(index, true);

    if (index >= vm->sp - vm->fp) {

        printf("|| Local %d out of range\n", index);
        return RESULT_ERR;
    }

    Value result = makeUpvalue(vm, vm->fp + index);

    PUSH(result)

    return RESULT_OK;
}

static Result op_deref(VM *vm) {

    traceOpcode(vm, "OP_DEREF", true);

    PEEK(upvalue, 0)

    if (upvalue->type != VAL_OBJ || upvalue->as.obj->type != OBJ_UPVALUE) {

        printf("|| Cannot dereference non-upvalue\n");
        return RESULT_ERR;
    }

    UpvalueObject *upvalueObj = (UpvalueObject *)upvalue->as.obj->ptr;
    *upvalue = *upvalueObj->ptr;

    return RESULT_OK;
}

static Result op_setRef(VM *vm) {

    traceOpcode(vm, "OP_SET_REF", true);

    POP(upvalue)
    POP(value)

    if (upvalue.type != VAL_OBJ || upvalue.as.obj->type != OBJ_UPVALUE) {

        printf("|| Cannot dereference non-upvalue\n");
        return RESULT_ERR;
    }

    UpvalueObject *upvalueObj = (UpvalueObject *)upvalue.as.obj->ptr;
    *upvalueObj->ptr = value;

    return RESULT_OK;
}

static Result op_isValType(VM *vm) {

    READ(val_type)

    traceOpcode(vm, "OP_IS_VAL_TYPE", false);
    traceU8(val_type, true);

    PEEK(value, 0)

    PUSH(makeBool(value->type == val_type))

    return RESULT_OK;
}

static Result op_isObjType(VM *vm) {

    READ(obj_type)

    traceOpcode(vm, "OP_IS_OBJ_TYPE", false);
    traceU8(obj_type, true);

    PEEK(value, 0)

    PUSH(makeBool(value->as.obj->type == obj_type))

    return RESULT_OK;
}

#undef BINARY_OP
#undef UNARY_OP
#undef READ
#undef PEEK
#undef PUSHN
#undef PUSH
#undef POPN
#undef POP

Result initVM(VM *vm) {

    vm->returnStore.type = VAL_NIL;

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
    INSTR(OP_PUSH_LOCAL, op_pushLocal);

    INSTR(OP_INT, op_int);
    INSTR(OP_BOOL, op_bool);
    INSTR(OP_NUM, op_num);
    INSTR(OP_STR, op_str);
    INSTR(OP_CLOCK, op_clock);
    INSTR(OP_PRINT, op_print);

    INSTR(OP_POP, op_pop);
    INSTR(OP_SQUASH, op_squash);

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
    INSTR(OP_LOAD_IP, op_loadIp);
    INSTR(OP_LOAD_FP, op_loadFp);
    INSTR(OP_SET_RETURN, op_setReturn);
    INSTR(OP_PUSH_RETURN, op_pushReturn);

    INSTR(OP_STRUCT, op_struct);
    INSTR(OP_DESTRUCT, op_destruct);
    INSTR(OP_GET_FIELD, op_getField);
    INSTR(OP_EXTRACT_FIELD, op_extractField);
    INSTR(OP_SET_FIELD, op_setField);
    INSTR(OP_INSERT_FIELD, op_insertField);

    INSTR(OP_REF_LOCAL, op_refLocal);
    INSTR(OP_DEREF, op_deref);
    INSTR(OP_SET_REF, op_setRef);

    INSTR(OP_IS_VAL_TYPE, op_isValType);
    INSTR(OP_IS_OBJ_TYPE, op_isObjType);

#undef INSTR

    return RESULT_OK;
}

static Result loadConstants(VM *vm, uint8_t *code, size_t length,
                            size_t *outIndex) {

    size_t index = 0;

    size_t constantCount = *(uint8_t *)code;
    index = index + sizeof(uint8_t);

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

        printf("\n    ");
        for (Value *value = vm->fp; value < vm->sp; value++) {

            printf("[");
            printValue(*value);
            printf("] ");
        }
        printf("\n\n");

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
