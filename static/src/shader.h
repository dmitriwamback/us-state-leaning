class Shader {
public:
    GLuint programId = 0;
 
    Shader() = default;
 
    // Compiles + links a vertex/fragment shader pair. Returns false (and
    // prints the GL error log) on failure rather than leaving a half-built
    // program bound.
    bool load(const char* vertexSrc, const char* fragmentSrc);
 
    void use() const;
 
    // Cache-free uniform setters -- fine for now since we're not calling
    // these hundreds of times per frame yet. If profiling later shows this
    // is a bottleneck, switch to caching locations in a map keyed by name.
    void setMat4(const char* name, const Mat4& mat) const;
    void setVec3(const char* name, float x, float y, float z) const;
    void setFloat(const char* name, float value) const;
    void setBool(const char* name, bool value) const;
 
private:
    static GLuint compile(GLenum type, const char* src);
};

GLuint Shader::compile(GLenum type, const char* src) {
    GLuint shader = glCreateShader(type);
    glShaderSource(shader, 1, &src, nullptr);
    glCompileShader(shader);
 
    GLint success;
    glGetShaderiv(shader, GL_COMPILE_STATUS, &success);
    if (!success) {
        char log[512];
        glGetShaderInfoLog(shader, 512, nullptr, log);
        printf("Shader compile error: %s\n", log);
    }
    return shader;
}
 
bool Shader::load(const char* vertexSrc, const char* fragmentSrc) {
    GLuint vs = compile(GL_VERTEX_SHADER, vertexSrc);
    GLuint fs = compile(GL_FRAGMENT_SHADER, fragmentSrc);
 
    programId = glCreateProgram();
    glAttachShader(programId, vs);
    glAttachShader(programId, fs);
    glLinkProgram(programId);
 
    GLint linked;
    glGetProgramiv(programId, GL_LINK_STATUS, &linked);
    if (!linked) {
        char log[512];
        glGetProgramInfoLog(programId, 512, nullptr, log);
        printf("Program link error: %s\n", log);
    }
 
    // shaders are linked into the program now, the standalone objects
    // aren't needed anymore
    glDeleteShader(vs);
    glDeleteShader(fs);
 
    return linked == GL_TRUE;
}
 
void Shader::use() const {
    glUseProgram(programId);
}

void Shader::setMat4(const char* name, const Mat4& mat) const {
    GLint loc = glGetUniformLocation(programId, name);
    glUniformMatrix4fv(loc, 1, GL_FALSE, mat.data());
}
 
void Shader::setVec3(const char* name, float x, float y, float z) const {
    GLint loc = glGetUniformLocation(programId, name);
    glUniform3f(loc, x, y, z);
}
 
void Shader::setFloat(const char* name, float value) const {
    GLint loc = glGetUniformLocation(programId, name);
    glUniform1f(loc, value);
}
 
void Shader::setBool(const char* name, bool value) const {
    GLint loc = glGetUniformLocation(programId, name);
    glUniform1i(loc, value ? 1 : 0); // GLSL ES 3.0 bool uniforms set via int
}