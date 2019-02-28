
#include <stdio.h>
#include <stdlib.h>

#include "common.h"
#include "chunk.h"
#include "vm.h"
#include "memory.h"

typedef struct {

    char *buffer;
    size_t length;

} FileBuffer;

FileBuffer readFile(const char *fileName) {

    FILE *inFile = fopen(fileName, "rb");

    FileBuffer result = { .buffer = NULL, .length = 0 };

    if (!inFile) {

        return result;
    }

    if (fseek(inFile, 0, SEEK_END)) {
        
        fclose(inFile);
        return result;
    }

    size_t fileLength = ftell(inFile);
    printf("File has length %zu\n\n", fileLength);

    if (fseek(inFile, 0, SEEK_SET)) {

        fclose(inFile);
        return result;
    }

    char *buffer = ALLOCATE(char, fileLength);

    fread(buffer, 1, fileLength, inFile);

    fclose(inFile);

    result.buffer = buffer;
    result.length = fileLength;

    return result;
}

int main(int argc, char **argv) {

    if (argc < 2) {

        printf("Incorrect usage: Please pass a .crl.b file to run\n");
        return 1;
    }

    VM vm;
    initVM(&vm);

    FileBuffer byteCode = readFile(argv[1]);

    if (byteCode.buffer == NULL) {

        printf("Could not read file!\n");
        return 1;
    }

    Chunk chunk;
    initChunk(&chunk);

    for (size_t i = 0; i < byteCode.length; i++) {

        writeChunk(&chunk, byteCode.buffer[i]);
    }

    FREE_ARRAY(char, byteCode.buffer, byteCode.length);

#ifdef DEBUG_DIS

    printf("Disassembling:\n");
    disassembleChunk(&chunk, "main");
    printf("\n");

#endif

    printf("Running:\n");
    interpret(&vm, &chunk);
    printf("\n");

    freeVM(&vm);
    freeChunk(&chunk);

    return 0;
}

