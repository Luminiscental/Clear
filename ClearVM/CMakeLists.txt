cmake_minimum_required(VERSION 2.6.0)
project(clr C)

set(CMAKE_EXPORT_COMPILE_COMMANDS ON)
add_definitions("-Wextra -Werror -Wswitch")
set(CMAKE_BUILD_TYPE Debug)
# add_compile_definitions(DEBUG_FILE)
# add_compile_definitions(DEBUG_DIS)
# add_compile_definitions(DEBUG_TRACE)
# add_compile_definitions(DEBUG_STACK)
# add_compile_definitions(DEBUG_MEM)

add_executable(clr main.c memory.c vm.c)
target_link_libraries(clr m)
