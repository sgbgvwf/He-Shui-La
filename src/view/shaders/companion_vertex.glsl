/* 喝水啦 — 3D Companion Vertex Shader
 * Transforms vertex position by MVP, passes eye-space normal to fragment shader.
 */
attribute vec4 v_pos;
attribute vec3 v_normal;

uniform mat4 u_mvp;
uniform mat4 u_modelview;

varying vec3 v_normal_eye;

void main() {
    gl_Position = u_mvp * v_pos;
    v_normal_eye = normalize(mat3(u_modelview) * v_normal);
}
