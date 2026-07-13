"""GLB (glTF Binary) loader — extracts vertices, faces, and material colors.

Pure-Python parser built on ``pygltflib``. Handles embedded GLB files exported
from Blender. Returns data compatible with the software rasterizer in
``companion_3d.py``.
"""

import numpy as np
from pygltflib import GLTF2

# ── glTF accessor componentType → NumPy dtype ──────────────────────
_COMPONENT_MAP = {
    5120: np.int8,     5121: np.uint8,
    5122: np.int16,    5123: np.uint16,
    5125: np.uint32,   5126: np.float32,
}

# ── glTF accessor type → element count ─────────────────────────────
_TYPE_ELEMENTS = {"SCALAR": 1, "VEC2": 2, "VEC3": 3, "VEC4": 4}


def load_glb(path: str) -> tuple[list, list, list | None]:
    """Load a GLB file and return (vertices, faces, material_rgb_or_None).

    Parameters
    ----------
    path : str
        Filesystem path to a ``.glb`` file.

    Returns
    -------
    vertices : list[tuple[float, float, float]]
        Vertex positions.
    faces : list[list[int]]
        Triangulated face indices (0-based).
    material_rgb : list[float, float, float] or None
        Base colour ``[r, g, b]`` from the first material's PBR
        ``baseColorFactor``, or ``None`` when no material is assigned.
    """
    gltf = GLTF2().load_binary(path)

    if not gltf.meshes:
        raise ValueError(f"No meshes found in {path}")

    mesh = gltf.meshes[0]
    if not mesh.primitives:
        raise ValueError(f"Mesh has no primitives in {path}")

    primitive = mesh.primitives[0]

    # ── vertex positions ───────────────────────────────────────────
    pos_accessor = gltf.accessors[primitive.attributes.POSITION]
    pos_data = _read_accessor(gltf, pos_accessor, "VEC3", np.float32)
    vertices = [(float(x), float(y), float(z)) for x, y, z in pos_data]

    # ── indices ────────────────────────────────────────────────────
    if primitive.indices is None:
        raise ValueError(f"GLB primitive has no index buffer in {path} — non-indexed geometry not supported")

    idx_accessor = gltf.accessors[primitive.indices]
    idx_data = _read_accessor(gltf, idx_accessor, "SCALAR", None)

    # triangulate on demand
    mode = primitive.mode if primitive.mode is not None else 4
    if mode == 4:  # TRIANGLES
        faces = idx_data.reshape(-1, 3).astype(np.int32).tolist()
    elif mode == 5:  # TRIANGLE_STRIP
        raw = idx_data.astype(np.int32).tolist()
        faces = []
        for i in range(len(raw) - 2):
            if i % 2 == 0:
                faces.append([raw[i], raw[i + 1], raw[i + 2]])
            else:
                faces.append([raw[i + 1], raw[i], raw[i + 2]])
    elif mode == 6:  # TRIANGLE_FAN
        raw = idx_data.astype(np.int32).tolist()
        faces = []
        for i in range(1, len(raw) - 1):
            faces.append([raw[0], raw[i], raw[i + 1]])
    else:
        raise ValueError(f"Unsupported primitive mode {mode} in {path} — expected 4 (TRIANGLES)")

    # ── material colour ────────────────────────────────────────────
    material_rgb = None
    if primitive.material is not None and primitive.material < len(gltf.materials):
        mat = gltf.materials[primitive.material]
        pbr = mat.pbrMetallicRoughness
        if pbr is not None and pbr.baseColorFactor is not None:
            base = pbr.baseColorFactor  # [r, g, b, a]
            material_rgb = [float(base[0]), float(base[1]), float(base[2])]

    return vertices, faces, material_rgb


def _read_accessor(gltf, accessor, expected_type: str, default_dtype):
    """Read data from a glTF accessor backed by an embedded buffer.

    Parameters
    ----------
    gltf : GLTF2
        Parsed glTF object with embedded binary blob.
    accessor : Accessor
        The accessor to read.
    expected_type : str
        Expected accessor type (e.g. ``"VEC3"``, ``"SCALAR"``).
    default_dtype : numpy.dtype or None
        Fallback dtype when ``componentType`` cannot be mapped.
        If ``None``, ``componentType`` *must* be in ``_COMPONENT_MAP``.

    Returns
    -------
    numpy.ndarray
        Flat or reshaped array of vertex / index data.
    """
    # validate type
    if accessor.type != expected_type:
        raise ValueError(
            f"Expected accessor type '{expected_type}', got '{accessor.type}'"
        )

    # resolve buffer view
    bv = gltf.bufferViews[accessor.bufferView]
    blob = gltf.binary_blob()
    start = bv.byteOffset if bv.byteOffset else 0
    end = start + bv.byteLength
    raw = blob[start:end]

    # dtype
    if default_dtype is not None:
        dtype = default_dtype
    else:
        dtype = _COMPONENT_MAP.get(accessor.componentType)
        if dtype is None:
            raise ValueError(
                f"Unknown componentType {accessor.componentType}"
            )

    arr = np.frombuffer(raw, dtype=dtype)

    # reshape if multi-element type
    elem_count = _TYPE_ELEMENTS.get(accessor.type, 1)
    if elem_count > 1:
        # apply byteStride if present and wider than packed
        if bv.byteStride and bv.byteStride > elem_count * np.dtype(dtype).itemsize:
            row_bytes = bv.byteStride
            row_count = len(raw) // row_bytes
            arr = arr.reshape(row_count, row_bytes // np.dtype(dtype).itemsize)[:, :elem_count]
        else:
            arr = arr.reshape(-1, elem_count)

    # apply accessor offset
    if accessor.byteOffset:
        byte_offset_elements = accessor.byteOffset // np.dtype(dtype).itemsize
        arr = arr[byte_offset_elements:]

    # slice to accessor count (important: total buffer may be larger)
    if accessor.count:
        arr = arr[:accessor.count]

    return arr
