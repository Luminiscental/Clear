
#include "obj.h"

#include <stdlib.h>
#include <stdio.h>
#include <string.h>

#include "vm.h"
#include "table.h"

static uint32_t hashChars(size_t length, char *chars) {

    uint32_t hash = 2166136261u;

    for (size_t i = 0; i < length; i++) {

        hash ^= chars[i];
        hash *= 16777619;
    }

    return hash;
}

static Entry *tableFindString(Table *table, char *string, size_t length) {

    if (table->entries == NULL) return NULL;

    uint32_t hash = hashChars(length, string);
    uint32_t index = hash % table->capacity;

    while (true) {

        Entry *entry = table->entries + index;

        if (entry->state == ENTRY_EMPTY) {

            return NULL;

        } else if (entry->state == ENTRY_FULL) {

            ObjString *entryStr = (ObjString*) entry->key.as.obj;

            if (entryStr->length == length
             && entry->key.hash == hash
             && memcmp(entryStr->chars, string, length) == 0) {

                return entry;

            }
        }

        index = (index + 1) % table->capacity;
    }
}

Value makeString(VM *vm, size_t length, char *string) {

    Entry *interned = tableFindString(&vm->strings, string, length);

    if (interned != NULL) {

        return interned->key;
    } 

    Value result;

    ObjString *stringObj = (ObjString*) malloc(sizeof(ObjString));

    result.type = VAL_OBJ;
    result.hash = hashChars(length, string);

    result.as.obj = (Obj*) stringObj;
    result.as.obj->type = OBJ_STRING;

    stringObj->chars = string;
    stringObj->length = length;

    tableSet(&vm->strings, result, makeBoolean(true));

    return result;
}

Value concatStrings(VM *vm, ObjString *first, ObjString *second) {

    size_t newLength = first->length + second->length;

    char *result = (char*) malloc(newLength + 1);
    result[newLength] = '\0';

    strcpy(result, first->chars);
    strcat(result, second->chars);

    return makeString(vm, newLength, result);
}

bool isObjType(Value a, ObjType type) {

    return a.type == VAL_OBJ && a.as.obj->type == type;
}

