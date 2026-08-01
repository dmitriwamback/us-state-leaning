#include <emscripten/emscripten.h>
#include <emscripten/html5.h>
#include <GLES3/gl3.h>
#include <iostream>
#include <math.h>
#include <stdio.h>

#include "src/linalg/vector2.h"
#include "src/linalg/vector3.h"
#include "src/linalg/vector4.h"
#include "src/linalg/matrix4.h"

#include "src/vertex.h"
#include "src/shader_sources.h"
#include "src/shader.h"
#include "src/debug_triangle.h"

EMSCRIPTEN_WEBGL_CONTEXT_HANDLE ctx;
DebugTriangle triangle;

EM_BOOL render_frame(double time, void *userData) {
    glClearColor(0.2f, 0.2f, 0.2f, 1.0f);
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT);

    Mat4 view = Mat4::lookAt(Vec3{0, 0, 3}, Vec3{0, 0, 0}, Vec3{0, 1, 0});
    Mat4 projection = Mat4::perspective(1.0472f, 1.0f, 0.1f, 100.0f);

    triangle.render(view, projection);

    return EM_TRUE;
}

int main() {
    EmscriptenWebGLContextAttributes attr;
    emscripten_webgl_init_context_attributes(&attr);
    attr.alpha          = EM_FALSE;
    attr.depth          = EM_TRUE;
    attr.stencil        = EM_FALSE;
    attr.antialias      = EM_TRUE;
    attr.majorVersion   = 2;

    ctx = emscripten_webgl_create_context("#webgl", &attr);
    if (ctx <= 0) {
        return 1;
    }
    emscripten_webgl_make_context_current(ctx);

    glEnable(GL_DEPTH_TEST);

    triangle.setup();
    emscripten_request_animation_frame_loop(render_frame, NULL);

    return 0;
}