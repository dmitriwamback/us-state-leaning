const char* debugVertexShaderSource = R"(#version 300 es
layout(location = 0) in vec2 position;

uniform mat4 model;
uniform mat4 view;
uniform mat4 projection;

void main() {
    gl_Position = projection * view * model * vec4(position, 0.0, 1.0);
}
)";

const char* debugFragmentShaderSrc = R"(#version 300 es
precision mediump float;
out vec4 fragc;
void main() {
    fragc = vec4(0.85, 0.15, 0.15, 1.0);
}
)";