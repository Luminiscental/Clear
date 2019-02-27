
#include "value.h"

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "memory.h"
#include "obj.h"

Value makeBoolean(bool boolean) {

    Value result;

    result.type = VAL_BOOL;
    result.hash = boolean ? 1 : 0;
    result.as.boolean = boolean;

    return result;
}

Value makeNumber(double number) {

    Value result;

    result.type = VAL_NUMBER;
    // TODO: Split into int / float so stuff like 1 + 1 == 2 isn't unreliable
    result.hash = *((uint32_t*) &number);
    result.as.number = number;

    return result;
}

bool valuesEqual(Value a, Value b) {

    if (a.type != b.type) return false;
    if (a.hash != b.hash) return false;

    switch (a.type) {
    
        case VAL_BOOL:

            return a.as.boolean == b.as.boolean;

        case VAL_NUMBER:

            return a.as.number == b.as.number;

        case VAL_OBJ: {

            if (a.as.obj->type != b.as.obj->type) return false;

            switch (a.as.obj->type) {
            
                case OBJ_STRING: {
            
                    return a.as.obj == b.as.obj;
            
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

