struct Mat4 {
    // stored as 4 columns, each a Vec4
    Vec4 col[4];
 
    // Identity by default
    Mat4() {
        col[0] = {1, 0, 0, 0};
        col[1] = {0, 1, 0, 0};
        col[2] = {0, 0, 1, 0};
        col[3] = {0, 0, 0, 1};
    }
 
    // Flat float* accessor for glUniformMatrix4fv -- column-major already
    const float* data() const { return &col[0].x; }
 
    // Matrix multiplication: this * other
    Mat4 operator*(const Mat4& o) const {
        Mat4 result;
        for (int c = 0; c < 4; ++c) {
            for (int r = 0; r < 4; ++r) {
                float sum = 0.0f;
                for (int k = 0; k < 4; ++k) {
                    // element (r, k) of `this` times element (k, c) of `o`
                    float thisElem = (&col[k].x)[r];
                    float otherElem = (&o.col[c].x)[k];
                    sum += thisElem * otherElem;
                }
                (&result.col[c].x)[r] = sum;
            }
        }
        return result;
    }
 
    Vec4 operator*(const Vec4& v) const {
        Vec4 result{0,0,0,0};
        for (int c = 0; c < 4; ++c) {
            float comp = (&v.x)[c];
            result.x += col[c].x * comp;
            result.y += col[c].y * comp;
            result.z += col[c].z * comp;
            result.w += col[c].w * comp;
        }
        return result;
    }
 
    static Mat4 translate(Vec3 t) {
        Mat4 m; // identity
        m.col[3] = {t.x, t.y, t.z, 1.0f};
        return m;
    }
 
    static Mat4 scale(Vec3 s) {
        Mat4 m; // identity
        m.col[0] = {s.x, 0, 0, 0};
        m.col[1] = {0, s.y, 0, 0};
        m.col[2] = {0, 0, s.z, 0};
        return m;
    }
 
    static Mat4 perspective(float fovYRadians, float aspect, float nearZ, float farZ) {
        Mat4 m;
        float f = 1.0f / std::tan(fovYRadians / 2.0f);
 
        m.col[0] = { f / aspect, 0, 0, 0 };
        m.col[1] = { 0, f, 0, 0 };
        m.col[2] = { 0, 0, (farZ + nearZ) / (nearZ - farZ), -1.0f };
        m.col[3] = { 0, 0, (2.0f * farZ * nearZ) / (nearZ - farZ), 0 };
 
        return m;
    }
 
    static Mat4 lookAt(Vec3 eye, Vec3 center, Vec3 up) {
        Vec3 f = (center - eye).normalized();
        Vec3 s = f.cross(up).normalized();
        Vec3 u = s.cross(f);
 
        Mat4 m;
        m.col[0] = { s.x, u.x, -f.x, 0 };
        m.col[1] = { s.y, u.y, -f.y, 0 };
        m.col[2] = { s.z, u.z, -f.z, 0 };
        m.col[3] = { -s.dot(eye), -u.dot(eye), f.dot(eye), 1 };
 
        return m;
    }
};