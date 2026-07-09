/* 喝水啦 — 3D Companion Fragment Shader
 * Simple ambient + diffuse lighting with a configurable tint color.
 */
varying vec3 v_normal_eye;

uniform vec3 u_light_dir;
uniform vec4 u_diffuse_color;
uniform vec4 u_ambient_color;

void main() {
    vec3 light = normalize(u_light_dir);
    vec3 normal = normalize(v_normal_eye);

    float n_dot_l = max(dot(normal, light), 0.0);

    gl_FragColor = u_ambient_color + u_diffuse_color * n_dot_l;
    gl_FragColor.a = 1.0;
}
