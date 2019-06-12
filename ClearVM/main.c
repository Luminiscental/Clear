
#include "stdio.h"
#include "stdlib.h"
#include "string.h"

#include "bytecode.h"
#include "common.h"
#include "memory.h"
#include "vm.h"

typedef struct {

    uint8_t *buffer;
    size_t length;

} FileBuffer;

FileBuffer readFile(const char *name) {

    size_t nameLength = strlen(name);
    size_t fileNameLength = nameLength + 6;

    char *fileName = ALLOCATE_ARRAY(char, fileNameLength + 1);
    fileName[fileNameLength] = '\0';
    strcpy(fileName, name);
    strcat(fileName, ".clr.b");

#ifdef DEBUG

    printf("File: %s\n", fileName);

#endif

    FILE *inFile = fopen(fileName, "rb");

    FREE_ARRAY(char, fileName, fileNameLength + 1);

    FileBuffer result = {.buffer = NULL, .length = 0};

    if (!inFile) {

        return result;
    }

    if (fseek(inFile, 0, SEEK_END)) {

        fclose(inFile);
        return result;
    }

    size_t fileLength = ftell(inFile);

#ifdef DEBUG

    printf("File has length %zu\n\n", fileLength);

#endif

    if (fseek(inFile, 0, SEEK_SET)) {

        fclose(inFile);
        return result;
    }

    uint8_t *buffer = ALLOCATE_ARRAY(uint8_t, fileLength);

    fread(buffer, 1, fileLength, inFile);

    fclose(inFile);

    result.buffer = buffer;
    result.length = fileLength;

    return result;
}

int main(int argc, char **argv) {

#define EXIT(code)                                                             \
    do {                                                                       \
        return code;                                                           \
    } while (false)

    if (argc < 2) {

        printf("Incorrect usage: Please pass a .crl.b file to run\n");
        EXIT(1);
    }

    VM vm;
    if (initVM(&vm) != RESULT_OK) {

        printf("|| Could not initialize vm\n");
        EXIT(1);
    }

#undef EXIT
#define EXIT(code)                                                             \
    do {                                                                       \
        freeVM(&vm);                                                           \
        return code;                                                           \
    } while (false)

    FileBuffer byteCode = readFile(argv[1]);

    if (byteCode.length == 0) {

        printf("File contains no instructions!\n");
        EXIT(1);
    }

    if (byteCode.buffer == NULL) {

        printf("Could not read file!\n");
        EXIT(1);
    }

#undef EXIT
#define EXIT(code)                                                             \
    do {                                                                       \
                                                                               \
        FREE_ARRAY(uint8_t, byteCode.buffer, byteCode.length);                 \
        freeVM(&vm);                                                           \
        return code;                                                           \
                                                                               \
    } while (false)

#ifdef DEBUG

    printf("\nDisassembling:\n```\n");
    Result disResult = disassembleCode(byteCode.buffer, byteCode.length);
    printf("```\n");

    if (disResult != RESULT_OK) {

        printf("Invalid code!\n");
        EXIT(1);
    }

#endif

    printf("\nRunning:\n```\n");
    Result execResult = executeCode(&vm, byteCode.buffer, byteCode.length);
    printf("```\n");

    if (execResult != RESULT_OK) {

        printf("Error while running!\n");
        EXIT(1);
    }

    EXIT(0);
}
