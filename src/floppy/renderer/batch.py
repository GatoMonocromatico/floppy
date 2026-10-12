import numpy as np

NEAR = 0.05


class Batch:
    def __init__(self):
        self.flat_tris, self.flat_cols = [], []
        self.tex_tris, self.tex_uvs = [], []

    def add_flat(self, tris, colors):
        self.flat_tris.append(tris)
        self.flat_cols.append(colors)

    def add_textured(self, tris, uvs):
        self.tex_tris.append(tris)
        self.tex_uvs.append(uvs)


class Rasterizer:
    def __init__(self, screen, texture):
        self.h, self.w = screen.shape
        self.screen = screen.reshape(-1)
        self.texture = texture
        self.depth = np.zeros(self.w * self.h, np.float32)
        self.ramp = np.arange(max(self.w, self.h), dtype=np.float32) + 0.5

    def draw(self, batch, PV, background):
        self.screen[:] = background
        self.depth[:] = 0.0

        frags = []
        if batch.flat_tris:
            tris = np.concatenate(batch.flat_tris)
            cols = np.concatenate(batch.flat_cols)
            frags += self.fragments(tris, PV, cols, None)
        if batch.tex_tris:
            tris = np.concatenate(batch.tex_tris)
            uvs = np.concatenate(batch.tex_uvs)
            frags += self.fragments(tris, PV, None, uvs)
        if not frags:
            return

        idx = np.concatenate([f[0] for f in frags])
        # float32 like the buffer or >= misses
        depth = np.concatenate([f[1] for f in frags]).astype(np.float32)
        color = np.concatenate([f[2] for f in frags])

        # bigger 1/w = closer
        np.maximum.at(self.depth, idx, depth)
        win = depth >= self.depth[idx]
        self.screen[idx[win]] = color[win]

    def fragments(self, tris, PV, cols, uvs):
        n = len(tris)
        ones = np.ones((n, 3, 1), np.float32)
        clip = np.concatenate([tris, ones], axis=2) @ PV.T.astype(np.float32)
        w = clip[:, :, 3]

        keep = (w > NEAR).all(axis=1)
        clip, w = clip[keep], w[keep]
        if cols is not None:
            cols = cols[keep]
        else:
            uvs = uvs[keep]

        sx = (clip[:, :, 0] / w * 0.5 + 0.5) * self.w
        sy = (0.5 - clip[:, :, 1] / w * 0.5) * self.h

        # ccw = front, y down
        area = (sx[:, 1] - sx[:, 0]) * (sy[:, 2] - sy[:, 0]) - (sx[:, 2] - sx[:, 0]) * (sy[:, 1] - sy[:, 0])
        x0 = np.floor(sx.min(axis=1)).clip(0, self.w - 1).astype(np.int32)
        y0 = np.floor(sy.min(axis=1)).clip(0, self.h - 1).astype(np.int32)
        x1 = np.ceil(sx.max(axis=1)).clip(0, self.w - 1).astype(np.int32)
        y1 = np.ceil(sy.max(axis=1)).clip(0, self.h - 1).astype(np.int32)
        keep = (area < -1e-6) & (x1 >= x0) & (y1 >= y0) & (sx.max(axis=1) >= 0) & (sy.max(axis=1) >= 0) \
            & (sx.min(axis=1) < self.w) & (sy.min(axis=1) < self.h)

        sx, sy, w, area = sx[keep], sy[keep], w[keep], area[keep]
        x0, y0, x1, y1 = x0[keep], y0[keep], x1[keep], y1[keep]
        if cols is not None:
            cols = cols[keep]
        else:
            uvs = uvs[keep]

        # group by pow2 bbox
        bw = 1 << np.ceil(np.log2(x1 - x0 + 1)).astype(np.int32)
        bh = 1 << np.ceil(np.log2(y1 - y0 + 1)).astype(np.int32)
        key = bw * 4096 + bh

        out = []
        for k in np.unique(key):
            g = np.nonzero(key == k)[0]
            BW, BH = int(k // 4096), int(k % 4096)
            out.append(self.group(sx[g], sy[g], w[g], area[g], x0[g], y0[g], BW, BH,
                                  None if cols is None else cols[g], None if uvs is None else uvs[g]))
        return out

    def group(self, sx, sy, w, area, x0, y0, BW, BH, cols, uvs):
        px = x0[:, None, None] + self.ramp[None, None, :BW]
        py = y0[:, None, None] + self.ramp[None, :BH, None]

        def edge(a, b):
            return ((sx[:, b, None, None] - sx[:, a, None, None]) * (py - sy[:, a, None, None])
                    - (sy[:, b, None, None] - sy[:, a, None, None]) * (px - sx[:, a, None, None])) / area[:, None, None]

        c0, c1 = edge(1, 2), edge(2, 0)
        c2 = 1.0 - c0 - c1
        inside = (c0 >= 0) & (c1 >= 0) & (c2 >= 0) & (px < self.w) & (py < self.h)

        iw = 1.0 / w
        d = c0 * iw[:, 0, None, None] + c1 * iw[:, 1, None, None] + c2 * iw[:, 2, None, None]

        tri, yy, xx = np.nonzero(inside)
        idx = (py[tri, yy, 0].astype(np.int32) * self.w + px[tri, 0, xx].astype(np.int32))
        depth = d[tri, yy, xx]

        if cols is not None:
            return idx, depth, cols[tri]

        b0, b1, b2 = c0[tri, yy, xx], c1[tri, yy, xx], c2[tri, yy, xx]
        uw = uvs[tri] * iw[tri, :, None]
        # perspective correct
        u = (b0 * uw[:, 0, 0] + b1 * uw[:, 1, 0] + b2 * uw[:, 2, 0]) / depth
        v = (b0 * uw[:, 0, 1] + b1 * uw[:, 1, 1] + b2 * uw[:, 2, 1]) / depth
        th, tw = self.texture.shape
        color = self.texture[v.astype(np.int32).clip(0, th - 1), u.astype(np.int32).clip(0, tw - 1)]
        return idx, depth, color
