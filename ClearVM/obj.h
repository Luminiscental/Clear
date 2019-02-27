#ifndef clearvm_obj_h
#define clearvm_obj_h

#include "common.h"
#include "value.h"

enum eObjType {

    OBJ_STRING

};

struct sObj {

    ObjType type;
};

struct sObjString {

    Obj obj;
    size_t length;
    char *chars;
};

Value concatStrings(ObjString *first, ObjString *second);
bool isObjType(Value a, ObjType type);
bool stringsEqual(ObjString *a, ObjString *b);

#endif
