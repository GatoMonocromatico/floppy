import numpy as np
import numpy.typing as npt
from game.constants import KEPSILON, Vec, Matrix, _as_vec3


def look_from_to(*, position: npt.ArrayLike,
                 looking_to: npt.ArrayLike,
                 up_direction: npt.ArrayLike) -> Matrix:
    cam_origin = _as_vec3(position, "position")
    target = _as_vec3(looking_to, "looking_to")
    up = _as_vec3(up_direction, "up_direction")

    normalize_in_place(up)

    looking_direction = normalize(target - cam_origin)

    view_matrix = np.zeros((4, 4))

    right = normalize(np.cross(looking_direction, up))

    view_matrix[:3, :3] = [right,
                           np.cross(right, looking_direction),
                           -looking_direction]
    view_matrix[:3, 3] = -view_matrix[:3, :3] @ cam_origin


    view_matrix[3, 3] = 1

    return view_matrix

def create_proj_matrix(fov: int, ratio: float, near_plane: float, far_plane: float) -> Matrix:
    fov_radians = np.pi * fov / 180

    proj = np.zeros((4,4))

    proj[0, 0] = 1 / (np.tan(fov_radians/2) * ratio)
    proj[1, 1] = 1 / (np.tan(fov_radians/2))
    proj[2, 2] = (near_plane + far_plane)/(near_plane - far_plane)
    proj[2, 3] = 2 * near_plane * far_plane/(near_plane - far_plane)
    proj[3, 2] = -1

    return proj

def normalize_in_place(vector: npt.ArrayLike) -> None:
    module = 0

    for e in vector:
        module += e ** 2

    module = module ** 0.5

    for i in range(len(vector)):
        vector[i] /= module

def normalize(vector: npt.ArrayLike) -> Vec:
    v = np.array(vector, dtype=np.float32)

    m = module(v)

    v /= m

    return v

def module(vector: npt.ArrayLike) -> float:
    v = np.asarray(vector, dtype=np.float32)

    total = 0.0

    for e in v:
        total += float(e) ** 2

    return total ** 0.5
