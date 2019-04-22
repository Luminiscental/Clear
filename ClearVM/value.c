
#include "value.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "memory.h"
#include "obj.h"

Value makeNil() {

    Value result = {};

    result.type = VAL_NIL;

    return result;
}

Value makeInteger(int32_t integer) {

    Value result = {};

    result.type = VAL_INTEGER;
    result.hash = integer;
    result.as.integer = integer;

    return result;
}

Value makeBoolean(bool boolean) {

    Value result = {};

    result.type = VAL_BOOL;
    result.hash = boolean ? 1 : 0;
    result.as.boolean = boolean;

    return result;
}

Value makeNumber(double number) {

    Value result = {};

    result.type = VAL_NUMBER;
    result.hash = *((uint32_t *)&number);
    result.as.number = number;

    return result;
}

bool valuesEqual(Value a, Value b) {

    if (a.type != b.type)
        return false;
    if (a.hash != b.hash)
        return false;

    switch (a.type) {

        case VAL_NIL: {

            return true; // all nil values are equal

        } break;

        case VAL_INTEGER: {

            return a.as.integer == b.as.integer;

        } break;

        case VAL_BOOL: {

            return a.as.boolean == b.as.boolean;

        } break;

        case VAL_NUMBER: {

            double diff = a.as.number - b.as.number;
            if (diff < 0)
                diff = -diff;
            return diff < NUMBER_PRECISION;

        } break;

        case VAL_OBJ: {

            if (a.as.obj->type != b.as.obj->type)
                return false;

            // Objects are compared by identity.
            // Because strings are interned this means strings are compared by
            // value.
            // TODO: Compare structs deeply?
            return a.as.obj == b.as.obj;

        } break;
    }
}

void initValueArray(ValueArray *array) {

    array->values = NULL;
    array->capacity = 0;
    array->count = 0;
}

void writeValueArray(ValueArray *array, Value value) {

    if (array->capacity < array->count + 1) {

        int oldCapacity = array->capacity;
        array->capacity = GROW_CAPACITY(oldCapacity);
        array->values =
            GROW_ARRAY(array->values, Value, oldCapacity, array->capacity);
    }

    array->values[array->count++] = value;
}

void freeValueArray(ValueArray *array) {

    FREE_ARRAY(Value, array->values, array->capacity);
    initValueArray(array);
}

void printValue(Value value, bool endLine) {

    switch (value.type) {

        case VAL_NIL: {

            printf("nil");

        } break;

        case VAL_INTEGER: {

            printf("%d", value.as.integer);

        } break;

        case VAL_NUMBER: {

            size_t length;
            char *rawString = makeRawStringFromNumber(value.as.number, &length);
            printf("%s", rawString);
            FREE_ARRAY(char, rawString, length + 1);

        } break;

        case VAL_BOOL: {

            printf("%s", value.as.boolean ? "true" : "false");

        } break;

        case VAL_OBJ: {

            switch (value.as.obj->type) {

                case OBJ_STRING: {

                    ObjString *strObj = (ObjString *)value.as.obj;
                    printf("%s", strObj->chars);

                } break;

                case OBJ_FUNCTION: {

                    // fp: function prototype
                    printf("<fp %p>", value.as.obj);

                } break;

                case OBJ_CLOSURE: {

                    // fn: function
                    printf("<fn %p>", value.as.obj);

                } break;

                case OBJ_UPVALUE: {

                    ObjUpvalue *upvalue = (ObjUpvalue *)value.as.obj;
                    printValue(*upvalue->value, false);

                } break;

                case OBJ_STRUCT: {

                    // TODO: Maybe pretty print these?
                    // st: struct
                    printf("<st %p> - ", value.as.obj);

                    ObjStruct *structObj = (ObjStruct *)value.as.obj;

                    for (size_t i = 0; i < structObj->fieldCount; i++) {

                        printf("[ ");
                        printValue(structObj->fields[i], false);
                        printf(" ]");
                    }

                } break;
            }

        } break;
    }

    if (endLine)
        printf("\n");
}
