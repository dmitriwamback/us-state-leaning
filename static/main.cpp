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
#include "src/model_loader.h"
#include "src/shader_sources.h"
#include "src/shader.h"
#include "src/debug_triangle.h"
#include "src/state_model.h"

EMSCRIPTEN_WEBGL_CONTEXT_HANDLE ctx;
DebugTriangle triangle;

StateModel california, maine, texas;

EM_BOOL render_frame(double time, void *userData) {
    glClearColor(0.0f, 0.0f, 0.0f, 1.0f);
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT);

    Mat4 view = Mat4::lookAt(Vec3{20, 0, 0}, Vec3{0, 0, 0}, Vec3{0, 1, 0});
    Mat4 projection = Mat4::perspective(1.0472f, 1920.0f/974.0f, 0.1f, 100.0f);

    california.render(view, projection);
    maine.render(view, projection);
    texas.render(view, projection);

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

    std::vector<Vertex> vertices;
    std::vector<unsigned int> indices;

    california.load("state-models/California.obj");
    california.setLean("D", 0.95);
    california.setHeightScale(1.0f);

    maine.load("state-models/Maine.obj");
    maine.setLean("D", 0.3);
    maine.setHeightScale(1.0f);

    texas.load("state-models/Texas.obj");
    texas.setLean("R", 0.1);
    texas.setHeightScale(1.0f);

    emscripten_request_animation_frame_loop(render_frame, NULL);

    return 0;
}