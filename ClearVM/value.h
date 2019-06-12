#ifndef clearvm_value_h
#define clearvm_value_h

#include "common.h"

#define STR_MAX 512
#define NUM_PLACES 7
#define NUM_PRECISION 0.0000001

typedef enum {

    OBJ_STRING,
    OBJ_STRUCT,
    OBJ_UPVALUE

} ObjectType;

typedef struct sObjectValue ObjectValue;
struct sObjectValue {

    ObjectType type;
    void *ptr;
    ObjectValue *next;
};

typedef enum {

    VAL_BOOL,
    VAL_NIL,
    VAL_OBJ,
    VAL_INT,
    VAL_NUM,
    VAL_IP,
    VAL_FP

} ValueType;

typedef struct sUpvalueObject UpvalueObject;

typedef struct {

    ValueType type;
    UpvalueObject *references;

    union {

        bool b;
        int32_t s32;
        double f64;
        ObjectValue *obj;
        void *ptr;

    } as;

} Value;

typedef struct {

    size_t length;
    char *data;

} StringObject;

typedef struct {

    size_t fieldCount;
    Value *fields;

} StructObject;

struct sUpvalueObject {

    Value *ptr;
    Value closed;

    UpvalueObject *next;
};

typedef struct sVM VM;

Value makeObject(VM *vm, size_t size, ObjectType type);
Value makeString(VM *vm, char *data, size_t length);
Value makeStringFromLiteral(VM *vm, const char *literal);
Value makeStruct(VM *vm, size_t fieldCount);
Value makeUpvalue(VM *vm, Value *from);

Value makeInt(int32_t unboxed);
Value makeBool(bool unboxed);
Value makeNum(double unboxed);
Value makeIP(uint8_t *unboxed);
Value makeFP(Value *unboxed);

void closeUpvalue(UpvalueObject *upvalue);
Result stringifyValue(VM *vm, Value input, Value *output);
Value concatStrings(VM *vm, StringObject a, StringObject b);
bool valuesEqual(Value a, Value b);

void printValue(Value value);

typedef struct {

    Value *data;
    size_t count;
    size_t capacity;

} ValueList;

void initValueList(ValueList *list);

void growValueList(ValueList *list);
void appendValueList(ValueList *list, Value value);
Result getValueList(ValueList *list, size_t index, Value *out);
Result setValueList(ValueList *list, size_t index, Value value);

void freeValueList(ValueList *list);

#endif
