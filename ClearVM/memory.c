
#include "memory.h"

#include <stdio.h>
#include <stdlib.h>

#include "common.h"

void *reallocate(void *previous, size_t oldSize, size_t newSize) {

#ifdef DEBUG_MEM

    static size_t memoryUsage = 0;

    memoryUsage += newSize;
    memoryUsage -= oldSize;

    printf("\t\t\t\t\t\t\t\tmemory: %zuB\n", memoryUsage);

#endif

    if (newSize == 0) {

        free(previous);
        return NULL;
    }

    return realloc(previous, newSize);
}

static void freeObject(Obj *object) {

    switch (object->type) {

        case OBJ_STRING: {
        
            ObjString *objStr = (ObjString*) object;
            FREE_ARRAY(char, objStr->chars, objStr->length + 1);
            FREE(ObjString, objStr);
        
        } break;
    }
}

void freeObjects(VM *vm) {

    Obj *object = vm->objects;

    while (object != NULL) {

        Obj *next = object->next;

        freeObject(object);

        object = next;
    }
}
