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


 
static const char* stateModelVertexShaderSource = R"(#version 300 es
layout(location = 0) in vec3 position;
layout(location = 1) in vec3 normal;
 
uniform mat4 model;
uniform mat4 view;
uniform mat4 projection;
uniform float heightScale;
 
out vec3 outNormal;
out vec3 fragp;
 
void main() {
    gl_Position = projection * view * model * vec4(position, 1.0);
    outNormal = normalize(normal);
    fragp = vec3(model * vec4(position, 1.0));
}
)";
 
static const char* stateModelFragmentShaderSource = R"(#version 300 es
precision mediump float;
 
in vec3 outNormal;
in vec3 fragp;

out vec4 fragc;
 
uniform vec3 baseColor;
uniform vec3 grayColor;
uniform vec3 noDataColor;
uniform float confidence;
uniform bool isTossUp;
uniform bool dataLoaded;

vec3 lightPosition = vec3(50.0, 0.0, 0.0);
 
void main() {
    vec3 color;
 
    if (isTossUp) {
        color = grayColor;
    } 
    else {
        float remapped = 0.5 + 0.5 * confidence;
        float t = remapped * remapped;
        color = mix(grayColor, baseColor, t);
    }

    if (!dataLoaded) {
        color = noDataColor;
    }

    vec3 lightDir = normalize(lightPosition - fragp);
 
    float diffuse = max(dot(normalize(outNormal), lightDir), 0.5);
    
    fragc = vec4(color * diffuse, 1.0);
}
)";