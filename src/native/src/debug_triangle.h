class DebugTriangle {
public:
    void setup();
    void render(const Mat4& view, const Mat4& projection);
 
private:
    Shader shader;
    GLuint vao = 0;
    GLuint vbo = 0;
};

void DebugTriangle::setup() {
    shader.load(debugVertexShaderSource, debugFragmentShaderSrc);
 
    Vertex vertices[3] = {
        { Vec3{ 0.0f,  0.5f, 0.0f}, Vec3{0, 0, 1} },
        { Vec3{-0.5f, -0.5f, 0.0f}, Vec3{0, 0, 1} },
        { Vec3{ 0.5f, -0.5f, 0.0f}, Vec3{0, 0, 1} },
    };
 
    glGenVertexArrays(1, &vao);
    glGenBuffers(1, &vbo);
 
    glBindVertexArray(vao);
    glBindBuffer(GL_ARRAY_BUFFER, vbo);
    glBufferData(GL_ARRAY_BUFFER, sizeof(vertices), vertices, GL_STATIC_DRAW);
 
    glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, sizeof(Vertex),
        (void*)offsetof(Vertex, position));
    glEnableVertexAttribArray(0);
 
    glVertexAttribPointer(1, 3, GL_FLOAT, GL_FALSE, sizeof(Vertex),
        (void*)offsetof(Vertex, normal));
    glEnableVertexAttribArray(1);
 
    glBindVertexArray(0);
}
 
void DebugTriangle::render(const Mat4& view, const Mat4& projection) {
    Mat4 model = Mat4::translate({0, 0, 0});
 
    shader.use();
    shader.setMat4("model", model);
    shader.setMat4("view", view);
    shader.setMat4("projection", projection);
 
    glBindVertexArray(vao);
    glDrawArrays(GL_TRIANGLES, 0, 3);
}