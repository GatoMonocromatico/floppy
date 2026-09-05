import numpy as np
from renderer.camera import Camera
from renderer.mesh import Mesh
from renderer.vertex import Vertex

# ---------------------------------------------------------------------------
# Scene constants (ported from Resources.cpp)
# ---------------------------------------------------------------------------
# The whole scene is tilted 82 degrees around X, so almost every position is
# some length projected onto (sin 82, -cos 82). dsin/dcos in the original.
S82 = float(np.sin(np.deg2rad(82.0)))
C82 = float(np.cos(np.deg2rad(82.0)))

# Screen quad (UI + monitor): half height, width, atlas cell size.
SCREEN_HALF_H = 0.41345
SCREEN_W = 1.1
CELL_U = 0.15966796875
CELL_V = 0.239501953125

# Arcade cabinet body: half height, width, and the offsets that recentre it
# around the screen quad.
BODY_HALF_H = 0.78113
BODY_W = 1.558
BODY_OFF_X = 0.2289833984375
BODY_OFF_Y = 0.0457693359375

# Side walls: thickness on X, and the atlas strip they sample from.
WALL_T = 0.0457966796875
WALL_U0 = 0.65966796875
WALL_DU = 0.003910068426197
WALL_DV = 0.007820136852394

# Portal quad: atlas cell for the diffuse sheet and for the spawn animation.
PORTAL_TEX_U = 0.666015625
PORTAL_MASK_U = 0.146484375
PORTAL_MASK_V = 0.10986328125

# Brick unit cube: half height and side length. Its atlas cell used to live
# here too (BRICK_UV, 7.5px normalised); it is now a pixel rect on bank 0,
# declared next to the vertices that use it.
BRICK_HALF_H = 0.015241935483870
BRICK_SIDE = 0.030483870967741


class Resources:
        def __init__(self):
            self.camera = Camera()

            self.anims = []
            self.verts = []
            self.indices = []
            self.meshs = []

            # ---------------------------------------------------------------
            # arcade
            # ---------------------------------------------------------------
            # 30 vertices. Three stacked quads sharing the same footprint (UI,
            # monitor, cabinet, separated only by tiny Z offsets so they never
            # z-fight) plus the two side walls, each built as three strips.
            # Vertices 28 and 29 are unreferenced in the original index list.
            vertices_arcade = [
                # UI
                # v<-  0
                Vertex((0.0, -SCREEN_HALF_H * S82, -SCREEN_HALF_H * -C82 + 0.00002),
                       texUV=(0.5 + CELL_U * 0.0, CELL_V * 1.0),
                       maskUV=(CELL_U * 0.0, CELL_V * 0.0)),
                # ^<-  1
                Vertex((0.0, SCREEN_HALF_H * S82, SCREEN_HALF_H * -C82 + 0.00002),
                       texUV=(0.5 + CELL_U * 0.0, CELL_V * 2.0),
                       maskUV=(CELL_U * 0.0, CELL_V * 1.0)),
                # ^->  2
                Vertex((SCREEN_W, SCREEN_HALF_H * S82, SCREEN_HALF_H * -C82 + 0.00002),
                       texUV=(0.5 + CELL_U * 1.0, CELL_V * 2.0),
                       maskUV=(CELL_U * 1.0, CELL_V * 1.0)),
                # v->  3
                Vertex((SCREEN_W, -SCREEN_HALF_H * S82, -SCREEN_HALF_H * -C82 + 0.00002),
                       texUV=(0.5 + CELL_U * 1.0, CELL_V * 1.0),
                       maskUV=(CELL_U * 1.0, CELL_V * 0.0)),

                # monitor
                # v<-  4
                Vertex((0.0, -SCREEN_HALF_H * S82, -SCREEN_HALF_H * -C82 + 0.00001),
                       texUV=(0.5 + CELL_U * 0.0, CELL_V * 0.0),
                       maskUV=(CELL_U * 0.0, CELL_V * 0.0)),
                # ^<-  5
                Vertex((0.0, SCREEN_HALF_H * S82, SCREEN_HALF_H * -C82 + 0.00001),
                       texUV=(0.5 + CELL_U * 0.0, CELL_V * 1.0),
                       maskUV=(CELL_U * 0.0, CELL_V * 1.0)),
                # ^->  6
                Vertex((SCREEN_W, SCREEN_HALF_H * S82, SCREEN_HALF_H * -C82 + 0.00001),
                       texUV=(0.5 + CELL_U * 1.0, CELL_V * 1.0),
                       maskUV=(CELL_U * 1.0, CELL_V * 1.0)),
                # v->  7
                Vertex((SCREEN_W, -SCREEN_HALF_H * S82, -SCREEN_HALF_H * -C82 + 0.00001),
                       texUV=(0.5 + CELL_U * 1.0, CELL_V * 0.0),
                       maskUV=(CELL_U * 1.0, CELL_V * 0.0)),

                # arcade
                # v<-  8
                Vertex((0.0 - BODY_OFF_X,
                        (-BODY_HALF_H - BODY_OFF_Y) * S82,
                        (-BODY_HALF_H - BODY_OFF_Y) * -C82),
                       texUV=(0.0, 0.0),
                       maskUV=(0.0, 0.0)),
                # ^<-  9
                Vertex((0.0 - BODY_OFF_X,
                        (BODY_HALF_H - BODY_OFF_Y) * S82,
                        (BODY_HALF_H - BODY_OFF_Y) * -C82),
                       texUV=(0.0, 1.0),
                       maskUV=(0.0, 1.0)),
                # ^->  10
                Vertex((BODY_W - BODY_OFF_X,
                        (BODY_HALF_H - BODY_OFF_Y) * S82,
                        (BODY_HALF_H - BODY_OFF_Y) * -C82),
                       texUV=(0.5, 1.0),
                       maskUV=(1.0, 1.0)),
                # v->  11
                Vertex((BODY_W - BODY_OFF_X,
                        (-BODY_HALF_H - BODY_OFF_Y) * S82,
                        (-BODY_HALF_H - BODY_OFF_Y) * -C82),
                       texUV=(0.5, 0.0),
                       maskUV=(1.0, 0.0)),

                # left wall - right side
                # vfront  12
                Vertex((0.0 - BODY_OFF_X,
                        (-BODY_HALF_H - BODY_OFF_Y) * S82,
                        (BODY_HALF_H + BODY_OFF_Y) * C82 + 0.05),
                       texUV=(WALL_U0 + WALL_DU, 0.0),
                       maskUV=(1.0, 0.0)),
                # ^front  13
                Vertex((0.0 - BODY_OFF_X,
                        (BODY_HALF_H - BODY_OFF_Y) * S82,
                        (BODY_HALF_H + BODY_OFF_Y) * C82 + 0.05 + 0.15),
                       texUV=(WALL_U0 + WALL_DU, WALL_DV),
                       maskUV=(1.0, 1.0)),
                # ^back  14
                Vertex((0.0 - BODY_OFF_X,
                        (BODY_HALF_H - BODY_OFF_Y) * S82,
                        (BODY_HALF_H - BODY_OFF_Y) * -C82),
                       texUV=(WALL_U0, WALL_DV),
                       maskUV=(0.0, 1.0)),
                # vback  15
                Vertex((0.0 - BODY_OFF_X,
                        (-BODY_HALF_H - BODY_OFF_Y) * S82,
                        (BODY_HALF_H + BODY_OFF_Y) * C82),
                       texUV=(WALL_U0, 0.0),
                       maskUV=(0.0, 0.0)),

                # left wall - front side
                # ^  16
                Vertex((0.0 - BODY_OFF_X - WALL_T,
                        (BODY_HALF_H - BODY_OFF_Y) * S82,
                        (BODY_HALF_H + BODY_OFF_Y) * C82 + 0.05 + 0.15),
                       texUV=(WALL_U0 + WALL_DU * 2.0, WALL_DV),
                       maskUV=(0.0, 1.0)),
                # v  17
                Vertex((0.0 - BODY_OFF_X - WALL_T,
                        (-BODY_HALF_H - BODY_OFF_Y) * S82,
                        (BODY_HALF_H + BODY_OFF_Y) * C82 + 0.05),
                       texUV=(WALL_U0 + WALL_DU * 2.0, 0.0),
                       maskUV=(0.0, 0.0)),

                # left wall - left side
                # v  18
                Vertex((0.0 - BODY_OFF_X - WALL_T,
                        (-BODY_HALF_H - BODY_OFF_Y) * S82,
                        (BODY_HALF_H + BODY_OFF_Y) * C82 + 0.05 - 1.0),
                       texUV=(WALL_U0 + WALL_DU * 3.0, 0.0),
                       maskUV=(1.0, 0.0)),
                # ^  19
                Vertex((0.0 - BODY_OFF_X - WALL_T,
                        (BODY_HALF_H - BODY_OFF_Y) * S82,
                        (BODY_HALF_H + BODY_OFF_Y) * C82 + 0.05 - 1.0),
                       texUV=(WALL_U0 + WALL_DU * 3.0, WALL_DV),
                       maskUV=(1.0, 1.0)),

                # right wall - left side
                # vfront  20
                Vertex((BODY_W - BODY_OFF_X,
                        (-BODY_HALF_H - BODY_OFF_Y) * S82,
                        (BODY_HALF_H + BODY_OFF_Y) * C82 + 0.05),
                       texUV=(WALL_U0 + WALL_DU, 0.0),
                       maskUV=(1.0, 0.0)),
                # ^front  21
                Vertex((BODY_W - BODY_OFF_X,
                        (BODY_HALF_H - BODY_OFF_Y) * S82,
                        (BODY_HALF_H + BODY_OFF_Y) * C82 + 0.05 + 0.15),
                       texUV=(WALL_U0 + WALL_DU, WALL_DV),
                       maskUV=(1.0, 1.0)),
                # ^back  22
                Vertex((BODY_W - BODY_OFF_X,
                        (BODY_HALF_H - BODY_OFF_Y) * S82,
                        (BODY_HALF_H - BODY_OFF_Y) * -C82),
                       texUV=(WALL_U0, WALL_DV),
                       maskUV=(0.0, 1.0)),
                # vback  23
                Vertex((BODY_W - BODY_OFF_X,
                        (-BODY_HALF_H - BODY_OFF_Y) * S82,
                        (BODY_HALF_H + BODY_OFF_Y) * C82),
                       texUV=(WALL_U0, 0.0),
                       maskUV=(0.0, 0.0)),

                # right wall - front side
                # ^  24    (0.157 here, 0.15 on the left wall: as in the original)
                Vertex((BODY_W - BODY_OFF_X + WALL_T,
                        (BODY_HALF_H - BODY_OFF_Y) * S82,
                        (BODY_HALF_H + BODY_OFF_Y) * C82 + 0.05 + 0.157),
                       texUV=(WALL_U0 + WALL_DU * 2.0, WALL_DV),
                       maskUV=(0.0, 1.0)),
                # v  25
                Vertex((BODY_W - BODY_OFF_X + WALL_T,
                        (-BODY_HALF_H - BODY_OFF_Y) * S82,
                        (BODY_HALF_H + BODY_OFF_Y) * C82 + 0.05),
                       texUV=(WALL_U0 + WALL_DU * 2.0, 0.0),
                       maskUV=(0.0, 0.0)),

                # right wall - right side
                # v  26
                Vertex((BODY_W - BODY_OFF_X + WALL_T,
                        (-BODY_HALF_H - BODY_OFF_Y) * S82,
                        (BODY_HALF_H + BODY_OFF_Y) * C82 + 0.05 - 1.0),
                       texUV=(WALL_U0 + WALL_DU * 3.0, 0.0),
                       maskUV=(1.0, 0.0)),
                # ^  27
                Vertex((BODY_W - BODY_OFF_X + WALL_T,
                        (BODY_HALF_H - BODY_OFF_Y) * S82,
                        (BODY_HALF_H + BODY_OFF_Y) * C82 + 0.05 - 1.0),
                       texUV=(WALL_U0 + WALL_DU * 3.0, WALL_DV),
                       maskUV=(1.0, 1.0)),

                # bottom celling
                # ^->  28   (copy of 10, unused by the index list)
                Vertex((BODY_W - BODY_OFF_X,
                        (BODY_HALF_H - BODY_OFF_Y) * S82,
                        (BODY_HALF_H - BODY_OFF_Y) * -C82),
                       texUV=(0.5, 1.0),
                       maskUV=(1.0, 1.0)),
                # v->  29   (copy of 11, unused by the index list)
                Vertex((BODY_W - BODY_OFF_X,
                        (-BODY_HALF_H - BODY_OFF_Y) * S82,
                        (-BODY_HALF_H - BODY_OFF_Y) * -C82),
                       texUV=(0.5, 0.0),
                       maskUV=(1.0, 0.0)),
            ]

            indices_arcade = np.array([
                9, 8, 10,       # arcade machine
                11, 10, 8,
                5, 4, 6,        # monitor
                7, 6, 4,
                1, 0, 2,        # ui
                3, 2, 0,
                13, 12, 14,     # left wall (right side)
                15, 14, 12,
                12, 13, 16,     # left wall (front side)
                17, 12, 16,
                17, 16, 18,     # left wall (left side)
                19, 18, 16,

                20, 21, 22,     # right wall (left side)
                22, 23, 20,
                21, 20, 24,     # right wall (front side)
                20, 25, 24,
                24, 25, 26,     # right wall (right side)
                26, 27, 24,
            ], dtype=np.uint32)

            # ---------------------------------------------------------------
            # portal
            # ---------------------------------------------------------------
            # Flat quad. texUV samples the portal art, maskUV lands on row 5 of
            # the spawn spritesheet -- the animation slides it with an offset.
            vertices_portal = [
                # v<-
                Vertex((0.0, -SCREEN_HALF_H, 0.0),
                       texUV=(PORTAL_TEX_U * 0.0, 1.0 * 0.0),
                       maskUV=(PORTAL_MASK_U * 0.0, PORTAL_MASK_V * 5.0)),
                # ^<-
                Vertex((0.0, SCREEN_HALF_H, 0.0),
                       texUV=(PORTAL_TEX_U * 0.0, 1.0 * 1.0),
                       maskUV=(PORTAL_MASK_U * 0.0, PORTAL_MASK_V * 6.0)),
                # ^->
                Vertex((SCREEN_W, SCREEN_HALF_H, 0.0),
                       texUV=(PORTAL_TEX_U * 1.0, 1.0 * 1.0),
                       maskUV=(PORTAL_MASK_U * 1.0, PORTAL_MASK_V * 6.0)),
                # v->
                Vertex((SCREEN_W, -SCREEN_HALF_H, 0.0),
                       texUV=(PORTAL_TEX_U * 1.0, 1.0 * 0.0),
                       maskUV=(PORTAL_MASK_U * 1.0, PORTAL_MASK_V * 5.0)),
            ]

            indices_portal = np.array([
                1, 0, 2,
                3, 2, 0,
            ], dtype=np.uint32)

            # ---------------------------------------------------------------
            # brick unit
            # ---------------------------------------------------------------
            # 8 vertices, drawn as a closed box. The front face is wound in the
            # opposite order to the back face, hence the odd index list below.
            # texUV is in bank pixels, not normalised: (u, v, bank) addresses
            # pyxel.images[bank] directly. The skin cell is the first swatch of
            # the strip along the bottom of bank1.png, which loads into bank 0.
            BRICKUNIT_U_START = 0
            BRICKUNIT_V_START = 192
            BRICKUNIT_PX_STRIDE = 30
            BRICKUNIT_BANK = 0

            # Cell edges. pyxel's origin is top-left with y growing downwards,
            # the opposite of the v axis these UVs used to be written against,
            # so the cube's *top* vertices take the *smaller* y.
            u_left = BRICKUNIT_U_START
            u_right = BRICKUNIT_U_START + BRICKUNIT_PX_STRIDE
            v_top = BRICKUNIT_V_START
            v_bottom = BRICKUNIT_V_START + BRICKUNIT_PX_STRIDE

            # maskUV still holds normalised coordinates: the brick unit's mask
            # is no-specular.png, which is not in a bank yet.
            vertices_brick_unit = [
                # back
                # v<-  0
                Vertex((0.0, -BRICK_HALF_H, 0.0),
                       texUV=(u_left, v_bottom, BRICKUNIT_BANK),
                       maskUV=(CELL_U * 0.0, CELL_V * 0.0)),
                # ^<-  1
                Vertex((0.0, BRICK_HALF_H, 0.0),
                       texUV=(u_left, v_top, BRICKUNIT_BANK),
                       maskUV=(CELL_U * 0.0, CELL_V * 1.0)),
                # ^->  2
                Vertex((BRICK_SIDE, BRICK_HALF_H, 0.0),
                       texUV=(u_right, v_top, BRICKUNIT_BANK),
                       maskUV=(CELL_U * 1.0, CELL_V * 1.0)),
                # v->  3
                Vertex((BRICK_SIDE, -BRICK_HALF_H, 0.0),
                       texUV=(u_right, v_bottom, BRICKUNIT_BANK),
                       maskUV=(CELL_U * 1.0, CELL_V * 0.0)),

                # front
                # ^<-  4
                Vertex((0.0, BRICK_HALF_H, BRICK_SIDE),
                       texUV=(u_left, v_bottom, BRICKUNIT_BANK),
                       maskUV=(CELL_U * 0.0, CELL_V * 0.0)),
                # ^->  5
                Vertex((BRICK_SIDE, BRICK_HALF_H, BRICK_SIDE),
                       texUV=(u_left, v_top, BRICKUNIT_BANK),
                       maskUV=(CELL_U * 0.0, CELL_V * 1.0)),
                # v->  6
                Vertex((BRICK_SIDE, -BRICK_HALF_H, BRICK_SIDE),
                       texUV=(u_right, v_top, BRICKUNIT_BANK),
                       maskUV=(CELL_U * 1.0, CELL_V * 1.0)),
                # v<-  7
                Vertex((0.0, -BRICK_HALF_H, BRICK_SIDE),
                       texUV=(u_right, v_bottom, BRICKUNIT_BANK),
                       maskUV=(CELL_U * 1.0, CELL_V * 0.0)),
            ]

            indices_brick_unit = np.array([
                0, 1, 2, 2, 3, 0,     # back
                6, 4, 7, 4, 6, 5,     # front
                1, 0, 7, 4, 1, 7,     # left
                2, 5, 3, 3, 5, 6,     # right
                0, 3, 6, 0, 6, 7,     # bottom
                2, 1, 4, 5, 2, 4,     # top
            ], dtype=np.uint32)

            # ---------------------------------------------------------------
            # cube (debug mesh, not part of the original game)
            # ---------------------------------------------------------------
            pos_cube = np.array([
                # back face (z = -0.5)
                [-0.5, -0.5, -0.5],   # 4  bottom-left
                [-0.5,  0.5, -0.5],   # 7  top-left
                [ 0.5,  0.5, -0.5],   # 6  top-right
                [ 0.5, -0.5, -0.5],   # 5  bottom-right
                # front face (z = +0.5)
                [-0.5,  0.5,  0.5],   # 3  top-left
                [ 0.5,  0.5,  0.5],   # 2  top-right
                [ 0.5, -0.5,  0.5],   # 1  bottom-right
                [-0.5, -0.5,  0.5],   # 0  bottom-left

            ], dtype=np.float32)

            texUV_cube = np.array([
              # back face (z = +0.5)
              [ u_left, v_bottom, BRICKUNIT_BANK ],   # 0  bottom-left
              [ u_left, v_top, BRICKUNIT_BANK ],   # 3  top-left
              [ u_right, v_top, BRICKUNIT_BANK ],   # 2  top-right
              [ u_right, v_bottom, BRICKUNIT_BANK ],   # 1  bottom-right
              # front face (z = -0.5)
              [ u_left, v_bottom, BRICKUNIT_BANK ],   # 0  bottom-left
              [ u_left, v_top, BRICKUNIT_BANK ],   # 3  top-left
              [ u_right, v_top, BRICKUNIT_BANK ],   # 2  top-right
              [ u_right, v_bottom, BRICKUNIT_BANK ],   # 1  bottom-right
              ], dtype=np.float32)

            vertices_cube = [ Vertex(pos, texUV=texuv) for pos, texuv in zip(pos_cube,texUV_cube) ]

            # 12 triangles, CCW seen from outside
            indices_cube = np.array([
                0, 1, 2, 2, 3, 0,     # back
                6, 4, 7, 4, 6, 5,     # front
                1, 0, 7, 4, 1, 7,     # left
                2, 5, 3, 3, 5, 6,     # right
                0, 3, 6, 0, 6, 7,     # bottom
                2, 1, 4, 5, 2, 4,     # top
            ], dtype=np.uint32)

            mesh_arcade = Mesh(vertices_arcade, indices_arcade)
            mesh_portal = Mesh(vertices_portal, indices_portal)
            mesh_brick_unit = Mesh(vertices_brick_unit, indices_brick_unit)
            mesh_cube = Mesh(vertices_cube, indices_cube)

            # Same calls, same order as Resources.cpp. Note glm::translate and
            # friends post-multiply (model = model * T) while Mesh here
            # pre-multiplies (model = T @ model), so the portal -- the only mesh
            # with more than one transform -- does not land where it does in the
            # C++ build until one of the two sides is flipped.
            mesh_arcade.translate_model((-0.775, 0.0, 0.0))

            mesh_portal.rotate_model((1.0, 0.0, 0.0), -5.0)
            mesh_portal.rotate_model((0.0, 1.0, 0.0), -15.0)
            mesh_portal.translate_model((-0.16, 0.0, 0.0))
            mesh_portal.scale_model((0.8, 0.8, 0.8))

            mesh_brick_unit.rotate_model((1.0, 0.0, 0.0), -8.0)
            # mesh_brick_unit.translate_model((0.543548387096774 - 0.775,
                                            #  -0.336816396484375,
                                            #  0.00003))

            self.verts.append(vertices_arcade)
            self.verts.append(vertices_portal)
            self.verts.append(vertices_brick_unit)
            self.verts.append(vertices_cube)

            self.indices.append(indices_arcade)
            self.indices.append(indices_portal)
            self.indices.append(indices_brick_unit)
            self.indices.append(indices_cube)

            # meshs[0..2] keep the indices the original game code uses
            # (arcade, portal, brick unit); the debug cube trails at the end.
            self.meshs.append(mesh_arcade)
            self.meshs.append(mesh_portal)
            self.meshs.append(mesh_brick_unit)
            self.meshs.append(mesh_cube)

            self.meshs[2].scale_model((10,10,10))

            # Textures each mesh samples, for when the fragment shader needs
            # them (assets/textures/):
            #   arcade      tex arcade.png            mask no-specular.png
            #   portal      tex arcade-monitor.png    mask enemy-portal-spawn-anim.png
            #   brick unit  tex brick-unit-skins.png  mask no-specular.png


        def load(self):
            pass

