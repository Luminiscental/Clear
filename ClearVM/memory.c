
#include "memory.h"

#include <stdio.h>
#include <stdlib.h>

#include "common.h"

void *reallocate(void *previous, size_t oldSize, size_t newSize) {

#ifdef DEBUG_MEM

    static size_t memoryUsage = 0;

    memoryUsage += newSize - oldSize;

    printf("\t\t\t\t\t\t\t\tmemory: %zuB\n", memoryUsage);

#endif

    if (newSize == 0) {

        free(previous);
        return NULL;
    }

    return realloc(previous, newSize);
}
