#ifndef clearvm_table_h
#define clearvm_table_h

#include "common.h"
#include "obj.h"

#define TABLE_MAX_LOAD 0.75

typedef enum {

    ENTRY_EMPTY,
    ENTRY_FULL,
    ENTRY_TOMBSTONE

} EntryState;

typedef struct {

    Value key;
    Value value;
    EntryState state;

} Entry;

typedef struct {

    size_t count;
    size_t capacity;
    Entry *entries;

} Table;

void initTable(Table *table);
bool tableGet(Table *table, Value key, Value *outValue);
bool tableSet(Table *table, Value key, Value value);
bool tableDelete(Table *table, Value key);
void tableAddAll(Table *from, Table *to);
void freeTable(Table *table);

#endif
