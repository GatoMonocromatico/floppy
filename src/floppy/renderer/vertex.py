import numpy as np
from game.constants import Vec, _as_vec3, _as_uv, Matrix, _as_vec4
from renderer.camera import Camera

class Vertex:
    def __init__(self,
                 position: Vec,
                 texUV: Vec = (0, 0),
                 maskUV: Vec = (0, 0),
                 normal: Vec = (0, 0, 0)):

        self.position = _as_vec4(position)
        # (u, v, bank): the third component names the pyxel image bank to
        # sample. Meshes that still carry 2-component UVs default to bank 0.
        self.texUV = _as_uv(texUV)
        self.maskUV = _as_uv(maskUV)
        self.normal = _as_vec3(normal)


def to_screen(vert: Vertex, width: int, height: int) -> Vec:
    clip = vert.position

    w = float(clip[3])

    if w <= 0.0:
        vert.position = np.array([0.0, 0.0, 0.0, w], dtype=np.float64)
        return vert

    ndc = clip[:3] / w

    sx = (ndc[0] * 0.5 + 0.5) * width
    sy = (1.0 - (ndc[1] * 0.5 + 0.5)) * height

    vert.position = np.array([sx, sy, ndc[2], w], dtype=np.float64)

    return vert


def proj_triangle(V0: Vertex, V1: Vertex, V2: Vertex, model: Matrix, PV: Matrix,
                  width: int = 256, height: int = 256) -> tuple:
    PVM = PV @ model

    V0.position = PVM @ V0.position
    V1.position = PVM @ V1.position
    V2.position = PVM @ V2.position

    return (to_screen(V0, width, height),
            to_screen(V1, width, height),
            to_screen(V2, width, height))
