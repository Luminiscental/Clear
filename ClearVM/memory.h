#ifndef clearvm_memory_h
#define clearvm_memory_h

#include "common.h"

#define GROW_CAPACITY(capacity) ((capacity) < 8 ? 8 : (capacity)*2)

#define GROW_ARRAY(previous, type, oldCount, count)                            \
    (type *)REALLOC(previous, sizeof(type) * oldCount, sizeof(type) * count)

#define FREE_ARRAY(type, pointer, oldCount)                                    \
    REALLOC(pointer, sizeof(type) * oldCount, 0)

#define FREE(type, pointer) FREE_ARRAY(type, pointer, 1)

#define ALLOCATE(type) ALLOCATE_ARRAY(type, 1)

#define ALLOCATE_ARRAY(type, count)                                            \
    (type *)REALLOC(NULL, 0, sizeof(type) * (count))

#ifdef DEBUG_MEM
#define REALLOC(prev, old, new) reallocate(prev, old, new)
#else
#define REALLOC(prev, old, new) reallocate(prev, new)
#endif

void *reallocate(void *previous,
#ifdef DEBUG_MEM
                 size_t oldSize,
#endif
                 size_t newSize);

#endif
