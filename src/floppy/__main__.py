import argparse
import os
import time

import numpy as np
import pyxel

from game.play import HACKS, TREE, TREE_INFO, Keys, Run
from game.rules import GARBAGE, HIDDEN_ROWS, NULL, score_gauge
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

# pages: (lines, what ends the page, things to frame)
LESSONS = {
    "intro": [
        (["THE ARCADE WOKE UP: MAGIC IS REAL NOW,",
          "AND AN ENEMY CROSSED OVER TO FIGHT YOU.",
          "THE MATCH IS PAUSED FOR A QUICK TOUR."], "enter", []),
        (["MAGIC POINTS BUY UPGRADES IN THE MAGIC TREE.",
          "EVERY ENEMY YOU BEAT PAYS POINTS. HERE ARE 2",
          "TO START. PRESS TAB TO OPEN THE TREE."], "tab", []),
        (["PICK HOLD AND PRESS ENTER TO BUY IT."], "buy", ["hold_row"]),
        (["BOUGHT. EACH NODE OPENS THE ONES BELOW IT,",
          "AND THE TREE IS KEPT EVEN WHEN YOU LOSE.",
          "PRESS TAB TO CLOSE IT."], "close", []),
        (["HOLD PUTS THE PIECE ASIDE FOR LATER, ONCE PER",
          "PIECE. PRESS K TO HOLD THE CURRENT ONE."], "hold", ["hold_box"]),
        (["THIS IS THE ENEMY GRID. IT PLAYS THE SAME GAME",
          "AGAINST YOU: FILL IT TO THE TOP TO WIN. ITS STYLE",
          "AND MOVE SPEED ARE SHOWN AT THE BOTTOM RIGHT."], "enter", ["portal", "foe"]),
        (["CLEARING LINES ATTACKS. A CLEAR OPENS THE ATTACK",
          "BAR, WHICH HOLDS THE DAMAGE FOR 3 SECONDS. EACH",
          "CLEAR ADDS 1 MORE, UP TO 8. THEN IT FIRES."], "enter", ["gauge"]),
        (["DAMAGE = BASE X MULT. BASE IS THE LINES CLEARED",
          "WHILE THE BAR IS OPEN. MULT IS THE BEST CLEAR",
          "IN IT: QUADS, T-SPINS, COMBOS AND B2B HIT HARD.",
          "SINGLES SEND NOTHING. CHAIN CLEARS FAST!"], "enter", ["gauge"]),
        (["ENEMY ATTACKS QUEUE LEFT OF YOUR WELL. GREY",
          "WAITS, ORANGE IS CLOSE. FLASHING RED LANDS AS",
          "GARBAGE WHEN YOU PLACE A PIECE WITHOUT CLEARING.",
          "YOUR OWN ATTACKS CANCEL IT FIRST."], "enter", ["incoming"]),
        (["LOSING SENDS YOU BACK TO ENEMY 1.",
          "GOOD LUCK!"], "enter", []),
    ],
    "hacks": [
        (["ENEMY DOWN! EVERY WIN PAYS POINTS AND A DISK.",
          "DISKS HOLD HACKS: PROGRAMS THAT BEND THE RULES",
          "FOR YOU, MOSTLY ON THE ATTACK BAR MATH."], "enter", ["choices"]),
        (["A DISK ONLY RUNS IN A FLOPPY DRIVE. HERE IS YOUR",
          "FIRST ONE, FREE. MORE DRIVES ARE IN THE MAGIC TREE.",
          "WHEN ALL DRIVES ARE FULL, A NEW DISK REPLACES",
          "THE OLDEST."], "enter", []),
        (["RUNNING HACKS ARE LISTED AT THE TOP RIGHT.",
          "LOSING A FIGHT ERASES EVERY DISK.",
          "NOW TAKE ONE."], "enter", []),
    ],
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
        if run.lesson:
            self.update_lesson()
            return
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

    def update_lesson(self):
        run = self.run
        _, wait, _ = LESSONS[run.lesson][run.lesson_step]
        done = False
        if wait == "enter":
            done = pyxel.btnp(pyxel.KEY_RETURN)
        elif wait == "tab" and pyxel.btnp(pyxel.KEY_TAB):
            self.menu = "tree"
            self.menu_pick = [k for k, *_ in TREE[1:]].index("hold")
            done = True
        elif wait == "buy":
            self.update_tree(only="hold")
            done = run.tree.levels["hold"] > 0
        elif wait == "close" and pyxel.btnp(pyxel.KEY_TAB):
            self.menu = None
            done = True
        elif wait == "hold" and pyxel.btnp(pyxel.KEY_K):
            run.player.act("HOLD")
            done = True
        if not done:
            return
        run.lesson_step += 1
        if run.lesson_step == len(LESSONS[run.lesson]):
            run.end_lesson()

    def update_tree(self, only=None):
        tree = self.run.tree
        if pyxel.btnp(pyxel.KEY_UP):
            self.menu_pick = (self.menu_pick - 1) % (len(TREE) - 1)
        if pyxel.btnp(pyxel.KEY_DOWN):
            self.menu_pick = (self.menu_pick + 1) % (len(TREE) - 1)
        key = TREE[1 + self.menu_pick][0]
        if pyxel.btnp(pyxel.KEY_RETURN) and tree.can_buy(key) and only in (None, key):
            tree.buy(key)
            self.run.apply_tree()
            self.run.save()
        if pyxel.btnp(pyxel.KEY_R) and only is None:
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

        self.pv = self.camera()
        self.raster.draw(batch, self.pv, BACKGROUND)
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
        if run.lesson:
            self.draw_lesson()

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
        for i, disk in enumerate(run.disks):
            pyxel.text(W - 60, 4 + i * 8, disk, scene.color(scene.DISK + HACKS[disk][0], 3))

    def draw_lesson(self):
        run = self.run
        text, wait, spots = LESSONS[run.lesson][run.lesson_step]
        if "gauge" in spots and not run.player.grid.gauge.open:
            # sample bar, the real one is closed while paused
            x, y = 4, H - 34
            pyxel.rect(x, y, 80, 3, 13)
            pyxel.rect(x, y, 48, 3, 7)
            pyxel.text(x, y + 6, "4 X 1.00 = 4", 3)
            pyxel.text(x, y + 14, "QUAD", 6)
        rects = [self.spot(name) for name in spots]
        if "incoming" in spots and not run.player.grid.incoming:
            # sample queue: waiting, close, landing
            x0, _, x1, y1 = rects[0]
            for i, col in enumerate((scene.color(GARBAGE, 2), scene.color(5, 3), scene.color(3, 3))):
                pyxel.rect(x0 + 1, y1 - 7 * (i + 1) - 4 * i, x1 - x0 - 1, 6 + 4 * i, col)
        if pyxel.frame_count // 8 % 2 == 0:
            for x0, y0, x1, y1 in rects:
                pyxel.rectb(x0 - 2, y0 - 2, x1 - x0 + 4, y1 - y0 + 4, 9)

        prompt = {"enter": "ENTER", "tab": "TAB", "buy": "ENTER", "close": "TAB", "hold": "K"}[wait]
        h = 16 + len(text) * 8
        # top unless it hides what it points at
        top = 24
        if self.menu or run.phase == "reward" or any(y0 - 2 < top + h for _, y0, _, _ in rects):
            top = H - h - 4
        pyxel.rect(16, top, W - 32, h, 0)
        pyxel.rectb(16, top, W - 32, h, 9)
        for i, line in enumerate(text):
            pyxel.text(22, top + 5 + i * 8, line, 7)
        step = f"{run.lesson_step + 1}/{len(LESSONS[run.lesson])}"
        pyxel.text(22, top + h - 9, step, 13)
        pyxel.text(W - 22 - len(prompt) * 4, top + h - 9, prompt, 9 if pyxel.frame_count // 15 % 2 else 3)

    def spot(self, name):
        run = self.run
        rows = run.player.grid.rows
        art = scene.CABINET_SCREEN
        if name == "hold_box":
            return self.frame(art, *scene.HOLD_BOX)
        if name == "incoming":
            top = scene.WELL_V - (rows - HIDDEN_ROWS) * scene.CELL
            return self.frame(art, scene.WELL_U - 6, top, scene.WELL_U - 1.5, scene.WELL_V)
        if name == "portal":
            top = scene.WELL_V - (run.ai.grid.rows - HIDDEN_ROWS) * scene.CELL
            return self.frame(scene.PORTAL_SCREEN, scene.WELL_U - 10, top - 6,
                              scene.WELL_U + 10 * scene.CELL + 6, scene.WELL_V + 6)
        return {
            "hold_row": (26, 56, W - 28, 70),
            "foe": (W - 92, H - 18, W - 4, H - 12),
            "gauge": (4, H - 34, 84, H - 14),
            "choices": (26, 80, 26 + 3 * 68 - 4, 130),
        }[name]

    def frame(self, s, u0, v0, u1, v1):
        # art rect on a 3d screen -> pixel box
        pts = np.array([s.at(u, v) for u in (u0, u1) for v in (v0, v1)], np.float32)
        clip = np.c_[pts, np.ones(4, np.float32)] @ self.pv.T
        x = (clip[:, 0] / clip[:, 3] * 0.5 + 0.5) * W
        y = (0.5 - clip[:, 1] / clip[:, 3] * 0.5) * H
        return int(x.min()), int(y.min()), int(x.max()), int(y.max())

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
    parser = argparse.ArgumentParser(prog="floppy")
    parser.add_argument("save", nargs="?", default="floppy.save")
    parser.add_argument("--no-lighting", action="store_true", help="draw the room unlit, full bright")
    args = parser.parse_args()
    scene.LIGHTING = not args.no_lighting
    App(args.save)


if __name__ == "__main__":
    main()
