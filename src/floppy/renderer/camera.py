import numpy as np
from renderer.math3d import look_from_to, create_proj_matrix
from game.constants import KEPSILON, Vec, Matrix


class Camera:
    def __init__(self, position: Vec = (0, 0, 3)):
        self.position = np.array(position, dtype=np.float32)
        self.orientation = np.array([0, 0, -1], dtype=np.float32)
        self.up = np.array([0, 1, 0], dtype=np.float32)
        self.camera_matrix = np.identity(4)

        self.pitch = 0
        self.yaw = 0

        self.sensitivity = 0.5

    def get_camera_matrix(self):
        return self.camera_matrix

    def updateMatrix(self, fov: int = 90, near_plane: float = 0.1,
                     far_plane: float = 100.0, width: int = 256, height: int = 256):
        safe_width = max(10, width)
        safe_height = max(10, height)

        # build view matrix
        view_matrix = look_from_to(position=self.position,
                                          up_direction=self.up,
                                          looking_to=self.position + self.orientation)

        # build projection matrix
        proj_matrix = create_proj_matrix(fov, safe_width/safe_height, near_plane, far_plane)

        self.camera_matrix = proj_matrix @ view_matrix

    def rotate(eixo: Vec, angle: float):
        pass
