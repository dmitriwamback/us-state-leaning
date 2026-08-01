#include <cstddef>
#include <cstdio>
#include <string>

class StateModel {
public:
    bool load(const std::string& objPath);
 
    void setLean(const std::string& lean, float confidence);
    void setHeightScale(float scale);
 
    void render(const Mat4& view, const Mat4& projection);
 
private:
    Shader shader;
    GLuint vertexArrayObject = 0;
    GLuint vertexBufferObject = 0;
    GLuint elementBufferObject = 0;
    size_t indexCount = 0;
 
    Vec3 baseColor{0.65f, 0.65f, 0.65f};
    Vec3 grayColor{0.65f, 0.65f, 0.65f};
    float confidence = 0.0f;
    bool isTossUp = true;
    float heightScale = 1.0f;
};
 
bool StateModel::load(const std::string& objPath) {
    std::vector<Vertex> vertices;
    std::vector<unsigned int> indices;
 
    if (!loadObj(objPath, vertices, indices)) {
        printf("StateModel: failed to load %s\n", objPath.c_str());
        return false;
    }
 
    shader.load(stateModelVertexShaderSource, stateModelFragmentShaderSource);
 
    indexCount = indices.size();
 
    glGenVertexArrays(1, &vertexArrayObject);
    glGenBuffers(1, &vertexBufferObject);
    glGenBuffers(1, &elementBufferObject);
 
    glBindVertexArray(vertexArrayObject);
 
    glBindBuffer(GL_ARRAY_BUFFER, vertexBufferObject);
    glBufferData(GL_ARRAY_BUFFER, vertices.size() * sizeof(Vertex), vertices.data(), GL_STATIC_DRAW);
 
    glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, elementBufferObject);
    glBufferData(GL_ELEMENT_ARRAY_BUFFER, indices.size() * sizeof(unsigned int), indices.data(), GL_STATIC_DRAW);
 
    glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, sizeof(Vertex), (void*)offsetof(Vertex, position));
    glEnableVertexAttribArray(0);
 
    glVertexAttribPointer(1, 3, GL_FLOAT, GL_FALSE, sizeof(Vertex), (void*)offsetof(Vertex, normal));
    glEnableVertexAttribArray(1);
 
    glBindVertexArray(0);
 
    return true;
}
 
void StateModel::setLean(const std::string& lean, float confidenceIn) {
    confidence = confidenceIn < 0.0f ? 0.0f : (confidenceIn > 1.0f ? 1.0f : confidenceIn);
    isTossUp = (lean == "Toss-up");
 
    if (lean == "D") {
        baseColor = Vec3{0.15f, 0.35f, 0.85f};
    } 
    else if (lean == "R") {
        baseColor = Vec3{0.85f, 0.15f, 0.15f};
    } 
    else {
        baseColor = grayColor;
    }
}
 
void StateModel::setHeightScale(float scale) {
    heightScale = scale;
}
 
void StateModel::render(const Mat4& view, const Mat4& projection) {
    if (vertexArrayObject == 0) return;
 
    Mat4 model = Mat4::scale({heightScale, 1.0f, 1.0f});
 
    shader.use();
    shader.setMat4("model", model);
    shader.setMat4("view", view);
    shader.setMat4("projection", projection);
    shader.setFloat("heightScale", heightScale);
    shader.setVec3("baseColor", baseColor.x, baseColor.y, baseColor.z);
    shader.setVec3("grayColor", grayColor.x, grayColor.y, grayColor.z);
    shader.setFloat("confidence", confidence);
    shader.setBool("isTossUp", isTossUp);
 
    glBindVertexArray(vertexArrayObject);
    glDrawElements(GL_TRIANGLES, (GLsizei)indexCount, GL_UNSIGNED_INT, 0);
}