import numpy as np
import pyxel
from resources import Resources
from renderer.rasterizer import rasterize
from renderer.vertex import proj_triangle, Vertex
from shaders.default_frag import deafult_fragment

W = H = 256
FPS = 60
COLOR = 1
NEAR = 0.1

MOVE_SPEED = 0.02      # world units per frame
ROT_SPEED = 2.0        # degrees per frame


class App:
    def __init__(self):
        pyxel.init(W, H, title="buffer quickstart", fps=FPS)
        pyxel.images[0].load(0, 0, "assets/textures/bank1.png")
        self.tex_buf = np.ctypeslib.as_array(pyxel.images[0].data_ptr()).reshape(256, 256)

        self.res = Resources()

        # pyxel.screen IS the framebuffer. data_ptr() returns a pointer to
        # pyxel's own memory: W*H bytes, one palette index per pixel, row-major.
        # reshape only changes indexing metadata, so buf[y, x] addresses that
        # same memory -- writing to it writes straight into the framebuffer.
        self.buf = np.ctypeslib.as_array(pyxel.screen.data_ptr()).reshape(H, W)
        self.depth_buf = np.zeros((H, W), np.float64)
        self.frame = 0

        # the mesh wasd/qe drive
        self.selected = self.res.meshs[3]

        pyxel.run(self.update, self.draw)

    def update(self):
        self.frame += 1

        # a/d slide along X, w/s along Y (up and down the screen)
        dx = pyxel.btn(pyxel.KEY_D) - pyxel.btn(pyxel.KEY_A)
        dy = pyxel.btn(pyxel.KEY_W) - pyxel.btn(pyxel.KEY_S)

        if dx or dy:
            self.selected.translate_model((-dx * MOVE_SPEED, -dy * MOVE_SPEED, 0.0))

        # q and e spin around Y in opposite directions
        spin = pyxel.btn(pyxel.KEY_Q) - pyxel.btn(pyxel.KEY_E)

        if spin:
            self.selected.rotate_model((0.0, 1.0, 0.0), spin * ROT_SPEED)

    def draw(self):
        self.buf[:] = COLOR
        self.depth_buf[:] = 0.0

        triangle_color = 2
        arcade = self.res.meshs[0]
        brickunit = self.res.meshs[2]
        cube = self.res.meshs[3]

        meshes_to_draw = (cube, arcade)

        self.res.camera.updateMatrix(W, H)
        PV = self.res.camera.get_camera_matrix()

        for mesh in meshes_to_draw:
            for i in range(mesh.get_triangle_amount()):
                V0 = mesh.get_V(mesh.get_idx(3*i))
                V1 = mesh.get_V(mesh.get_idx(3*i + 1))
                V2 = mesh.get_V(mesh.get_idx(3*i + 2))

                
                A = Vertex(V0.position, V0.texUV, V0.maskUV, V0.normal)
                B = Vertex(V1.position, V1.texUV, V1.maskUV, V1.normal)
                C = Vertex(V2.position, V2.texUV, V2.maskUV, V2.normal)

                proj_triangle(A, B, C, mesh.get_model(), PV, W, H)

                if A.position[3] <= NEAR or B.position[3] <= NEAR or C.position[3] <= NEAR:
                    triangle_color += 1
                    continue
                
                result = rasterize(A.position, B.position, C.position, W, H)

                if result is None:
                    triangle_color += 1
                    continue

                c0s, c1s, c2s, depth_buffer, x_min, y_min, x_max, y_max = result

                mask = (c0s >= 0) & (c1s >= 0) & (c2s >= 0)

                depth_slice = self.depth_buf[y_min : y_max + 1, x_min : x_max + 1]

                visible = mask & (depth_buffer > depth_slice)

                np.putmask(depth_slice, visible, depth_buffer)
                # np.putmask(self.buf[y_min : y_max + 1, x_min : x_max + 1],
                        # visible, np.uint8(triangle_color % 16))

                colors = deafult_fragment(A, B, C, c0s, c1s, c2s, visible, self.tex_buf)

                np.putmask(self.buf[y_min : y_max + 1, x_min : x_max + 1],
                        visible, colors)
                
                triangle_color += 1


        pyxel.text(50, 50, f"{self.frame}", 3)

def main() -> None:
    App()

if __name__ == "__main__":
    main()
