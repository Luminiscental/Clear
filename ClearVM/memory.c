
#include "memory.h"

#include <stdio.h>
#include <stdlib.h>

#include "common.h"

void *reallocate(void *previous, size_t oldSize, size_t newSize) {

    static size_t memoryUsage = 0;

    memoryUsage += newSize - oldSize;

    printf("\t\t\t\tmemory: %zuB\n", memoryUsage);

    if (newSize == 0) {

        free(previous);
        return NULL;
    }

    return realloc(previous, newSize);
}
