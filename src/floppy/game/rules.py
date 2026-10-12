import math
import random

T, I, S, Z, J, L, O = range(7)
GARBAGE = 7
NULL = -1
SHAPE_NAMES = "TISZJLO"

START = {
    T: [(3, 4), (4, 3), (4, 4), (5, 4)],
    S: [(3, 4), (4, 3), (4, 4), (5, 3)],
    Z: [(3, 3), (4, 3), (4, 4), (5, 4)],
    J: [(3, 3), (3, 4), (4, 4), (5, 4)],
    L: [(3, 4), (4, 4), (5, 3), (5, 4)],
    I: [(3, 4), (4, 4), (5, 4), (6, 4)],
    O: [(4, 3), (4, 4), (5, 3), (5, 4)],
}

# [unit][from], cw turn
ROT_ADJ = {
    T: [[(1, -1), (1, 1), (-1, 1), (-1, -1)], [(1, 1), (-1, 1), (-1, -1), (1, -1)],
        [(0, 0)] * 4, [(-1, 1), (-1, -1), (1, -1), (1, 1)]],
    S: [[(1, -1), (1, 1), (-1, 1), (-1, -1)], [(1, 1), (-1, 1), (-1, -1), (1, -1)],
        [(0, 0)] * 4, [(0, 2), (-2, 0), (0, -2), (2, 0)]],
    Z: [[(2, 0), (0, 2), (-2, 0), (0, -2)], [(1, 1), (-1, 1), (-1, -1), (1, -1)],
        [(0, 0)] * 4, [(-1, 1), (-1, -1), (1, -1), (1, 1)]],
    J: [[(2, 0), (0, 2), (-2, 0), (0, -2)], [(1, -1), (1, 1), (-1, 1), (-1, -1)],
        [(0, 0)] * 4, [(-1, 1), (-1, -1), (1, -1), (1, 1)]],
    L: [[(1, -1), (1, 1), (-1, 1), (-1, -1)], [(0, 0)] * 4,
        [(0, 2), (-2, 0), (0, -2), (2, 0)], [(-1, 1), (-1, -1), (1, -1), (1, 1)]],
    I: [[(2, -1), (1, 2), (-2, 1), (-1, -2)], [(1, 0), (0, 1), (-1, 0), (0, -1)],
        [(0, 1), (-1, 0), (0, -1), (1, 0)], [(-1, 2), (-2, -1), (1, -2), (2, 1)]],
    O: [[(1, 0), (0, 1), (-1, 0), (0, -1)], [(0, -1), (1, 0), (0, 1), (-1, 0)],
        [(0, 1), (-1, 0), (0, -1), (1, 0)], [(-1, 0), (0, -1), (1, 0), (0, 1)]],
}

PIECE_TABLE = []
for _shape in range(7):
    _pos = list(START[_shape])
    _rots = []
    for _r in range(4):
        _rots.append(tuple(_pos))
        _pos = [(x + ROT_ADJ[_shape][u][_r][0], y + ROT_ADJ[_shape][u][_r][1])
                for u, (x, y) in enumerate(_pos)]
    PIECE_TABLE.append(_rots)

# [isNotI][from][cw-1], 180 = SRS+
KICKS = [
    [
        [[(-2, 0), (1, 0), (-2, 1), (1, -2)], [(-1, 0), (-2, 0), (1, 0), (2, 0), (0, -1)], [(-1, 0), (2, 0), (-1, -2), (2, 1)]],
        [[(-1, 0), (2, 0), (-1, -2), (2, 1)], [(0, -1), (0, -2), (0, 1), (0, 2), (-1, 0)], [(2, 0), (-1, 0), (2, -1), (-1, 2)]],
        [[(2, 0), (-1, 0), (2, -1), (-1, 2)], [(1, 0), (2, 0), (-1, 0), (-2, 0), (0, 1)], [(1, 0), (-2, 0), (1, 2), (-2, -1)]],
        [[(1, 0), (-2, 0), (1, 2), (-2, -1)], [(0, -1), (0, -2), (0, 1), (0, 2), (1, 0)], [(-2, 0), (1, 0), (-2, 1), (1, -2)]],
    ],
    [
        [[(-1, 0), (-1, -1), (0, 2), (-1, 2)],
         [(1, 0), (2, 0), (1, -1), (2, -1), (-1, 0), (-2, 0), (-1, -1), (-2, -1), (0, 1), (3, 0), (-3, 0)],
         [(1, 0), (1, -1), (0, 2), (1, 2)]],
        [[(1, 0), (1, 1), (0, -2), (1, -2)],
         [(0, -1), (0, -2), (-1, -1), (-1, -2), (0, 1), (0, 2), (-1, 1), (-1, 2), (1, 0), (0, -3), (0, 3)],
         [(1, 0), (1, 1), (0, -2), (1, -2)]],
        [[(1, 0), (1, -1), (0, 2), (1, 2)],
         [(-1, 0), (-2, 0), (-1, 1), (-2, 1), (1, 0), (2, 0), (1, 1), (2, 1), (0, -1), (-3, 0), (3, 0)],
         [(-1, 0), (-1, -1), (0, 2), (-1, 2)]],
        [[(-1, 0), (-1, 1), (0, -2), (-1, -2)],
         [(0, -1), (0, -2), (1, -1), (1, -2), (0, 1), (0, 2), (1, 1), (1, 2), (-1, 0), (0, -3), (0, 3)],
         [(-1, 0), (-1, 1), (0, -2), (-1, -2)]],
    ],
]

HIDDEN_ROWS = 6
COLUMNS = 10


def cells(shape, st):
    rot, dx, dy = st
    return [(x + dx, y + dy) for x, y in PIECE_TABLE[shape][rot]]


# bit c = column c, row 0 = top
class Board:
    def __init__(self, num_rows, num_columns=COLUMNS):
        self.num_rows = num_rows
        self.num_columns = num_columns
        self.rows = [0] * num_rows
        self.colors = [[NULL] * num_columns for _ in range(num_rows)]

    def copy(self):
        b = Board.__new__(Board)
        b.num_rows, b.num_columns = self.num_rows, self.num_columns
        b.rows = list(self.rows)
        b.colors = None
        return b

    @property
    def full_row(self):
        return (1 << self.num_columns) - 1

    @property
    def floor(self):
        return self.num_rows - 1

    def occupied(self, x, y):
        return (self.rows[y] >> x) & 1

    def empty(self):
        return self.rows[-1] == 0

    def cell_count(self):
        return sum(bin(r).count("1") for r in self.rows)

    def stack_rows(self):
        n = 0
        while n < self.num_rows and self.rows[self.num_rows - 1 - n]:
            n += 1
        return n

    def fits(self, shape, st):
        rot, dx, dy = st
        rows, w, h = self.rows, self.num_columns, self.num_rows
        for x, y in PIECE_TABLE[shape][rot]:
            x += dx
            y += dy
            if x < 0 or x >= w or y < 0 or y >= h or (rows[y] >> x) & 1:
                return False
        return True

    def dropped(self, shape, st):
        rot, dx, dy = st
        while self.fits(shape, (rot, dx, dy + 1)):
            dy += 1
        return (rot, dx, dy)

    def set_cell(self, x, y, color=GARBAGE):
        self.rows[y] |= 1 << x
        if self.colors is not None:
            self.colors[y][x] = color

    def lock_cells(self, shape, st):
        for x, y in cells(shape, st):
            self.set_cell(x, y, shape)

    def clear_full_rows(self):
        full = self.full_row
        kept = [i for i, r in enumerate(self.rows) if r != full]
        cleared = [i for i, r in enumerate(self.rows) if r == full]
        if not cleared:
            return 0, cleared
        pad = len(cleared)
        self.rows = [0] * pad + [self.rows[i] for i in kept]
        if self.colors is not None:
            self.colors = [[NULL] * self.num_columns for _ in range(pad)] + [self.colors[i] for i in kept]
        return pad, cleared

    def add_garbage(self, lines, hole):
        if any(self.rows[:lines]):
            return False
        row = self.full_row & ~(1 << hole)
        self.rows = self.rows[lines:] + [row] * lines
        if self.colors is not None:
            garbage = [GARBAGE] * self.num_columns
            garbage[hole] = NULL
            self.colors = self.colors[lines:] + [list(garbage) for _ in range(lines)]
        return True

    def heights(self):
        out = [0] * self.num_columns
        for y, r in enumerate(self.rows):
            if not r:
                continue
            for x in range(self.num_columns):
                if out[x] == 0 and (r >> x) & 1:
                    out[x] = self.num_rows - y
        return out


def try_rotate(board, shape, st, cw):
    rot, dx, dy = st
    to = (rot + cw) % 4
    if board.fits(shape, (to, dx, dy)):
        return (to, dx, dy), False
    kicks = KICKS[0 if shape == I else 1][rot][cw - 1]
    for k, (kx, ky) in enumerate(kicks):
        out = (to, dx + kx, dy + ky)
        if board.fits(shape, out):
            return out, cw != 2 and k == len(kicks) - 1
    return None


SPIN_NONE, SPIN_MINI, SPIN_FULL = range(3)


# all-mini+
def spin_kind(board, shape, st, final_kick):
    if shape == O:
        return SPIN_NONE
    rot, dx, dy = st
    if shape == T:
        p = cells(shape, st)
        centre = p[0]
        for a in p:
            if sum(abs(o[0] - a[0]) + abs(o[1] - a[1]) == 1 for o in p) == 3:
                centre = a
        nub = (0, 0)
        for arm in p:
            if arm != centre and (2 * centre[0] - arm[0], 2 * centre[1] - arm[1]) not in p:
                nub = (arm[0] - centre[0], arm[1] - centre[1])

        def filled(x, y):
            return x < 0 or x >= board.num_columns or y < 0 or y > board.floor or board.occupied(x, y)

        side = (nub[1], nub[0])
        cx, cy = centre
        front = filled(cx + nub[0] + side[0], cy + nub[1] + side[1]) + filled(cx + nub[0] - side[0], cy + nub[1] - side[1])
        back = filled(cx - nub[0] + side[0], cy - nub[1] + side[1]) + filled(cx - nub[0] - side[0], cy - nub[1] - side[1])
        if front + back >= 3:
            return SPIN_FULL if front == 2 or final_kick else SPIN_MINI

    for mx, my in ((-1, 0), (1, 0), (0, -1), (0, 1)):
        if board.fits(shape, (rot, dx + mx, dy + my)):
            return SPIN_NONE
    return SPIN_MINI


CLEAR_ATTACK = (0, 0, 1, 2, 4)
TSPIN_ATTACK = (0, 2, 4, 6)
MINI_ATTACK = (0, 0, 1, 2, 4)
SURGE_AT, SURGE_BASE = 4, 4
ALL_CLEAR_ATTACK = 5


class Streaks:
    __slots__ = ("combo", "b2b", "surge")

    def __init__(self, combo=-1, b2b=-1, surge=0):
        self.combo, self.b2b, self.surge = combo, b2b, surge

    def copy(self):
        return Streaks(self.combo, self.b2b, self.surge)


def lock_attack(streaks, lines, spin, all_clear):
    if lines == 0:
        streaks.combo = -1
        streaks.surge = 0
        return 0
    streaks.combo += 1
    streaks.surge = 0
    if lines >= 4 or spin != SPIN_NONE or all_clear:
        streaks.b2b += 1
    else:
        if streaks.b2b >= SURGE_AT:
            streaks.surge = SURGE_BASE + streaks.b2b - SURGE_AT
        streaks.b2b = -1

    if spin == SPIN_FULL:
        attack = float(TSPIN_ATTACK[lines])
    elif spin == SPIN_MINI:
        attack = float(MINI_ATTACK[lines])
    else:
        attack = float(CLEAR_ATTACK[lines])
    if streaks.b2b > 0:
        attack += 1.0
    if streaks.combo > 0:
        attack *= 1.0 + 0.25 * streaks.combo
        if streaks.combo > 1:
            attack = max(math.log1p(1.25 * streaks.combo), attack)
    return int(attack) + streaks.surge + (ALL_CLEAR_ATTACK if all_clear else 0)


def clear_name(streaks, lines, spin, all_clear):
    name = "B2B " if streaks.b2b > 0 else ""
    if spin == SPIN_FULL:
        name += "T-SPIN "
    if spin == SPIN_MINI:
        name += "MINI "
    name += ("", "SINGLE", "DOUBLE", "TRIPLE", "QUAD")[lines]
    if all_clear:
        name += " ALL CLEAR"
    if streaks.combo > 0:
        name += f" x{streaks.combo}"
    if streaks.surge > 0:
        name += " SURGE"
    return name


WINDOW_OPEN, WINDOW_EXTEND, WINDOW_MAX = 3.0, 1.0, 8.0
GARBAGE_DELAY, GARBAGE_CAP = 5.0, 8


class Gauge:
    def __init__(self):
        self.open = False
        self.base = 0
        self.hand = 0.0
        self.time = 0.0
        self.length = 0.0
        self.clears = 0
        self.quad = False
        self.tspin = False
        self.hand_name = ""
        self.last_clear = ""

    def feed(self, streaks, attack, lines, spin, all_clear):
        if not self.open:
            self.__init__()
            self.open = True
            self.length = WINDOW_OPEN
        else:
            self.length = min(self.length + WINDOW_EXTEND, WINDOW_MAX)
        self.base += lines
        self.last_clear = clear_name(streaks, lines, spin, all_clear)
        hand = attack / lines
        if self.clears == 0 or hand > self.hand:
            self.hand = hand
            self.hand_name = self.last_clear
        self.clears += 1
        self.quad = self.quad or lines >= 4
        self.tspin = self.tspin or spin == SPIN_FULL


class Incoming:
    __slots__ = ("lines", "hole", "wait")

    def __init__(self, lines, hole):
        self.lines, self.hole, self.wait = lines, hole, GARBAGE_DELAY

    def ready(self):
        return self.wait <= 0.0


class Grid:
    def __init__(self, visible_rows=10, rng=None):
        self.rng = rng or random.Random()
        self.visible_rows = visible_rows
        self.fully_random = True
        self.visible_next = 1
        self.hold_slots = 0
        self.next = []
        self.bag = []
        self.wipe()
        self.refill_queue()

    def wipe(self):
        self.board = Board(HIDDEN_ROWS + self.visible_rows)
        self.shape = NULL
        self.st = (0, 0, 0)
        self.rotated = False
        self.final_kick = False
        self.hold = [NULL, NULL]
        self.held_this_piece = False
        self.streaks = Streaks()
        self.gauge = Gauge()
        self.incoming = []

    @property
    def rows(self):
        return self.board.num_rows

    def draw_piece(self):
        if self.fully_random:
            return self.rng.randrange(7)
        if not self.bag:
            self.bag = list(range(7))
        return self.bag.pop(self.rng.randrange(len(self.bag)))

    def refill_queue(self):
        self.bag = list(range(7))
        self.next = [self.draw_piece() for _ in range(max(7, self.visible_next))]

    def step_queue(self):
        piece = self.next.pop(0)
        self.next.append(self.draw_piece())
        return piece

    def move(self, dx):
        rot, x, y = self.st
        if not self.board.fits(self.shape, (rot, x + dx, y)):
            return False
        self.st = (rot, x + dx, y)
        self.rotated = False
        return True

    def rotate(self, cw):
        turned = try_rotate(self.board, self.shape, self.st, cw)
        if turned is None:
            return False
        self.st, self.final_kick = turned
        self.rotated = True
        return True

    def gravity_step(self):
        rot, x, y = self.st
        if not self.board.fits(self.shape, (rot, x, y + 1)):
            return False
        self.st = (rot, x, y + 1)
        self.rotated = False
        return True

    def soft_drop(self):
        landed = self.board.dropped(self.shape, self.st)
        if landed == self.st:
            return False
        self.st = landed
        self.rotated = False
        return True

    def resting(self):
        rot, x, y = self.st
        return not self.board.fits(self.shape, (rot, x, y + 1))

    def ghost(self):
        return self.board.dropped(self.shape, self.st)

    def spawn(self, shape, clutch_clear):
        st = (0, 0, 0)
        # clutch: push up while blocked
        if clutch_clear:
            first = PIECE_TABLE[shape][0][0][1]
            while not self.board.fits(shape, st) and first + st[2] >= 0:
                st = (0, 0, st[2] - 1)
        self.shape, self.st = shape, st
        self.rotated = self.final_kick = False
        self.held_this_piece = False
        return self.board.fits(shape, st)

    def take_hold(self, slot):
        out = self.hold[slot]
        if out == NULL:
            out = self.step_queue()
        self.hold[slot] = self.shape
        return out

    def lock(self, hacks, fight):
        board = self.board
        spin = spin_kind(board, self.shape, self.st, self.final_kick) if self.rotated else SPIN_NONE
        board.lock_cells(self.shape, self.st)
        lines, cleared = board.clear_full_rows()
        all_clear = lines > 0 and board.empty()
        attack = lock_attack(self.streaks, lines, spin, all_clear)
        report = {"lines": lines, "spin": spin, "all_clear": all_clear, "attack": attack,
                  "cleared": cleared, "lost": False, "shape": self.shape}
        self.shape = NULL

        if attack > 0 or (lines and "SINGLES.BAT" in (hacks or ())):
            if fight:
                self.gauge.feed(self.streaks, attack, lines, spin, all_clear)
        elif lines == 0 and not self.land_garbage():
            report["lost"] = True
        return report

    def land_garbage(self):
        room = GARBAGE_CAP
        while room > 0 and self.incoming and self.incoming[0].ready():
            g = self.incoming[0]
            lines = min(room, g.lines)
            if not self.board.add_garbage(lines, g.hole):
                return False
            g.lines -= lines
            room -= lines
            if g.lines == 0:
                self.incoming.pop(0)
        return True

    def tick(self, dt, hacks):
        for g in self.incoming:
            g.wait -= dt
        gauge = self.gauge
        if not gauge.open:
            return 0
        gauge.time += dt
        if gauge.time < gauge.length:
            return 0
        gauge.open = False
        return score_gauge(gauge, self.streaks, self.board, hacks)[2]

    def send(self, to, lines):
        while lines > 0 and self.incoming:
            c = min(lines, self.incoming[0].lines)
            self.incoming[0].lines -= c
            lines -= c
            if self.incoming[0].lines == 0:
                self.incoming.pop(0)
        if lines:
            to.incoming.append(Incoming(lines, self.rng.randrange(to.board.num_columns)))

    def incoming_lines(self):
        return sum(g.lines for g in self.incoming)


def score_gauge(gauge, streaks, board, hacks):
    base, mult = gauge.base, gauge.hand
    for hack in hacks or ():
        if hack == "PLAIN.DSK":
            mult += 0.25
        elif hack == "QUADRO":
            mult += 0.5 if gauge.quad else 0.0
        elif hack == "SPINLOCK":
            mult += 0.75 if gauge.tspin else 0.0
        elif hack == "COMBO.SYS":
            base += max(0, gauge.clears - 1)
        elif hack == "B2B.CHAIN":
            mult += 0.1 * max(0, streaks.b2b)
        elif hack == "LOWRIDER":
            base += 3 if board.stack_rows() <= 4 else 0
        elif hack == "OVERCLOCK":
            mult *= 1.25 if gauge.clears >= 3 else 1.0
    return base, mult, int(base * mult)
