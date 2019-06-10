cmake_minimum_required(VERSION 2.6.0)
project(clr C)

option(DEBUG "Whether to compile in debug mode" ON)
option(DEBUG_MEM "Whether to print out memory allocation info" OFF)
option(DEUBG_STACK "Whether to print stack info" OFF)

if(DEBUG)
    set(CMAKE_BUILD_TYPE Debug)
    add_definitions("-Wextra -Wall -Werror -Wswitch")

	add_compile_definitions(DEBUG)
endif()

if(DEBUG_STACK)
	add_compile_definitions(DEBUG_TRACE)
	add_compile_definitions(DEBUG_STACK)
endif()

if(DEBUG_MEM)
	add_compile_definitions(DEBUG_MEM)
endif()

set(CMAKE_EXPORT_COMPILE_COMMANDS ON)

add_executable(clr main.c memory.c vm.c bytecode.c value.c)
target_link_libraries(clr m)
