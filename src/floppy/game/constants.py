import numpy as np
import numpy.typing as npt

KEPSILON = 1e-5

type Vec = np.ndarray[tuple[int], np.dtype[np.float32]]
type Matrix = np.ndarray[tuple[int, int], np.dtype[np.float32]]

def _as_vec3(v: npt.ArrayLike, name: str = "value") -> Vec:
    a = np.asarray(v, dtype=np.float32)
    if a.shape != (3,):
        raise ValueError(f"{name}: expected shape (3,), got {a.shape}")
    return a

def _as_vec2(v: npt.ArrayLike, name: str = "value") -> Vec:
    a = np.asarray(v, dtype=np.float32)
    if a.shape != (2,):
        raise ValueError(f"{name}: expected shape (2,), got {a.shape}")
    return a

def _as_uv(v: npt.ArrayLike, name: str = "value") -> Vec:
    """Texture coordinate as (u, v, bank). A 2-tuple is taken as image bank 0."""
    a = np.asarray(v, dtype=np.float32)
    if a.shape == (2,):
        a = np.array([a[0], a[1], 0.0], dtype=np.float32)
    if a.shape != (3,):
        raise ValueError(f"{name}: expected shape (2,) or (3,), got {a.shape}")
    return a

def _as_vec4(v: npt.ArrayLike, name: str = "value") -> Vec:
    a = np.asarray(v, dtype=np.float32)
    if a.shape == (3,):
        a = np.array([a[0], a[1], a[2], 1.0], dtype=np.float32)
    if a.shape != (4,):
        raise ValueError(f"{name}: expected shape (4,) or (3,), got {a.shape}")
    return a