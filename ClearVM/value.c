
#include "value.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "memory.h"
#include "obj.h"

Value makeBoolean(bool boolean) {

    Value result;

    result.type = VAL_BOOL;
    result.as.boolean = boolean;

    return result;
}

Value makeNumber(double number) {

    Value result;

    result.type = VAL_NUMBER;
    result.as.number = number;

    return result;
}

Value makeString(size_t length, char *string) {

    Value result;

    ObjString *stringObj = (ObjString*) malloc(sizeof(ObjString));

    result.type = VAL_OBJ;
    result.as.obj = (Obj*) stringObj;
    result.as.obj->type = OBJ_STRING;

    stringObj->chars = string;
    stringObj->length = length;

    return result;
}

bool valuesEqual(Value a, Value b) {

    if (a.type != b.type) return false;

    switch (a.type) {
    
        case VAL_BOOL:

            return a.as.boolean == b.as.boolean;

        case VAL_NUMBER:

            return a.as.number == b.as.number;

        case VAL_OBJ: {

            if (a.as.obj->type != b.as.obj->type) return false;

            switch (a.as.obj->type) {
            
                case OBJ_STRING: {
            
                    ObjString *aStr = (ObjString*) a.as.obj;
                    ObjString *bStr = (ObjString*) b.as.obj;

                    return stringsEqual(aStr, bStr);
            
                } break;
            }

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
        array->values = GROW_ARRAY(array->values, Value, oldCapacity,
                array->capacity);
    }

    array->values[array->count++] = value;
}

void freeValueArray(ValueArray *array) {

    for (size_t i = 0; i < array->count; i++) {

        Value value = array->values[i];

        if (value.type == VAL_OBJ) {

            switch (value.as.obj->type) {
            
                case OBJ_STRING: {
            
                    ObjString *strObj = (ObjString*) value.as.obj;
                    free(strObj->chars);
                    free(strObj);
            
                } break;
            }
        }
    }

    FREE_ARRAY(Value, array->values, array->capacity);
    initValueArray(array);
}

void printValue(Value value, bool endLine) {

    switch (value.type) {

        case VAL_NUMBER: {

            printf("<num %g>", value.as.number);

        } break;

        case VAL_BOOL: {

            printf("<bool %s>", value.as.boolean ? "true" : "false");

        } break;

        case VAL_OBJ: {
        
            switch (value.as.obj->type) {
            
                case OBJ_STRING: {
            
                    ObjString *strObj = (ObjString*) value.as.obj;
                    printf("<str \"%s\">", strObj->chars);
            
                } break;
            }
        
        } break;
    }

    if (endLine) printf("\n");
}

