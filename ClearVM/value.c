
#include "value.h"

#include "memory.h"
#include "vm.h"

#include <math.h>
#include <stdio.h>
#include <string.h>

Value makeObject(VM *vm, size_t size, ObjectType type) {

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

Value makeString(VM *vm, char *data, size_t length) {

    Value result = makeObject(vm, sizeof(StringObject), OBJ_STRING);

    StringObject *strObj = (StringObject *)result.as.obj->ptr;
    strObj->length = length;
    strObj->data = data;

    return result;
}

Value makeStringFromLiteral(VM *vm, const char *literal) {

    size_t len = strnlen(literal, STR_MAX);
    char *buffer = ALLOCATE_ARRAY(char, len + 1);
    memcpy(buffer, literal, len + 1);

    return makeString(vm, buffer, len);
}

Value makeInt(int32_t unboxed) {

    Value result;

    result.type = VAL_INT;
    result.as.s32 = unboxed;

    return result;
}

Value makeBool(bool unboxed) {

    Value result;

    result.type = VAL_BOOL;
    result.as.b = unboxed;

    return result;
}

Value makeNum(double unboxed) {

    Value result;

    result.type = VAL_NUM;
    result.as.f64 = unboxed;

    return result;
}

Result stringifyValue(VM *vm, Value input, Value *output) {

    switch (input.type) {

        case VAL_BOOL: {

            if (input.as.b) {

                *output = makeStringFromLiteral(vm, "true");

            } else {

                *output = makeStringFromLiteral(vm, "false");
            }

        } break;

        case VAL_INT: {

            size_t digits = 0;
            int32_t i = input.as.s32;

            do {

                i /= 10;
                digits++;

            } while (i != 0);

            size_t length = input.as.s32 < 0 ? 1 + digits : digits;

            char *buffer = ALLOCATE_ARRAY(char, length + 1);
            buffer[length] = '\0';

            snprintf(buffer, length + 1, "%d", input.as.s32);

            *output = makeString(vm, buffer, length);

        } break;

        case VAL_NIL: {

            *output = makeStringFromLiteral(vm, "nil");

        } break;

        case VAL_NUM: {

            double num = input.as.f64;

            size_t signLength = num < 0 ? 1 : 0;
            double size = num < 0 ? -num : num;
            size_t preDecimalDigits = size < 1.0 ? 1 : 1 + (size_t)log10(size);

            size_t length = signLength + preDecimalDigits + 1 + NUM_PLACES;

            char *buffer = ALLOCATE_ARRAY(char, length + 1);
            buffer[length] = '\0';

            snprintf(buffer, length + 1, "%.*f", NUM_PLACES, num);

            *output = makeString(vm, buffer, length);

        } break;

        case VAL_OBJ: {

            printf("|| Cannot cast object types\n");
            return RESULT_ERR;

        } break;

        default: {

            printf("|| Unknown input type %d\n", input.type);
            return RESULT_ERR;

        } break;
    }

    return RESULT_OK;
}

Value concatStrings(VM *vm, StringObject a, StringObject b) {

    size_t newLength = a.length + b.length;

    char *data = ALLOCATE_ARRAY(char, newLength + 1);
    data[newLength] = '\0';

    memcpy(data, a.data, a.length);
    memcpy(data + a.length, b.data, b.length);

    return makeString(vm, data, newLength);
}

bool valuesEqual(Value a, Value b) {

    if (a.type != b.type) {

        return false;
    }

    switch (a.type) {

        case VAL_BOOL: {

            return a.as.b == b.as.b;

        } break;

        case VAL_INT: {

            return a.as.s32 == b.as.s32;

        } break;

        case VAL_NIL: {

            return true;

        } break;

        case VAL_NUM: {

            if (a.as.f64 > b.as.f64) {

                return a.as.f64 - b.as.f64 < NUM_PRECISION;

            } else {

                return b.as.f64 - a.as.f64 < NUM_PRECISION;
            }

        } break;

        case VAL_OBJ: {

            ObjectValue aObj = *a.as.obj;
            ObjectValue bObj = *b.as.obj;

            if (aObj.type != bObj.type) {

                return false;
            }

            switch (aObj.type) {

                case OBJ_STRING: {

                    StringObject aStr = *(StringObject *)aObj.ptr;
                    StringObject bStr = *(StringObject *)bObj.ptr;

                    return aStr.length == bStr.length &&
                           memcmp(aStr.data, bStr.data, aStr.length) == 0;

                } break;

                default:
                    return false;
            }

        } break;

        default:
            return false;
    }
}

// TODO: Make this consistent with OP_PRINT
void printValue(Value value) {

    switch (value.type) {

        case VAL_BOOL: {

            printf(value.as.b ? "true" : "false");

        } break;

        case VAL_INT: {

            printf("%d", value.as.s32);

        } break;

        case VAL_NIL: {

            printf("nil");

        } break;

        case VAL_NUM: {

            printf("%f", value.as.f64);

        } break;

        case VAL_OBJ: {

            ObjectValue obj = *value.as.obj;

            switch (obj.type) {

                case OBJ_STRING: {

                    StringObject strObj = *(StringObject *)obj.ptr;
                    printf("%s", strObj.data);

                } break;
            }

        } break;
    }
}

void initValueList(ValueList *list) {

    list->data = NULL;
    list->count = 0;
    list->capacity = 0;
}

void growValueList(ValueList *list) {

    size_t oldCapacity = list->capacity;
    list->capacity = GROW_CAPACITY(oldCapacity);
    list->data = GROW_ARRAY(list->data, Value, oldCapacity, list->capacity);
}

void appendValueList(ValueList *list, Value value) {

    if (list->capacity < list->count + 1) {

        growValueList(list);
    }

    list->data[list->count++] = value;
}

Result getValueList(ValueList *list, size_t index, Value *out) {

    if (index >= list->count) {

        return RESULT_ERR;
    }

    if (out != NULL) {

        *out = list->data[index];
    }

    return RESULT_OK;
}

Result setValueList(ValueList *list, size_t index, Value value) {

    if (index >= list->count) {

        return RESULT_ERR;
    }

    list->data[index] = value;

    return RESULT_OK;
}

void freeValueList(ValueList *list) {

    FREE_ARRAY(Value, list->data, list->capacity);
}
