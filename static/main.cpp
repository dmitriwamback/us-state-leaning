#include <emscripten/emscripten.h>
#include <emscripten/html5.h>
#include <GLES2/gl2.h>
#include <iostream>
#include <stdio.h>

EMSCRIPTEN_WEBGL_CONTEXT_HANDLE ctx;

EM_BOOL render_frame(double time, void *userData) {
    glClearColor(0.9f, 0.2f, 0.2f, 1.0f);
    glClear(GL_COLOR_BUFFER_BIT);
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
    emscripten_webgl_make_context_current(ctx);

    emscripten_request_animation_frame_loop(render_frame, NULL);

    return 0;
}