import random

from game.ai import PROFILES, AIPlayer
from game.rules import I, NULL, SPIN_NONE, Grid

HACKS = {
    "PLAIN.DSK": (0, "+0.25 mult"),
    "QUADRO": (1, "+0.5 mult if the window has a quad"),
    "SPINLOCK": (2, "+0.75 mult if the window has a T-spin"),
    "COMBO.SYS": (3, "+1 base per clear after the first"),
    "SINGLES.BAT": (4, "clears that send nothing still feed"),
    "B2B.CHAIN": (5, "+0.1 mult per B2B level"),
    "LOWRIDER": (6, "+3 base if the stack is 4 rows or less"),
    "OVERCLOCK": (7, "x1.25 mult with 3+ clears"),
}

TREE = [
    ("discoveringMagic", "DISCOVERING MAGIC", None, [0]),
    ("enhancedNext", "ENHANCED NEXT", "discoveringMagic", [1, 2, 3, 4, 5]),
    ("hold", "HOLD", "discoveringMagic", [2, 4]),
    ("floppyDrives", "FLOPPY DRIVES", "discoveringMagic", [2, 3, 4, 5, 6]),
    ("bagRandomizer", "7-BAG", "enhancedNext", [3]),
    ("tallerWell", "TALLER WELL", "hold", [2, 3, 4, 5, 6, 7]),
]
TREE_INFO = {
    "discoveringMagic": "the root, owned from the start",
    "enhancedNext": "one more next piece per level",
    "hold": "lv1 opens hold, lv2 a second one (U)",
    "floppyDrives": "one more drive per level",
    "bagRandomizer": "pieces come from a 7-bag",
    "tallerWell": "two more rows per level",
}

GRAVITY, SOFT_GRAVITY = 1.0, 0.02
LOCK_DELAY, MAX_RESETS = 1.0, 15
DAS, ARR, HARD_DROP_GUARD = 0.15, 0.03, 0.1


class Fighter:
    def __init__(self, grid, hacks=None):
        self.grid = grid
        self.hacks = hacks if hacks is not None else []
        self.fight = False
        self.gravity_time = 0.0
        self.gravity = GRAVITY
        self.lock_time = 0.0
        self.resets = 0
        self.since_spawn = 0.0
        self.last_lock = None

    def spawn(self, shape, clutch_clear):
        self.gravity_time = self.lock_time = 0.0
        self.resets = 0
        self.since_spawn = 0.0
        return self.grid.spawn(shape, clutch_clear)

    def fall_fraction(self):
        if self.grid.resting():
            return 0.0
        return min(1.0, self.gravity_time / self.gravity)

    def act(self, move):
        g = self.grid
        moved = False
        if move == "L":
            moved = g.move(-1)
        elif move == "R":
            moved = g.move(1)
        elif move == "CW":
            moved = g.rotate(1)
        elif move == "CCW":
            moved = g.rotate(3)
        elif move == "180":
            moved = g.rotate(2)
        elif move == "SD":
            moved = g.soft_drop()
        elif move in ("HOLD", "HOLD2"):
            return self.hold(1 if move == "HOLD2" else 0)
        elif move == "HD":
            g.soft_drop()
            return self.lock()
        # lock reset, max 15
        if moved and g.resting() and self.resets < MAX_RESETS:
            self.resets += 1
            self.lock_time = 0.0
        return None

    def hold(self, slot):
        g = self.grid
        if g.held_this_piece:
            return None
        out = g.take_hold(slot)
        self.spawn(out, False)
        g.held_this_piece = True
        return None

    def lock(self):
        g = self.grid
        report = g.lock(self.hacks, self.fight)
        self.last_lock = report
        if report["lost"] or not self.spawn(g.step_queue(), report["lines"] > 0):
            report["lost"] = True
        return report

    def update(self, dt, lock_in=True):
        g = self.grid
        self.since_spawn += dt
        self.gravity_time += dt
        if self.gravity_time >= self.gravity:
            self.gravity_time = 0.0
            g.gravity_step()
        if lock_in and g.resting():
            self.lock_time += dt
            if self.lock_time >= LOCK_DELAY:
                return self.lock()
        else:
            self.lock_time = 0.0
        return None


class Keys:
    def __init__(self):
        self.direction = 0
        self.das = 0.0
        self.arr = 0.0

    def moves(self, left, right, dt):
        direction = right - left
        out = []
        if direction != self.direction:
            self.direction = direction
            self.das = self.arr = 0.0
            if direction:
                out.append("R" if direction > 0 else "L")
            return out
        if direction:
            self.das += dt
            if self.das >= DAS:
                self.arr += dt
                while self.arr >= ARR:
                    self.arr -= ARR
                    out.append("R" if direction > 0 else "L")
                    if len(out) > 10:
                        break
        return out


class MagicTree:
    def __init__(self):
        self.points = 0
        self.levels = {key: 0 for key, *_ in TREE}
        self.levels["discoveringMagic"] = 1

    def node(self, key):
        return next(n for n in TREE if n[0] == key)

    def cost(self, key):
        _, _, _, costs = self.node(key)
        level = self.levels[key]
        return costs[level] if level < len(costs) else None

    def can_buy(self, key):
        _, _, parent, _ = self.node(key)
        cost = self.cost(key)
        return (parent is None or self.levels[parent] > 0) and cost is not None and self.points >= cost

    def buy(self, key):
        self.points -= self.cost(key)
        self.levels[key] += 1

    def reset(self):
        for key, _, _, costs in TREE[1:]:
            self.points += sum(costs[:self.levels[key]])
            self.levels[key] = 0


class Run:
    def __init__(self, save_path):
        self.save_path = save_path
        self.rng = random.Random()
        self.tree = MagicTree()
        self.discovered = False
        self.enemy = 1
        self.disks = []
        # 0 none, 1 intro seen, 2 hacks seen
        self.tutorial = 0
        self.load()
        self.lesson = None
        self.lesson_step = 0

        self.phase = "dormant"
        self.reward = None
        self.message = ""
        self.message_time = 0.0
        self.player = Fighter(Grid(rng=self.rng), self.disks)
        self.ai = None
        self.foe = None
        self.apply_tree()
        self.fresh(self.player)
        if self.discovered:
            self.start_combat()

    def apply_tree(self):
        g = self.player.grid
        lv = self.tree.levels
        g.visible_next = 1 + lv["enhancedNext"]
        g.hold_slots = lv["hold"]
        if lv["bagRandomizer"] and g.fully_random:
            g.fully_random = False
            g.bag = list(range(7))
        while len(g.next) < g.visible_next:
            g.next.append(g.draw_piece())
        g.visible_rows = 10 + 2 * lv["tallerWell"]

    @property
    def drives(self):
        return self.tree.levels["floppyDrives"]

    def fresh(self, fighter):
        g = fighter.grid
        g.wipe()
        g.refill_queue()
        fighter.spawn(g.step_queue(), False)

    def start_combat(self):
        n = self.enemy
        self.phase = "combat"
        self.player.fight = True
        grid = Grid(visible_rows=10 + 2 * min(6, n - 1), rng=self.rng)
        grid.hold_slots = 1
        self.foe = {
            "profile": self.rng.choice(list(PROFILES)),
            "delay": max(0.2, 1.5 * 0.85 ** (n - 1)),
        }
        self.ai = Fighter(grid)
        self.ai.fight = True
        self.ai_player = AIPlayer(self.foe["profile"], self.foe["delay"], self.rng)
        self.fresh(self.player)
        self.fresh(self.ai)
        self.say(f"ENEMY {n}: {self.foe['profile'].upper()}")

    def teach(self, lesson):
        self.lesson = lesson
        self.lesson_step = 0

    def end_lesson(self):
        self.tutorial = max(self.tutorial, 2 if self.lesson == "hacks" else 1)
        self.lesson = None
        self.save()

    def say(self, text):
        self.message = text
        self.message_time = 3.0

    def player_lost(self):
        if self.phase == "dormant":
            self.fresh(self.player)
            return
        self.disks.clear()
        self.enemy = 1
        self.say("LOST: DISKS ERASED")
        self.save()
        self.start_combat()

    def enemy_lost(self):
        self.tree.points += self.enemy
        self.enemy += 1
        self.phase = "reward"
        names = list(HACKS)
        self.reward = {"choices": self.rng.sample(names, 3), "pick": 0}
        if self.tutorial < 2:
            # first drive is free so the first disk runs
            self.tree.levels["floppyDrives"] = max(1, self.drives)
            self.teach("hacks")
        self.save()

    def take_reward(self, hack):
        if hack is not None and self.drives:
            if len(self.disks) >= self.drives:
                self.disks.pop(0)
            self.disks.append(hack)
        self.reward = None
        self.save()
        self.start_combat()

    def update(self, dt, inputs):
        self.message_time = max(0.0, self.message_time - dt)
        if self.phase == "reward" or self.lesson:
            return

        fighting = self.phase == "combat"
        p = self.player
        p.fight = fighting
        reports = [p.act(m) for m in inputs]
        reports.append(p.update(dt))

        for r in reports:
            if not r:
                continue
            if r["lost"]:
                self.player_lost()
                return
            if not self.discovered and r["lines"] == 4 and r["shape"] == I and r["spin"] == SPIN_NONE:
                self.discovered = True
                self.say("MAGIC DISCOVERED")
                self.start_combat()
                if self.tutorial < 1:
                    # enough for the hold the intro buys
                    self.tree.points += self.tree.cost("hold")
                    self.teach("intro")
                self.save()
                return

        if not fighting:
            return

        a = self.ai
        a.since_spawn += dt
        ai_reports = []
        self.ai_player.update(a.grid, dt, lambda m: ai_reports.append(a.act(m)))
        if any(r and r["lost"] for r in ai_reports):
            self.enemy_lost()
            return

        fired = p.grid.tick(dt, self.disks)
        if fired:
            p.grid.send(a.grid, fired)
        fired = a.grid.tick(dt, None)
        if fired:
            a.grid.send(p.grid, fired)

    def save(self):
        lines = [f"points {self.tree.points}", f"discovered {int(self.discovered)}", f"enemy {self.enemy}",
                 f"tutorial {self.tutorial}"]
        lines += [f"{k} {v}" for k, v in self.tree.levels.items()]
        lines += [f"disk {d}" for d in self.disks]
        with open(self.save_path, "w") as f:
            f.write("\n".join(lines) + "\n")

    def load(self):
        try:
            with open(self.save_path) as f:
                pairs = [line.split() for line in f if line.strip()]
        except FileNotFoundError:
            return
        for key, value in pairs:
            if key == "points":
                self.tree.points = int(value)
            elif key == "discovered":
                self.discovered = value == "1"
            elif key == "enemy":
                self.enemy = int(value)
            elif key == "tutorial":
                self.tutorial = int(value)
            elif key == "disk":
                self.disks.append(value)
            elif key in self.tree.levels:
                self.tree.levels[key] = int(value)
