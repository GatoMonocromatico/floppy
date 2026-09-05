import numpy as np
from game.constants import Vec, Matrix

def find_bbox(A: Vec, B: Vec, C: Vec, width: int, height: int) -> tuple:
    x_min = min(A[0], B[0], C[0])
    y_min = min(A[1], B[1], C[1])
    x_max = max(A[0], B[0], C[0])
    y_max = max(A[1], B[1], C[1])

    # vertices already arrive in pixel coordinates
    x_min = max(0, int(np.floor(x_min)))
    y_min = max(0, int(np.floor(y_min)))
    x_max = min(width - 1, int(np.ceil(x_max)))
    y_max = min(height - 1, int(np.ceil(y_max)))

    return(x_min, y_min, x_max, y_max)

def rasterize(A: Vec, B: Vec, C: Vec, width: int, height: int) -> tuple:
    x_min, y_min, x_max, y_max = find_bbox(A, B, C, width, height)

    if x_min > x_max or y_min > y_max:
        return None

    xs = np.arange(x_max - x_min + 1)[None, :] + x_min + 0.5
    ys = np.arange(y_max - y_min + 1)[:, None] + y_min + 0.5

    # every pixel position must be able to be expressed
    # as a weighted mean of the three triangle vertices
    # px = c1 * Ax + c2 * Bx + c3 * Cx
    # py = c1 * Ay + c2 * By + c3 * Cy
    # c1 + c2 + c3 = 1 (same constants for x and y)
    # this system has 3 equations and 3 unkows
    # solving:

    # aux for the whole solution
    d = (B[1]-C[1])*(A[0]-C[0]) + (C[0]-B[0])*(A[1]-C[1])

    if d == 0:
        return None

    # aux for c0
    i0 = (B[1]-C[1])/d
    j0 = (C[0]-B[0])/d
    k0 = -(i0*C[0] + j0*C[1])

    # aux for c1
    i1 = (C[1]-A[1])/d
    j1 = (A[0]-C[0])/d
    k1 = -(i1*C[0] + j1*C[1])

    # c2 is 1 - (c0 + c1)

    c0s = i0 * xs + j0 * ys + k0
    c1s = i1 * xs + j1 * ys + k1
    c2s = 1 - (c0s + c1s)

    # managing calculating depth
    iw0 = 1 / A[3]
    iw1 = 1 / B[3]
    iw2 = 1 / C[3]

    #the bigger the value the closer the pixel should be considered
    depth_buffer = c0s * iw0 + c1s * iw1 + c2s * iw2

    # if one of those values are less than 0
    # then it is outside one of the edges
    return (c0s, c1s, c2s, depth_buffer, x_min, y_min, x_max, y_max)



# d = (y1-y2)*(x0-x2) + (x2-x1)*(y0-y2)
# a0 = (y1-y2)/d      b0 = (x2-x1)/d      c0 = -(a0*x2 + b0*y2)
# a1 = (y2-y0)/d      b1 = (x0-x2)/d      c1 = -(a1*x2 + b1*y2)
