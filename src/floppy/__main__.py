import os
import sys
import time

import numpy as np
import pyxel

from game.play import HACKS, TREE, TREE_INFO, Keys, Run
from game.rules import NULL, score_gauge
from renderer.batch import Batch, Rasterizer
from renderer.math3d import create_proj_matrix, look_from_to
import scene

W, H = 320, 240
FPS = 30
FOV = 50.0
BACKGROUND = 0
WALK_SPEED, TURN_SPEED = 1.6, 110.0
SIT_TIME = 0.35

ASSETS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "textures")

PLAY_KEYS = {
    pyxel.KEY_D: "CW", pyxel.KEY_C: "CCW", pyxel.KEY_A: "180",
    pyxel.KEY_I: "SD", pyxel.KEY_S: "HD", pyxel.KEY_K: "HOLD", pyxel.KEY_U: "HOLD2",
}


class App:
    def __init__(self, save_path):
        pyxel.init(W, H, title="floppy", fps=FPS)

        # load art with 16 cols, ramps after
        pyxel.colors[:] = scene.ART_PALETTE
        pyxel.images[0].load(0, 0, os.path.join(ASSETS, "bank1.png"))
        # clean copy for paint_stats
        pyxel.images[1].load(0, 0, os.path.join(ASSETS, "bank1.png"))
        pyxel.colors[:] = scene.palette()

        screen = np.ctypeslib.as_array(pyxel.screen.data_ptr(), shape=(H * W,)).reshape(H, W)
        texture = np.ctypeslib.as_array(pyxel.images[0].data_ptr(), shape=(256 * 256,)).reshape(256, 256)
        self.raster = Rasterizer(screen, texture)

        self.room = scene.build_room()
        self.monitor = scene.screen_quad()

        self.run = Run(save_path)
        self.keys = Keys()
        self.menu = None
        self.menu_pick = 0
        self.reset_armed = False

        self.pos = np.array([0.2, 1.6, 2.6], np.float32)
        self.yaw = -90.0
        self.seated = False
        self.sit_t = 0.0

        self.last = time.perf_counter()
        self.fps = 0.0
        pyxel.run(self.update, self.draw)

    def update(self):
        now = time.perf_counter()
        dt = min(0.1, now - self.last)
        self.last = now
        self.fps = self.fps * 0.9 + (1.0 / max(dt, 1e-3)) * 0.1

        run = self.run
        if run.phase == "reward":
            self.update_reward()
            return
        if pyxel.btnp(pyxel.KEY_TAB):
            self.menu = None if self.menu else "tree"
            self.menu_pick = 0
            self.reset_armed = False
        if self.menu:
            self.update_tree()
            return

        if pyxel.btnp(pyxel.KEY_RETURN):
            if self.seated:
                self.seated = False
            elif np.linalg.norm((self.pos - scene.SEAT)[[0, 2]]) < 1.6:
                self.seated = True
        self.sit_t = min(1.0, self.sit_t + dt / SIT_TIME) if self.seated else max(0.0, self.sit_t - dt / SIT_TIME)

        if not self.seated:
            self.walk(dt)
            return
        if self.sit_t < 1.0:
            return

        moves = self.keys.moves(pyxel.btn(pyxel.KEY_J), pyxel.btn(pyxel.KEY_L), dt)
        fighter = run.player
        for key, move in PLAY_KEYS.items():
            if not pyxel.btnp(key):
                continue
            if move == "HD" and fighter.since_spawn < 0.1:
                continue
            if move.startswith("HOLD") and fighter.grid.hold_slots < (2 if move == "HOLD2" else 1):
                continue
            moves.append(move)
        fighter.gravity = 0.02 if pyxel.btn(pyxel.KEY_B) else 1.0
        run.update(dt, moves)

    def walk(self, dt):
        turn = pyxel.btn(pyxel.KEY_RIGHT) - pyxel.btn(pyxel.KEY_LEFT)
        step = pyxel.btn(pyxel.KEY_UP) - pyxel.btn(pyxel.KEY_DOWN)
        self.yaw += turn * TURN_SPEED * dt
        rad = np.deg2rad(self.yaw)
        nxt = self.pos + np.array([np.cos(rad), 0.0, np.sin(rad)], np.float32) * step * WALK_SPEED * dt
        x0, x1, z0, z1, _ = scene.ROOM
        nxt[0] = np.clip(nxt[0], x0 + 0.3, x1 - 0.3)
        nxt[2] = np.clip(nxt[2], z0 + 0.3, z1 - 0.3)
        if -0.75 < nxt[0] < 1.15 and nxt[2] < 0.85:
            return
        self.pos = nxt

    def update_tree(self):
        tree = self.run.tree
        if pyxel.btnp(pyxel.KEY_UP):
            self.menu_pick = (self.menu_pick - 1) % (len(TREE) - 1)
        if pyxel.btnp(pyxel.KEY_DOWN):
            self.menu_pick = (self.menu_pick + 1) % (len(TREE) - 1)
        key = TREE[1 + self.menu_pick][0]
        if pyxel.btnp(pyxel.KEY_RETURN) and tree.can_buy(key):
            tree.buy(key)
            self.run.apply_tree()
            self.run.save()
        if pyxel.btnp(pyxel.KEY_R):
            if self.reset_armed:
                tree.reset()
                self.run.player.grid.fully_random = True
                self.run.apply_tree()
                self.run.save()
            self.reset_armed = not self.reset_armed

    def update_reward(self):
        reward = self.run.reward
        if pyxel.btnp(pyxel.KEY_LEFT):
            reward["pick"] = (reward["pick"] - 1) % 4
        if pyxel.btnp(pyxel.KEY_RIGHT):
            reward["pick"] = (reward["pick"] + 1) % 4
        if pyxel.btnp(pyxel.KEY_RETURN):
            pick = reward["pick"]
            self.run.take_reward(reward["choices"][pick] if pick < 3 else None)

    def camera(self):
        rad = np.deg2rad(self.yaw)
        walk_look = self.pos + np.array([np.cos(rad), 0.0, np.sin(rad)], np.float32)
        t = self.sit_t * self.sit_t * (3 - 2 * self.sit_t)
        eye = self.pos * (1 - t) + scene.SEAT * t
        look = walk_look * (1 - t) + scene.SEAT_LOOK * t
        view = look_from_to(position=eye, looking_to=look, up_direction=np.array([0.0, 1.0, 0.0]))
        return create_proj_matrix(FOV, W / H, 0.05, 30.0) @ view

    def draw(self):
        run = self.run
        magic = run.discovered
        self.paint_stats()

        batch = Batch()
        batch.add_flat(*self.room)
        batch.add_textured(*self.monitor)
        batch.add_flat(*scene.drives_mesh(run.drives, run.disks))

        boards = scene.BoardDraw()
        s = scene.CABINET_SCREEN
        boards.grid(s, run.player, magic)
        g = run.player.grid
        boards.preview(s, g.next[0], scene.NEXT_BOX, scene.CELL * 0.9, magic)
        for i in range(1, g.visible_next):
            boards.preview(s, g.next[i], (206, 104 + i * 13, 242, 116 + i * 13), 4.5, magic)
        if g.hold_slots and g.hold[0] != NULL:
            boards.preview(s, g.hold[0], scene.HOLD_BOX, scene.CELL * 0.9, magic)
        if g.hold_slots > 1 and g.hold[1] != NULL:
            boards.preview(s, g.hold[1], (81, 74, 117, 96), 5.0, magic)

        if run.ai and run.phase == "combat":
            batch.add_flat(*scene.portal_backing(run.ai.grid.rows))
            boards.grid(scene.PORTAL_SCREEN, run.ai, magic, show_side=False)
        tris, cols = boards.build()
        if len(tris):
            batch.add_flat(tris, cols)

        self.raster.draw(batch, self.camera(), BACKGROUND)
        self.draw_hud()

    def paint_stats(self):
        img = pyxel.images[0]
        img.blt(18, 64, 1, 18, 64, 53, 112)
        run, g = self.run, self.run.player.grid
        lines = [f"ENEMY {run.enemy}" if run.discovered else "INSERT", "", f"PTS {run.tree.points}",
                 f"DRIVES {run.drives}", f"NEXT {g.visible_next}", f"ROWS {g.visible_rows}"]
        for i, text in enumerate(lines):
            img.text(20, 66 + i * 7, text, 7)
        if run.ai and run.phase == "combat":
            gauge = g.gauge
            img.text(20, 150, f"IN {g.incoming_lines()}", 10)
            if gauge.open:
                img.text(20, 158, f"{gauge.base}X{gauge.hand:.1f}", 9)

    def draw_hud(self):
        run = self.run
        pyxel.text(4, 4, f"{self.fps:4.1f} FPS", 3)
        if run.message_time > 0:
            pyxel.text(W // 2 - len(run.message) * 2, 14, run.message, 9)

        if not self.seated:
            near = np.linalg.norm((self.pos - scene.SEAT)[[0, 2]]) < 1.6
            pyxel.text(4, H - 10, "ENTER: SIT" if near else "ARROWS: WALK   TAB: MAGIC", 3)

        if run.discovered and run.phase == "combat" and self.seated:
            self.draw_gauge()

        if self.menu == "tree":
            self.draw_tree()
        if run.phase == "reward":
            self.draw_reward()

    def draw_gauge(self):
        run = self.run
        g = run.player.grid
        gauge = g.gauge
        x, y = 4, H - 34
        if gauge.open:
            base, mult, out = score_gauge(gauge, g.streaks, g.board, run.disks)
            left = 1.0 - gauge.time / gauge.length
            pyxel.rect(x, y, 80, 3, 13)
            pyxel.rect(x, y, int(80 * left), 3, 7)
            pyxel.text(x, y + 6, f"{base} X {mult:.2f} = {out}", 3)
            pyxel.text(x, y + 14, gauge.hand_name[:28], 6)
        pyxel.text(W - 92, H - 18, f"{run.foe['profile']} {run.foe['delay']:.2f}s", 12)
        incoming = g.incoming_lines()
        if incoming:
            pyxel.text(W - 92, H - 10, f"INCOMING {incoming}", 10)
        for i, disk in enumerate(run.disks):
            pyxel.text(W - 60, 4 + i * 8, disk, scene.color(scene.DISK + HACKS[disk][0], 3))

    def draw_tree(self):
        tree = self.run.tree
        pyxel.rect(20, 20, W - 40, H - 40, 0)
        pyxel.rectb(20, 20, W - 40, H - 40, 7)
        pyxel.text(28, 26, f"MAGIC   POINTS {tree.points}", 7)
        for i, (key, name, parent, costs) in enumerate(TREE[1:]):
            y = 42 + i * 16
            level = tree.levels[key]
            locked = tree.levels[parent] == 0
            col = 13 if locked else (3 if tree.can_buy(key) else 2)
            mark = ">" if i == self.menu_pick else " "
            cost = tree.cost(key)
            status = "MAXED" if cost is None else (f"LOCKED" if locked else f"COST {cost}")
            pyxel.text(28, y, f"{mark} {name}  {level}/{len(costs)}  {status}", col)
            if i == self.menu_pick:
                pyxel.text(40, y + 7, TREE_INFO[key], 6)
        pyxel.text(28, H - 30, "UP/DOWN  ENTER: BUY  R: RESET  TAB: CLOSE", 2)
        if self.reset_armed:
            pyxel.text(28, H - 38, "R AGAIN TO CONFIRM THE RESET", 10)

    def draw_reward(self):
        run = self.run
        reward = run.reward
        pyxel.rect(20, 50, W - 40, 110, 0)
        pyxel.rectb(20, 50, W - 40, 110, 7)
        pyxel.text(28, 56, f"ENEMY DOWN  +{run.enemy - 1} POINTS. TAKE A DISK", 9)
        if not run.drives:
            pyxel.text(28, 66, "NO DRIVES YET: BUY FLOPPY DRIVES (TAB)", 10)
        elif len(run.disks) >= run.drives:
            pyxel.text(28, 66, f"DRIVES FULL: REPLACES {run.disks[0]}", 10)
        for i, name in enumerate(reward["choices"] + ["SKIP"]):
            x = 28 + i * 68
            col = 3 if i == reward["pick"] else 2
            pyxel.rectb(x - 2, 80, 64, 50, col)
            if name != "SKIP":
                pyxel.rect(x + 2, 84, 10, 10, scene.color(scene.DISK + HACKS[name][0], 3))
            pyxel.text(x, 98, name, col)
            if name != "SKIP":
                words = HACKS[name][1].split()
                for j in range(0, len(words), 3):
                    pyxel.text(x, 106 + j * 2, " ".join(words[j:j + 3]), 6)
        pyxel.text(28, 146, "LEFT/RIGHT  ENTER", 2)


def main() -> None:
    App(sys.argv[1] if len(sys.argv) > 1 else "floppy.save")


if __name__ == "__main__":
    main()
