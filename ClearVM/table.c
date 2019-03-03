
#include "table.h"

#include <stdio.h>

#include "memory.h"

void initTable(Table *table) {

    table->count = 0;
    table->capacity = 0;
    table->entries = NULL;
}

static bool isAvailable(Entry *entry) {

    return entry->state == ENTRY_EMPTY || entry->state == ENTRY_TOMBSTONE;
}

static Entry *findEntry(Entry *entries, size_t capacity, Value key) {

    uint32_t index = key.hash % capacity;
    Entry *tombstone = NULL;

    while (true) {

        Entry *entry = entries + index;

        if (entry->state == ENTRY_EMPTY) {

            return tombstone != NULL ? tombstone : entry;

        } else if (entry->state == ENTRY_TOMBSTONE) {

            if (tombstone == NULL)
                tombstone = entry;

        } else if (valuesEqual(entry->key, key)) {

            return entry;
        }

        index = (index + 1) % capacity;
    }
}

static void adjustCapacity(Table *table, size_t capacity) {

    Entry *entries = ALLOCATE(Entry, capacity);

    for (size_t i = 0; i < capacity; i++) {

        entries[i].state = ENTRY_EMPTY;
    }

    table->count = 0;
    for (size_t i = 0; i < table->capacity; i++) {

        Entry *entry = table->entries + i;

        if (isAvailable(entry))
            continue;

        Entry *dest = findEntry(entries, capacity, entry->key);
        dest->key = entry->key;
        dest->value = entry->value;
        dest->state = ENTRY_FULL;
        table->count++;
    }

    FREE_ARRAY(Entry, table->entries, table->capacity);
    table->entries = entries;
    table->capacity = capacity;
}

bool tableGet(Table *table, Value key, Value *outValue) {

    if (table->entries == NULL)
        return false;

    Entry *entry = findEntry(table->entries, table->capacity, key);
    if (isAvailable(entry))
        return false;

    *outValue = entry->value;
    return true;
}

bool tableSet(Table *table, Value key, Value value) {

    if (table->count + 1 > table->capacity * TABLE_MAX_LOAD) {

        size_t capacity = GROW_CAPACITY(table->capacity);
        adjustCapacity(table, capacity);
    }

    Entry *entry = findEntry(table->entries, table->capacity, key);

    bool isNewKey = entry->state == ENTRY_EMPTY;
    if (isNewKey)
        table->count++;

    entry->key = key;
    entry->value = value;
    entry->state = ENTRY_FULL;

    return isNewKey;
}

bool tableDelete(Table *table, Value key) {

    if (table->count == 0)
        return false;

    Entry *entry = findEntry(table->entries, table->capacity, key);
    if (isAvailable(entry))
        return false;

    entry->state = ENTRY_TOMBSTONE;
    return true;
}

void tableAddAll(Table *from, Table *to) {

    for (size_t i = 0; i < from->capacity; i++) {

        Entry *entry = from->entries + i;

        if (entry->state != ENTRY_EMPTY) {

            tableSet(to, entry->key, entry->value);
        }
    }
}

void freeTable(Table *table) {

    FREE_ARRAY(Entry, table->entries, table->capacity);
    initTable(table);
}
