#include <fstream>
#include <sstream>
#include <unordered_map>
#include <cstdio>
#include <vector>
#include <string>

struct FaceVertexKey {
    int positionIndex;
    int normalIndex;

    bool operator==(const FaceVertexKey& object) const {
        return positionIndex == object.positionIndex && normalIndex == object.normalIndex;
    }
};

struct FaceVertexKeyHash {
    size_t operator()(const FaceVertexKey& key) const {
        return std::hash<long long>()(
            (static_cast<long long>(key.positionIndex) << 32) ^ static_cast<unsigned int>(key.normalIndex)
        );
    }
};

void parseFaceVertexToken(const std::string& token, int& positionIndex, int& normalIndex) {
    positionIndex = 0;
    normalIndex = -1;

    size_t firstSlash = token.find('/');
    if (firstSlash == std::string::npos) {
        positionIndex = std::stoi(token);
        return;
    }

    positionIndex = std::stoi(token.substr(0, firstSlash));

    size_t secondSlash = token.find('/', firstSlash + 1);

    if (secondSlash == std::string::npos) {
        return;
    }

    std::string normalString = token.substr(secondSlash + 1);
    if (!normalString.empty()) {
        normalIndex = std::stoi(normalString);
    }
}

bool loadObj(const std::string& path, std::vector<Vertex>& vertices, std::vector<unsigned int>& indices) {
    vertices.clear();
    indices.clear();

    std::ifstream file(path);
    if (!file.is_open()) {
        printf("Cannot load file %s\n", path.c_str());
        return false;
    }

    std::vector<Vec3> positions;
    std::vector<Vec3> normals;

    std::unordered_map<FaceVertexKey, unsigned int, FaceVertexKeyHash> vertexCache;

    std::string line;
    while (std::getline(file, line)) {
        if (line.empty() || line[0] == '#') continue;

        std::istringstream iss(line);
        std::string tag;
        iss >> tag;

        if (tag == "v") {
            Vec3 position;
            iss >> position.x >> position.y >> position.z;
            positions.push_back(position);
        }
        else if (tag == "vn") {
            Vec3 normal;
            iss >> normal.x >> normal.y >> normal.z;
            normals.push_back(normal);
        }
        else if (tag == "vt") continue;

        else if (tag == "f") {
            std::vector<std::string> faceTokens;
            std::string token;
            while (iss >> token) faceTokens.push_back(token);

            if (faceTokens.size() < 3) continue;

            std::vector<unsigned int> resolvedIndices;
            resolvedIndices.reserve(faceTokens.size());

            for (const auto& t : faceTokens) {
                int positionIndex, normalIndex;
                parseFaceVertexToken(t, positionIndex, normalIndex);

                int resolvedPositionIndex = positionIndex - 1;
                if (resolvedPositionIndex < 0 || resolvedPositionIndex > (int)positions.size()) {
                    return false;
                }

                FaceVertexKey key{positionIndex, normalIndex};
                auto it = vertexCache.find(key);
                if (it != vertexCache.end()) {
                    resolvedIndices.push_back(it->second);
                    continue;
                }

                Vertex v;
                v.position = positions[resolvedPositionIndex];

                if (normalIndex > 0 && (normalIndex - 1) < (int)normals.size()) {
                    v.normal = normals[normalIndex - 1];
                }
                else {
                    v.normal = Vec3{0, 0, 0};
                }

                unsigned int newIndex = (unsigned int)vertices.size();
                vertices.push_back(v);
                vertexCache[key] = newIndex;
                resolvedIndices.push_back(newIndex);
            }

            for (size_t i = 1; i + 1 < resolvedIndices.size(); ++i) {
                indices.push_back(resolvedIndices[0]);
                indices.push_back(resolvedIndices[i]);
                indices.push_back(resolvedIndices[i + 1]);
            }
        }
    }

    if (vertices.empty()) {
        printf("no vertices parsed %s\n", path.c_str());
        return false;
    }

    return true;
}