from game.constants import Matrix, Vec, _as_vec3
import numpy as np
from numpy import cos, sin
from renderer.vertex import Vertex

class Mesh:
    def __init__(self, vertices, indices):
        # accepts either ready-made Vertex objects or bare positions
        self.vertexes = [v if isinstance(v, Vertex) else Vertex(v) for v in vertices]
        self.indices = indices
        self._T = np.identity(4)
        self._R = np.identity(4)
        
    def get_V(self, i: int):
        if i < 0:
            raise ValueError(f"vertex index is negative: {i}")
        return self.vertexes[i]

    def get_idx(self, i: int):
        if i < 0:
            raise ValueError(f"indice index is negative: {i}")
        return self.indices[i]

    def get_triangle_amount(self):
        if len(self.indices) % 3 != 0:
            raise ValueError(f"amount of indices is not multiple of 3: {len(self.indices)}")
        return len(self.indices) // 3

    def get_model(self):
        return self._T @ self._R 

    def translate_model(self, translation: Vec):
        t = _as_vec3(translation)
        translation_mat = np.array([[1, 0, 0, t[0]],
                                    [0, 1, 0, t[1]],
                                    [0, 0, 1, t[2]],
                                    [0, 0, 0, 1]])
        self._T = translation_mat @ self._T

    def rotate_model(self, axis: Vec, angle: float) -> None:
        rad = np.pi * angle / 180
        u = _as_vec3(axis)
        x, y, z = u

        rotation = np.array([[cos(rad) + x**2*(1 - cos(rad)), x*y*(1-cos(rad))-z*sin(rad), x*z*(1-cos(rad)) + y*sin(rad), 0],
                             [y*x*(1-cos(rad)) + z*sin(rad), cos(rad) + y**2*(1-cos(rad)), y*z*(1-cos(rad)) - x*sin(rad), 0],
                             [z*x*(1-cos(rad)) - y*sin(rad), z*y*(1-cos(rad)) + x*sin(rad), cos(rad) + z**2*(1-cos(rad)), 0],
                             [0, 0, 0, 1]])

        self._R = rotation @ self._R

    def scale_model(self, scale: Vec) -> None:
        s = _as_vec3(scale)
        scale_mat = np.array([[s[0], 0, 0, 0],
                              [0, s[1], 0, 0],
                              [0, 0, s[2], 0],
                              [0, 0, 0, 1]])
        self.model = scale_mat @ self._R

    def create_normals():
        pass
