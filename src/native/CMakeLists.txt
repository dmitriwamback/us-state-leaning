cmake_minimum_required(VERSION 4.1)
project(static)

set(CMAKE_CXX_STANDARD 20)

add_executable(static main.cpp)

set_target_properties(static PROPERTIES SUFFIX ".mjs")

target_link_options(static PRIVATE
        "-sMODULARIZE=1"
        "-sEXPORT_ES6=1"
        "-sMIN_WEBGL_VERSION=2"
        "-sMAX_WEBGL_VERSION=2"
        "-sUSE_WEBGL2=1"
        "-sEXPORTED_FUNCTIONS=['_setState','_main']"
        "-sEXPORTED_RUNTIME_METHODS=['ccall','cwrap']"
)