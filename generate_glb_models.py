"""Generate GLB model files from existing OBJ data with embedded materials.

Run this script once to convert the four placeholder OBJ files to GLB.
Each model gets a distinct material colour that will be blended with the
hydration-driven dynamic colour in the renderer.

Usage:  python generate_glb_models.py
"""

import os, struct
import numpy as np
from pygltflib import (
    GLTF2, Scene, Node, Mesh, Primitive, Attributes,
    Accessor, BufferView, Material, PbrMetallicRoughness, Buffer, Asset,
)

MODELS_DIR = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "src", "view", "resources", "models",
)

# ── per-model material colours ─────────────────────────────────────
# Multiply-blended with hydration tint in the renderer.
# White [1,1,1] means "no material influence".
MODEL_CONFIGS = {
    "companion": [0.25, 0.65, 1.00],   # blue — matches original _diffuse
    "crystal":   [0.30, 0.90, 0.85],   # cyan crystal
    "diamond":   [0.85, 0.55, 1.00],   # purple diamond
    "ico":       [0.35, 0.90, 0.40],   # green icosahedron
}


def load_obj_raw(path):
    """Parse an OBJ file into vertices and triangulated faces (1-based indices)."""
    positions, faces = [], []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split()
            t = parts[0]
            if t == "v":
                positions.append((float(parts[1]), float(parts[2]), float(parts[3])))
            elif t == "f":
                pts = []
                for vi in range(1, len(parts)):
                    vs = parts[vi]
                    vi_s = vs.split("/")[0] if "/" in vs else vs
                    pts.append(int(vi_s))
                for i in range(1, len(pts) - 1):
                    faces.append([pts[0], pts[i], pts[i + 1]])
    return positions, faces


def build_glb(name, verts_3d, faces_1based, base_color):
    """Create an in-memory GLTF2 model and save it as .glb."""

    # ── convert to flat float32 / uint16 numpy arrays ──────────
    verts_flat = np.array(verts_3d, dtype=np.float32).flatten()  # [x0,y0,z0, x1,y1,z1, ...]
    indices = np.array([[i - 1 for i in f] for f in faces_1based], dtype=np.uint32).flatten()

    verts_bytes = verts_flat.tobytes()
    idx_bytes = indices.tobytes()

    # pad to 4-byte alignment (required by GLB spec)
    while len(verts_bytes) % 4 != 0:
        verts_bytes += b"\x00"
    while len(idx_bytes) % 4 != 0:
        idx_bytes += b"\x00"

    # ── assemble binary blob ──────────────────────────────────
    binary_blob = verts_bytes + idx_bytes

    # ── buffer views ──────────────────────────────────────────
    bv_verts = BufferView(
        buffer=0, byteOffset=0, byteLength=len(verts_bytes),
        target=34962,  # ARRAY_BUFFER
    )
    bv_idx = BufferView(
        buffer=0, byteOffset=len(verts_bytes), byteLength=len(idx_bytes),
        target=34963,  # ELEMENT_ARRAY_BUFFER
    )

    # ── accessors ─────────────────────────────────────────────
    acc_verts = Accessor(
        bufferView=0, byteOffset=0,
        componentType=5126,  # FLOAT
        count=len(verts_3d), type="VEC3",
        max=[float(v) for v in verts_flat.reshape(-1, 3).max(axis=0)],
        min=[float(v) for v in verts_flat.reshape(-1, 3).min(axis=0)],
    )
    acc_idx = Accessor(
        bufferView=1, byteOffset=0,
        componentType=5125,  # UNSIGNED_INT
        count=indices.size, type="SCALAR",
        max=[int(indices.max())], min=[int(indices.min())],
    )

    # ── material ──────────────────────────────────────────────
    mat = Material(
        name=f"{name}_material",
        pbrMetallicRoughness=PbrMetallicRoughness(
            baseColorFactor=[float(base_color[0]), float(base_color[1]),
                              float(base_color[2]), 1.0],
            metallicFactor=0.0,
            roughnessFactor=1.0,
        ),
    )

    # ── mesh primitive ────────────────────────────────────────
    primitive = Primitive(
        attributes=Attributes(POSITION=0),
        indices=1,
        material=0,
        mode=4,  # TRIANGLES
    )
    mesh = Mesh(name=name, primitives=[primitive])

    # ── scene graph ───────────────────────────────────────────
    node = Node(mesh=0, name=name)
    scene = Scene(nodes=[0], name="default")

    # ── assemble GLTF2 ────────────────────────────────────────
    gltf = GLTF2(
        asset=Asset(version="2.0", generator="pygltflib"),
        scenes=[scene],
        nodes=[node],
        meshes=[mesh],
        materials=[mat],
        accessors=[acc_verts, acc_idx],
        bufferViews=[bv_verts, bv_idx],
        buffers=[Buffer(byteLength=len(binary_blob))],
        scene=0,
    )

    # ── write ─────────────────────────────────────────────────
    out_path = os.path.join(MODELS_DIR, f"{name}.glb")
    gltf.set_binary_blob(binary_blob)
    gltf.save_binary(out_path)
    print(f"  -> {out_path}  ({len(verts_3d)} verts, {len(faces_1based)} faces)")


def main():
    print("Generating GLB models...")
    for name, color in MODEL_CONFIGS.items():
        obj_path = os.path.join(MODELS_DIR, f"{name}.obj")
        if not os.path.exists(obj_path):
            print(f"  SKIP {name}: OBJ not found at {obj_path}")
            continue
        verts, faces = load_obj_raw(obj_path)
        build_glb(name, verts, faces, color)
    print("Done.")


if __name__ == "__main__":
    main()
