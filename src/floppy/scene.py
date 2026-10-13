import numpy as np

from game.rules import GARBAGE, GARBAGE_DELAY, HIDDEN_ROWS, NULL, PIECE_TABLE, cells

# 0..15 = art colours, then 4 shade ramps per material
ART_PALETTE = [
    0x000000, 0x262626, 0x939393, 0xFFFFFF, 0x133D37, 0x3CAA90, 0x04FFC4, 0x00FFFF,
    0x807D42, 0xFFF405, 0xFF4305, 0x8C0943, 0x793678, 0x514059, 0x33035F, 0x6305FF,
]
MATERIALS = [
    0x8A2BFF, 0x19F0E6, 0x3CE05A, 0xFF4A12, 0x2F5BFF, 0xFF9A1F, 0xF4E12A, 0x9A9A9A,
    0x8A6440,
    0x6A4C32,
    0x5E6B66,
    0x2A7A68,
    0x30303A,
    0xFFD27A,
    0x8C8C94,
    0x4A2A6A,
    0xE0E0E0, 0x19F0E6, 0x8A2BFF, 0xFF4A12, 0x3CE05A, 0xF4E12A, 0xFF5AC8, 0xFF9A1F,
]
SHADES = (0.22, 0.48, 0.74, 1.0)
FLOOR, FLOOR2, WALL, BODY, TRIM, LAMP, DRIVE, PORTAL, DISK = 8, 9, 10, 11, 12, 13, 14, 15, 16


def palette():
    out = list(ART_PALETTE)
    for rgb in MATERIALS:
        r, g, b = rgb >> 16, (rgb >> 8) & 255, rgb & 255
        for s in SHADES:
            out.append((int(r * s) << 16) | (int(g * s) << 8) | int(b * s))
    return out


def color(material, shade):
    return 16 + material * 4 + shade


LIGHT = np.array([0.0, 2.45, 1.1], np.float32)
AMBIENT = 0.28
LIGHTING = True


def shade_tris(tris, materials, emissive=None):
    if not LIGHTING:
        return (16 + np.asarray(materials) * 4 + 3).astype(np.uint8)
    a, b, c = tris[:, 0], tris[:, 1], tris[:, 2]
    n = np.cross(b - a, c - a)
    n /= np.linalg.norm(n, axis=1, keepdims=True) + 1e-9
    to_light = LIGHT - (a + b + c) / 3.0
    dist = np.linalg.norm(to_light, axis=1)
    lambert = np.maximum(0.0, (n * to_light).sum(axis=1) / dist)
    light = AMBIENT + lambert * 2.2 / (1.0 + 0.35 * dist * dist)
    shade = np.clip((light * 3.2).astype(np.int32), 0, 3)
    if emissive is not None:
        shade = np.where(emissive, 3, shade)
    return (16 + np.asarray(materials) * 4 + shade).astype(np.uint8)


def quad(p0, p1, p2, p3):
    return [(p0, p1, p2), (p0, p2, p3)]


def grid_quad(origin, du, dv, nu, nv):
    o, du, dv = (np.asarray(x, np.float32) for x in (origin, du, dv))
    out = []
    for j in range(nv):
        for i in range(nu):
            p = o + du * (i / nu) + dv * (j / nv)
            out.append(quad(p, p + du / nu, p + du / nu + dv / nv, p + dv / nv))
    return out


def box(lo, hi, skip=()):
    x0, y0, z0 = lo
    x1, y1, z1 = hi
    faces = {
        "front": quad((x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)),
        "back": quad((x1, y0, z0), (x0, y0, z0), (x0, y1, z0), (x1, y1, z0)),
        "left": quad((x0, y0, z0), (x0, y0, z1), (x0, y1, z1), (x0, y1, z0)),
        "right": quad((x1, y0, z1), (x1, y0, z0), (x1, y1, z0), (x1, y1, z1)),
        "top": quad((x0, y1, z1), (x1, y1, z1), (x1, y1, z0), (x0, y1, z0)),
        "bottom": quad((x0, y0, z0), (x1, y0, z0), (x1, y0, z1), (x0, y0, z1)),
    }
    return [t for name, f in faces.items() if name not in skip for t in f]


class Mesh:
    def __init__(self):
        self.tris, self.mats, self.emit = [], [], []

    def add(self, tris, material, emissive=False):
        self.tris += tris
        self.mats += [material] * len(tris)
        self.emit += [emissive] * len(tris)

    def build(self):
        tris = np.array(self.tris, np.float32).reshape(-1, 3, 3)
        return tris, shade_tris(tris, self.mats, np.array(self.emit))


ROOM = (-2.5, 2.5, -1.0, 4.0, 2.6)
SEAT = np.array([0.3, 1.43, 0.92], np.float32)
SEAT_LOOK = np.array([0.3, 1.42, 0.2], np.float32)


def build_room():
    x0, x1, z0, z1, h = ROOM
    m = Mesh()
    for k, tile in enumerate(grid_quad((x0, 0, z1), (x1 - x0, 0, 0), (0, 0, z0 - z1), 10, 10)):
        m.add(tile, FLOOR if (k + k // 10) % 2 else FLOOR2)
    m.add([t for q in grid_quad((x0, h, z0), (x1 - x0, 0, 0), (0, 0, z1 - z0), 5, 5) for t in q], WALL)
    m.add([t for q in grid_quad((x0, 0, z0), (x1 - x0, 0, 0), (0, h, 0), 5, 3) for t in q], WALL)
    m.add([t for q in grid_quad((x1, 0, z1), (x0 - x1, 0, 0), (0, h, 0), 5, 3) for t in q], WALL)
    m.add([t for q in grid_quad((x0, 0, z1), (0, 0, z0 - z1), (0, h, 0), 5, 3) for t in q], WALL)
    m.add([t for q in grid_quad((x1, 0, z0), (0, 0, z1 - z0), (0, h, 0), 5, 3) for t in q], WALL)

    m.add(box((-0.15, h - 0.08, 0.95), (0.15, h, 1.25)), LAMP, True)
    m.add(box((x0, 1.1, -0.5), (x0 + 0.35, 1.14, 1.5)), TRIM)
    m.add(box((x0, 0.0, -0.5), (x0 + 0.35, 1.1, -0.46)), TRIM)
    m.add(box((x0, 0.0, 1.46), (x0 + 0.35, 1.1, 1.5)), TRIM)
    m.add(box((x0 + 0.02, 1.14, -0.3), (x0 + 0.3, 1.4, 0.1)), FLOOR)
    m.add(box((x0 + 0.02, 1.14, 0.3), (x0 + 0.25, 1.3, 0.6)), DRIVE)
    m.add(box((x1 - 0.03, 0.0, 2.2), (x1, 2.0, 3.1)), FLOOR2)
    m.add(box((x1 - 0.06, 0.95, 2.3), (x1 - 0.03, 1.05, 2.4)), DRIVE)

    m.add(box((-0.4, 0.0, -0.35), (0.4, 0.95, 0.38), skip=("bottom",)), BODY)
    m.add(box((-0.4, 0.95, -0.35), (0.4, 1.02, 0.52), skip=("bottom",)), TRIM)
    m.add(box((-0.06, 1.02, 0.36), (-0.03, 1.12, 0.39)), TRIM)
    m.add(box((-0.08, 1.12, 0.34), (-0.01, 1.16, 0.41)), DISK + 3, True)
    m.add(box((0.06, 1.02, 0.38), (0.1, 1.04, 0.42)), DISK + 4, True)
    m.add(box((0.14, 1.02, 0.38), (0.18, 1.04, 0.42)), DISK + 1, True)
    m.add(box((-0.4, 1.02, -0.35), (0.4, 1.16, 0.2), skip=("bottom",)), BODY)
    m.add(box((-0.4, 1.68, -0.35), (0.4, 1.78, 0.2)), BODY)
    m.add(box((-0.4, 1.16, -0.35), (-0.358, 1.68, 0.2)), BODY)
    m.add(box((0.358, 1.16, -0.35), (0.4, 1.68, 0.2)), BODY)
    m.add(box((-0.4, 1.78, -0.35), (0.4, 1.98, 0.28)), LAMP, True)
    m.add(box((-0.44, 0.0, -0.37), (-0.4, 2.0, 0.45), skip=("bottom",)), TRIM)
    m.add(box((0.4, 0.0, -0.37), (0.44, 2.0, 0.45), skip=("bottom",)), TRIM)
    return m.build()


# art px: u right, v down, d out
class Screen:
    def __init__(self, origin, right, down, px):
        self.o = np.asarray(origin, np.float32)
        self.r = np.asarray(right, np.float32) * px
        self.dn = np.asarray(down, np.float32) * px
        self.out = np.cross(self.dn, self.r)
        self.out /= np.linalg.norm(self.out)
        self.out *= px

    def at(self, u, v, d=0.0):
        return self.o + self.r * u + self.dn * v + self.out * d

    def rect(self, u0, v0, u1, v1, d):
        return quad(self.at(u0, v1, d), self.at(u1, v1, d), self.at(u1, v0, d), self.at(u0, v0, d))


ART_W, ART_H = 256, 186
PX = 0.716 / ART_W
CABINET_SCREEN = Screen((-0.358, 1.68, 0.201), (1, 0, 0), (0, -1, 0), PX)

_yaw = np.deg2rad(-30.0)
_right = np.array([np.cos(_yaw), 0.0, -np.sin(_yaw)], np.float32)
_px = PX * 0.55
PORTAL_SCREEN = Screen(np.array([0.45, 1.3, 0.42], np.float32) - _right * _px * 126.0
                       - np.array([0, -1, 0], np.float32) * _px * 178.0, _right, (0, -1, 0), _px)

# well in bank1 px
WELL_U, WELL_V, CELL = 126.0, 178.0, 7.1
NEXT_BOX = (206, 82, 242, 110)
HOLD_BOX = (81, 42, 117, 70)


def screen_quad():
    s = CABINET_SCREEN
    tris = np.array(s.rect(0, 0, ART_W, ART_H, 0.0), np.float32)
    uvs = np.array([[(0, ART_H), (ART_W, ART_H), (ART_W, 0)], [(0, ART_H), (ART_W, 0), (0, 0)]], np.float32)
    return tris, uvs


def portal_backing(rows):
    s = PORTAL_SCREEN
    top = WELL_V - (rows - HIDDEN_ROWS) * CELL
    m = Mesh()
    m.add(s.rect(WELL_U - 10, top - 6, WELL_U + 10 * CELL + 6, WELL_V + 6, -1.0), PORTAL, True)
    m.add(s.rect(WELL_U - 6.5, top - 2, WELL_U + 10 * CELL + 2, WELL_V + 2, -0.5), 1, True)
    tris, _ = m.build()
    cols = np.full(len(tris), color(PORTAL, 1), np.uint8)
    cols[2:] = 0
    return tris, cols


class BoardDraw:
    FACE_SHADE = {"front": 3, "top": 3, "left": 2, "right": 1, "bottom": 0}

    def __init__(self):
        self.tris, self.cols = [], []

    def flat(self, s, u, v, size, material, depth=0.4):
        self.tris += s.rect(u, v, u + size, v + size, depth)
        self.cols += [color(material, 1)] * 2
        inset = size * 0.18
        self.tris += s.rect(u + inset, v + inset, u + size - inset, v + size - inset, depth + 0.2)
        self.cols += [color(material, 3)] * 2

    def cube(self, s, u, v, size, material, open_sides):
        d = size
        a = lambda uu, vv, dd: s.at(uu, vv, dd)
        u1, v1 = u + size, v + size
        faces = {
            "front": quad(a(u, v1, d), a(u1, v1, d), a(u1, v, d), a(u, v, d)),
            "top": quad(a(u, v, d), a(u1, v, d), a(u1, v, 0), a(u, v, 0)),
            "bottom": quad(a(u, v1, 0), a(u1, v1, 0), a(u1, v1, d), a(u, v1, d)),
            "left": quad(a(u, v, 0), a(u, v1, 0), a(u, v1, d), a(u, v, d)),
            "right": quad(a(u1, v, d), a(u1, v1, d), a(u1, v1, 0), a(u1, v, 0)),
        }
        for name in ("front",) + tuple(open_sides):
            self.tris += faces[name]
            self.cols += [color(material, self.FACE_SHADE[name])] * 2

    def piece(self, s, cells_uv, size, material, magic):
        filled = {(round((u - cells_uv[0][0]) / size), round((v - cells_uv[0][1]) / size)) for u, v in cells_uv}
        for u, v in cells_uv:
            if magic:
                cx, cy = round((u - cells_uv[0][0]) / size), round((v - cells_uv[0][1]) / size)
                self.cube(s, u, v, size, material, self.open_sides(filled, cx, cy))
            else:
                self.flat(s, u, v, size, material)

    @staticmethod
    def open_sides(filled, x, y):
        out = []
        if (x, y - 1) not in filled:
            out.append("top")
        if (x, y + 1) not in filled:
            out.append("bottom")
        if (x - 1, y) not in filled:
            out.append("left")
        if (x + 1, y) not in filled:
            out.append("right")
        return out

    def grid(self, s, fighter, magic, show_side=True):
        g = fighter.grid
        board = g.board
        rows = board.num_rows

        def uv(x, y, fall=0.0):
            return WELL_U + x * CELL, WELL_V - (rows - y) * CELL + fall * CELL

        top = WELL_V - (rows - HIDDEN_ROWS) * CELL
        self.tris += s.rect(WELL_U - 1, top - 1.5, WELL_U + 10 * CELL + 1, top - 0.5, 0.3)
        self.cols += [7, 7]

        self.incoming(s, g, WELL_V - top)

        filled = {(x, y) for y in range(rows) for x in range(board.num_columns) if board.occupied(x, y)}
        for x, y in filled:
            mat = board.colors[y][x]
            u, v = uv(x, y)
            if magic:
                self.cube(s, u, v, CELL, mat, self.open_sides(filled, x, y))
            else:
                self.flat(s, u, v, CELL, mat)

        if g.shape == NULL:
            return
        ghost = g.ghost()
        if ghost != g.st:
            for x, y in cells(g.shape, ghost):
                u, v = uv(x, y)
                self.tris += s.rect(u + 0.5, v + 0.5, u + CELL - 0.5, v + CELL - 0.5, 0.2)
                self.cols += [color(g.shape, 0)] * 2
        fall = fighter.fall_fraction() if show_side else 0.0
        self.piece(s, [uv(x, y, fall) for x, y in cells(g.shape, g.st)], CELL, g.shape, magic)

    def incoming(self, s, g, height):
        # garbage meter left of the well, oldest chunk at the bottom
        u0, u1 = WELL_U - 5.5, WELL_U - 2.0
        self.tris += s.rect(u0, WELL_V - height, u1, WELL_V, 0.1)
        self.cols += [color(GARBAGE, 0)] * 2
        v = WELL_V
        for chunk in g.incoming:
            if v <= WELL_V - height:
                break
            top = max(WELL_V - height, v - chunk.lines * CELL)
            if chunk.ready():
                mat, shade = 3, 3 if int(-chunk.wait * 6) % 2 == 0 else 1
            elif chunk.wait < GARBAGE_DELAY * 0.4:
                mat, shade = 5, 3
            else:
                mat, shade = GARBAGE, 2
            self.tris += s.rect(u0, top + 0.6, u1, v, 0.3)
            self.cols += [color(mat, shade)] * 2
            v = top

    def preview(self, s, shape, box, size, magic):
        pts = PIECE_TABLE[shape][0]
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        w, h = (max(xs) - min(xs) + 1) * size, (max(ys) - min(ys) + 1) * size
        u0 = (box[0] + box[2] - w) / 2
        v0 = (box[1] + box[3] - h) / 2
        cells_uv = [(u0 + (x - min(xs)) * size, v0 + (y - min(ys)) * size) for x, y in pts]
        self.piece(s, cells_uv, size, shape, magic)

    def build(self):
        return np.array(self.tris, np.float32).reshape(-1, 3, 3), np.array(self.cols, np.uint8)


def drives_mesh(count, disks, cooldown=None):
    from game.play import HACKS
    m = Mesh()
    if count:
        m.add(box((0.5, 0.0, -0.1), (0.85, 0.7, 0.3), skip=("bottom",)), TRIM)
    for i in range(count):
        y = 0.7 + i * 0.09
        m.add(box((0.52, y, -0.08), (0.83, y + 0.08, 0.28)), DRIVE)
        if i < len(disks):
            m.add(box((0.58, y + 0.025, 0.28), (0.77, y + 0.05, 0.3)), DISK + HACKS[disks[i]][0], True)
    if not m.tris:
        return np.zeros((0, 3, 3), np.float32), np.zeros(0, np.uint8)
    return m.build()
