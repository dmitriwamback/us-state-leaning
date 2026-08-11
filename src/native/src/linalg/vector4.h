struct Vec4 {
    float x, y, z, w;
 
    Vec4() = default;
    Vec4(float x_, float y_, float z_, float w_) : x(x_), y(y_), z(z_), w(w_) {}
    Vec4(const Vec3& v, float w_) : x(v.x), y(v.y), z(v.z), w(w_) {}
 
    Vec4 operator+(const Vec4& o) const { return {x+o.x, y+o.y, z+o.z, w+o.w}; }
    Vec4 operator-(const Vec4& o) const { return {x-o.x, y-o.y, z-o.z, w-o.w}; }
    Vec4 operator*(float s) const { return {x*s, y*s, z*s, w*s}; }
 
    float dot(const Vec4& o) const { return x*o.x + y*o.y + z*o.z + w*o.w; }
};