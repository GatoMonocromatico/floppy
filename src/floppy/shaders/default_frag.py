import numpy as np
from renderer.vertex import Vertex
from game.constants import Matrix
import pyxel

def deafult_fragment(A: Vertex, B: Vertex, C: Vertex, c0s: Matrix, c1s: Matrix, c2s: Matrix, mask: Matrix, tex_buf):
    iw0 = 1 / A.position[3]
    iw1 = 1 / B.position[3]
    iw2 = 1 / C.position[3]

    us = (c0s * iw0 * A.texUV[0] + c1s * iw1 * B.texUV[0] + c2s * iw2 * C.texUV[0]) / (c0s * iw0 + c1s * iw1 + c2s * iw2)
    vs = (c0s * iw0 * A.texUV[1] + c1s * iw1 * B.texUV[1] + c2s * iw2 * C.texUV[1]) / (c0s * iw0 + c1s * iw1 + c2s * iw2)

    return tex_buf[vs.astype(int)* mask, us.astype(int)* mask] 
