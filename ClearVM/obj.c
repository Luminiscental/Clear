
#include "obj.h"

#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "memory.h"
#include "table.h"
#include "vm.h"

#define ALLOCATE_OBJ(vm, type, objType)                                        \
    (type *)allocateObject(vm, sizeof(type), objType)

static Obj *allocateObject(VM *vm, size_t size, ObjType type) {

    Obj *obj = (Obj *)reallocate(NULL, 0, size);

    obj->type = type;
    obj->next = vm->objects;
    vm->objects = obj;

    return obj;
}

static ObjString *allocateString(VM *vm, size_t length, char *string) {

    ObjString *objStr = ALLOCATE_OBJ(vm, ObjString, OBJ_STRING);

    objStr->chars = string;
    objStr->length = length;

    return objStr;
}

static uint32_t hashChars(size_t length, const char *chars) {

    uint32_t hash = 2166136261u;

    for (size_t i = 0; i < length; i++) {

        hash ^= chars[i];
        hash *= 16777619;
    }

    return hash;
}

static Entry *tableFindString(Table *table, const char *string, size_t length) {

    if (table->entries == NULL)
        return NULL;

    uint32_t hash = hashChars(length, string);
    uint32_t index = hash % table->capacity;

    while (true) {

        Entry *entry = table->entries + index;

        if (entry->state == ENTRY_EMPTY) {

            return NULL;

        } else if (entry->state == ENTRY_FULL) {

            ObjString *entryStr = (ObjString *)entry->key.as.obj;

            if (entryStr->length == length && entry->key.hash == hash &&
                memcmp(entryStr->chars, string, length) == 0) {

                return entry;
            }
        }

        index = (index + 1) % table->capacity;
    }
}

Value makeStringFromLiteral(VM *vm, const char *string) {

    size_t length = strlen(string);
    Entry *interned = tableFindString(&vm->strings, string, length);

    if (interned != NULL) {

        return interned->key;
    }

    Value result = {};

    char *copyStr = ALLOCATE_ARRAY(char, length + 1);
    strcpy(copyStr, string);

    ObjString *stringObj = allocateString(vm, length, copyStr);

    result.type = VAL_OBJ;
    result.hash = hashChars(length, string);

    result.as.obj = (Obj *)stringObj;

    stringObj->chars = copyStr;
    stringObj->length = length;

    tableSet(&vm->strings, result, makeBoolean(true));

    return result;
}

static size_t countDigits(int32_t integer) {

    size_t digits = 0;

    do {

        integer /= 10;
        digits++;

    } while (integer != 0);

    return digits;
}

Value makeStringFromInteger(VM *vm, int32_t integer) {

    size_t minusSignLength = (integer < 0) ? 1 : 0;
    size_t digits = countDigits(integer);
    size_t length = minusSignLength + digits;

    char *buffer = ALLOCATE_ARRAY(char, length + 1);
    buffer[length] = '\0';

    snprintf(buffer, length + 1, "%d", integer);

    return makeString(vm, length, buffer);
}

char *makeRawStringFromNumber(double number, size_t *lengthOut) {

    size_t minusSignLength = (number < 0) ? 1 : 0;

    double size = (number < 0) ? -number : number;
    size_t preDecimalDigits = size < 1.0 ? 1 : 1 + (size_t)log10(size);
    size_t length = minusSignLength + preDecimalDigits + 1 + NUMBER_PLACES;

    char *buffer = ALLOCATE_ARRAY(char, length + 1);
    buffer[length] = '\0';

    snprintf(buffer, length + 1, "%.*f", NUMBER_PLACES, number);

    if (lengthOut != NULL) {

        *lengthOut = length;
    }

    return buffer;
}

Value makeStringFromNumber(VM *vm, double number) {

    size_t length;
    char *buffer = makeRawStringFromNumber(number, &length);

    return makeString(vm, length, buffer);
}

Value makeString(VM *vm, size_t length, char *string) {

    Entry *interned = tableFindString(&vm->strings, string, length);

    if (interned != NULL) {

        FREE_ARRAY(char, string, length + 1);
        return interned->key;
    }

    Value result = {};

    ObjString *stringObj = allocateString(vm, length, string);

    result.type = VAL_OBJ;
    result.hash = hashChars(length, string);

    result.as.obj = (Obj *)stringObj;

    stringObj->chars = string;
    stringObj->length = length;

    tableSet(&vm->strings, result, makeBoolean(true));

    return result;
}

Value concatStrings(VM *vm, ObjString *first, ObjString *second) {

    size_t newLength = first->length + second->length;

    char *result = ALLOCATE_ARRAY(char, newLength + 1);
    result[newLength] = '\0';

    memcpy(result, first->chars, first->length);
    memcpy(result + first->length, second->chars, second->length);

    return makeString(vm, newLength, result);
}

Value makeFunction(VM *vm, uint8_t *code, size_t size) {

    ObjFunction *objFunc = ALLOCATE_OBJ(vm, ObjFunction, OBJ_FUNCTION);

    objFunc->code = code;
    objFunc->size = size;
    objFunc->ip = code;

    Value result = {};

    result.type = VAL_OBJ;
    result.hash = (size_t)objFunc;
    result.as.obj = (Obj *)objFunc;

    return result;
}

Value makeUpvalue(VM *vm, Value *slot) {

    ObjUpvalue *upvalue = ALLOCATE_OBJ(vm, ObjUpvalue, OBJ_UPVALUE);

    upvalue->next = slot->references;
    upvalue->value = slot;

    slot->references = upvalue;

    Value result = {};

    result.type = VAL_OBJ;
    result.hash = (size_t)upvalue;
    result.as.obj = (Obj *)upvalue;

    return result;
}

ObjUpvalue *makeClosedUpvalue(VM *vm, Value value) {

    ObjUpvalue *upvalue = ALLOCATE_OBJ(vm, ObjUpvalue, OBJ_UPVALUE);

    upvalue->closedValue = value;
    upvalue->value = &upvalue->closedValue;
    upvalue->next = NULL;

    return upvalue;
}

Value makeClosure(VM *vm, ObjFunction *function, size_t upvalueCount) {

    ObjClosure *closure = ALLOCATE_OBJ(vm, ObjClosure, OBJ_CLOSURE);

    closure->function = function;
    closure->upvalueCount = upvalueCount;
    closure->upvalues = ALLOCATE_ARRAY(ObjUpvalue *, upvalueCount);

    for (size_t i = 0; i < upvalueCount; i++) {

        closure->upvalues[i] = NULL;
    }

    Value result = {};

    result.type = VAL_OBJ;
    result.hash = (size_t)closure;
    result.as.obj = (Obj *)closure;

    return result;
}

Value makeStruct(VM *vm, Value *fields, size_t fieldCount) {

    ObjStruct *objStruct = ALLOCATE_OBJ(vm, ObjStruct, OBJ_STRUCT);

    objStruct->fields = fields;
    objStruct->fieldCount = fieldCount;

    Value result = {};

    result.type = VAL_OBJ;
    result.hash = (size_t)objStruct;
    result.as.obj = (Obj *)objStruct;

    return result;
}

bool getField(ObjStruct *objStruct, size_t index, Value *out) {

    if (index >= objStruct->fieldCount) {

        return false;
    }

    if (out != NULL)
        *out = objStruct->fields[index];

    return true;
}

bool setField(ObjStruct *objStruct, size_t index, Value replacement) {

    if (index >= objStruct->fieldCount) {

        return false;
    }

    objStruct->fields[index] = replacement;

    return true;
}

bool isObjType(Value a, ObjType type) {

    return a.type == VAL_OBJ && a.as.obj->type == type;
}
