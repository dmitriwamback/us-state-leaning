#include <emscripten/emscripten.h>
#include <emscripten/html5.h>
#include <GLES3/gl3.h>
#include <iostream>
#include <map>
#include <math.h>
#include <stdio.h>
#include <string>

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

#include <cstdlib>
#include <ctime>

EMSCRIPTEN_WEBGL_CONTEXT_HANDLE ctx;
DebugTriangle triangle;

std::map<std::string, std::string> abbreviationsToStateName = {
    {"AL", "Alabama"},          {"AK", "Alaska"},       {"AZ", "Arizona"},          {"AR", "Arkansas"},
    {"CA", "California"},       {"CO", "Colorado"},     {"CT", "Connecticut"},      {"DE", "Delaware"},
    {"FL", "Florida"},          {"GA", "Georgia"},      {"HI", "Hawaii"},           {"ID", "Idaho"}, 
    {"IL", "Illinois"},         {"IN", "Indiana"},      {"IA", "Iowa"},             {"KS", "Kansas"},
    {"KY", "Kentucky"},         {"LA", "Louisiana"},    {"ME", "Maine"},            {"MD", "Maryland"},         
    {"MA", "Massachusetts"},    {"MI", "Michigan"},     {"MN", "Minnesota"},        {"MS", "Mississippi"},      
    {"MO", "Missouri"},         {"MT", "Montana"},      {"NE", "Nebraska"},         {"NV", "Nevada"},           
    {"NH", "New Hampshire"},    {"NJ", "New Jersey"},   {"NM", "New Mexico"},       {"NY", "New York"},         
    {"NC", "North Carolina"},   {"ND", "North Dakota"}, {"OH", "Ohio"},             {"OK", "Oklahoma"},         
    {"OR", "Oregon"},           {"PA", "Pennsylvania"}, {"RI", "Rhode Island"},     {"SC", "South Carolina"},   
    {"SD", "South Dakota"},     {"TN", "Tennessee"},    {"TX", "Texas"},            {"UT", "Utah"},             
    {"VT", "Vermont"},          {"VA", "Virginia"},     {"WA", "Washington"},       {"WV", "West Virginia"},    
    {"WI", "Wisconsin"},        {"WY", "Wyoming"},      {"DC", "Washington DC"}
};

std::map<std::string, int> electoralVotes = {
    {"AL", 9},      {"AK", 3},      {"AZ", 11},     {"AR", 6},
    {"CA", 54},     {"CO", 10},     {"CT", 7},      {"DE", 3},
    {"FL", 30},     {"GA", 16},     {"HI", 4},      {"ID", 4}, 
    {"IL", 19},     {"IN", 11},     {"IA", 6},      {"KS", 6},
    {"KY", 8},      {"LA", 8},      {"ME", 4},      {"MD", 10},         
    {"MA", 11},     {"MI", 15},     {"MN", 10},     {"MS", 6},      
    {"MO", 10},     {"MT", 4},      {"NE", 5},      {"NV", 6},           
    {"NH", 4},      {"NJ",14},      {"NM", 5},      {"NY", 28},         
    {"NC", 16},     {"ND", 3},      {"OH", 17},     {"OK", 7},         
    {"OR", 8},      {"PA", 19},     {"RI", 4},      {"SC", 9},   
    {"SD", 3},      {"TN", 11},     {"TX", 40},     {"UT", 6},             
    {"VT", 3},      {"VA", 13},     {"WA", 12},     {"WV", 4},    
    {"WI", 10},     {"WY", 3},      {"DC", 3}
};
std::map<std::string, StateModel> stateGeometry;

EM_BOOL render_frame(double time, void *userData) {
    glClearColor(0.0f, 0.0f, 0.0f, 1.0f);
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT);

    Mat4 view = Mat4::lookAt(Vec3{25, 0, 0}, Vec3{0, 0, 0}, Vec3{0, 1, 0});
    Mat4 projection = Mat4::perspective(1.0472f, 1920.0f/974.0f, 0.1f, 100.0f);

    for (auto& [key, value] : stateGeometry) {
        value.render(view, projection);
    }

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

    srand(time(nullptr));

    for (const auto& [key, value] : abbreviationsToStateName) {

        float r = (float)rand() / RAND_MAX;
        std::string party = "";

        float t = (float)rand() / RAND_MAX;
        if (t > 0.5f) party = "D";
        else party = "R";

        stateGeometry[key] = StateModel();
        stateGeometry[key].load(std::string("state-models/") + value + ".obj");
        stateGeometry[key].setLean(party, r);
        stateGeometry[key].setHeightScale((float)electoralVotes[key]/50.0f);
    }

    emscripten_request_animation_frame_loop(render_frame, NULL);

    return 0;
}