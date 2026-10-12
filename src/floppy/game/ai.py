from collections import deque

from game.rules import (NULL, O, SPIN_FULL, SPIN_MINI, SPIN_NONE, T, cells,
                        lock_attack, spin_kind, try_rotate)

PROFILES = {
    "cleanFast": dict(
        clear=(0.0, 0.76, 1.52, 2.28, 3.04), tspin=(0.0, 0.76, 1.52, 2.28), mini=(0.0, 0.76, 1.52, 2.28, 3.04),
        attack=5.0, aggregate=1.0, max_height=0.21, holes=-5.99, bumpiness=1.0, danger=-3.0, danger_height=16,
        row_tr=-3.0, col_tr=-3.0, covered=-1.86),
    "quad": dict(
        clear=(0.0, -2.0, -1.5, -1.0, 17.15), tspin=(0.0, -2.0, -1.5, -1.0), mini=(0.0, -2.0, -1.5, -1.0, 10.0),
        attack=5.0, aggregate=0.76, max_height=0.25, holes=-4.13, bumpiness=-0.31, danger=-3.28, danger_height=16,
        keep_well=True, well_depth=1.54, row_tr=-1.55, col_tr=-0.13, covered=-0.93, panic=19),
    "tSpin": dict(
        clear=(0.0, -1.5, -1.0, -0.5, -0.78), tspin=(0.0, 2.0, 8.73, 0.0), mini=(0.0, -1.0, -0.5, 0.0, 3.0),
        attack=5.0, aggregate=1.0, max_height=0.14, holes=0.48, bumpiness=0.79, danger=-2.24, danger_height=15,
        tslot=(-2.44, 13.45, 17.6), row_tr=-2.75, col_tr=-1.51, covered=-1.69),
    "allSpin": dict(
        clear=(0.0, -1.5, -1.0, -0.5, 2.0), tspin=(0.0, 4.0, 8.0, 8.0), mini=(0.0, 4.0, 6.0, 6.0, 6.0),
        attack=5.0, aggregate=1.0, max_height=0.06, holes=1.0, bumpiness=1.0, danger=0.0, danger_height=22,
        tslot=(-5.0, 10.0, 15.0), row_tr=-3.0, col_tr=-0.37, covered=-3.0, panic=19),
}
TUNED_ROWS = 26

MOVES = (("L", -1), ("R", 1), ("CW", 1), ("CCW", 3), ("180", 2), ("SD", 0))


# evaluateBoard, aiSearch.cpp
def evaluate(p, board):
    n, rows, num_rows = board.num_columns, board.rows, board.num_rows
    tops = [num_rows] * n
    holes = covered = 0
    for x in range(n):
        above = 0
        for y in range(num_rows):
            if (rows[y] >> x) & 1:
                if tops[x] == num_rows:
                    tops[x] = y
                above += 1
            elif above:
                holes += 1
                covered += min(6, above)
    heights = [num_rows - t for t in tops]
    max_h = max(heights)

    well = heights.index(min(heights))
    keep_well = p.get("keep_well", False)
    bump = 0
    for x in range(n - 1):
        if keep_well and (x == well or x + 1 == well):
            continue
        bump += abs(heights[x] - heights[x + 1])

    score = p["aggregate"] * sum(heights) + p["max_height"] * max_h + p["holes"] * holes + p["bumpiness"] * bump
    over = max(0, max_h - (p["danger_height"] - (TUNED_ROWS - num_rows)))
    score += p["danger"] * over * over

    if keep_well:
        left = heights[well - 1] if well > 0 else num_rows
        right = heights[well + 1] if well < n - 1 else num_rows
        score += p["well_depth"] * min(4, min(left, right) - heights[well])

    if "tslot" in p:
        slots = count_tslots(board)
        score += sum(w * s for w, s in zip(p["tslot"], slots))

    top = min(tops)
    full_walls = (1 << (n + 1)) - 1
    changes = 0
    for y in range(top, num_rows):
        walled = (rows[y] << 1) | 1 | (1 << (n + 1))
        changes += bin((walled ^ (walled >> 1)) & full_walls).count("1")
    score += p["row_tr"] * changes

    changes = 0
    for x in range(n):
        col = [(rows[y] >> x) & 1 for y in range(tops[x], num_rows)] + [1]
        changes += sum(a != b for a, b in zip(col, col[1:]))
    score += p["col_tr"] * changes
    score += p["covered"] * covered
    return score


def count_tslots(board):
    n, rows, full = board.num_columns, board.rows, board.full_row
    inside = full & ~1 & ~(1 << (n - 1))
    out = [0, 0, 0]
    for y in range(1, board.floor):
        above, row, below = rows[y - 1], rows[y], rows[y + 1]
        free = ~row & full
        slots = (inside & free & (free << 1) & (free >> 1) & ~below & (below << 1) & (below >> 1)
                 & ((above << 1) ^ (above >> 1)) & ~above)
        if slots:
            lines = (bin(row).count("1") == n - 3) + (bin(below).count("1") == n - 1)
            out[lines] += bin(slots).count("1")
    return out


def lock_reward(p, streaks, lines, spin, all_clear):
    reward = p["attack"] * lock_attack(streaks, lines, spin, all_clear)
    if spin == SPIN_FULL:
        reward += p["tspin"][lines]
    elif spin == SPIN_MINI:
        reward += p["mini"][lines]
    else:
        reward += p["clear"][lines]
    return reward


def placements(board, shape, start):
    first = (start, False, False)
    paths = {first: ()}
    queue = deque([first])
    found = {}
    work = 0
    while queue:
        node = queue.popleft()
        st, _, _ = node
        path = paths[node]
        for name, arg in MOVES:
            if name in ("L", "R"):
                to = (st[0], st[1] + arg, st[2])
                nxt = (to, False, False) if board.fits(shape, to) else None
            elif name == "SD":
                to = board.dropped(shape, st)
                nxt = (to, False, False) if to != st else None
            elif shape == O:
                nxt = None
            else:
                turned = try_rotate(board, shape, st, arg)
                nxt = (turned[0], True, turned[1]) if turned else None
            if nxt and nxt not in paths:
                paths[nxt] = path + (name,)
                queue.append(nxt)
        if board.dropped(shape, st) == st:
            found[node] = path
        # yield so the search runs a slice per frame
        work += 1
        if work % 40 == 0:
            yield None
    yield found


class AIPlayer:
    def __init__(self, profile, play_delay, rng):
        self.profile_name = profile
        self.play_delay = play_delay
        self.rng = rng
        self.search = None
        self.plan = []
        self.wait = 0.0

    def profile(self, grid):
        p = PROFILES[self.profile_name]
        panic = p.get("panic", 27) - (TUNED_ROWS - grid.rows)
        if max(grid.board.heights()) >= panic:
            return PROFILES["cleanFast"]
        return p

    def think(self, grid):
        p = self.profile(grid)
        options = [(grid.shape, ())]
        if grid.hold_slots and not grid.held_this_piece:
            other = grid.hold[0] if grid.hold[0] != NULL else grid.next[0]
            options.append((other, ("HOLD",)))

        best, best_plan = None, ["HD"]
        for shape, prefix in options:
            spawn = (0, 0, 0)
            search = placements(grid.board, shape, spawn)
            found = next(search)
            while found is None:
                yield
                found = next(search)
            for (st, rotated, final_kick), path in found.items():
                b = grid.board.copy()
                spin = spin_kind(b, shape, st, final_kick) if rotated else SPIN_NONE
                for x, y in cells(shape, st):
                    b.rows[y] |= 1 << x
                full = b.full_row
                kept = [r for r in b.rows if r != full]
                lines = b.num_rows - len(kept)
                b.rows = [0] * lines + kept
                score = lock_reward(p, grid.streaks.copy(), lines, spin, lines > 0 and not b.rows[-1])
                score += evaluate(p, b)
                if best is None or score > best:
                    best, best_plan = score, list(prefix + path) + ["HD"]
            yield
        self.plan = best_plan

    def update(self, grid, dt, act):
        if grid.shape == NULL:
            return
        if self.search is None and not self.plan:
            self.search = self.think(grid)
            self.wait = self.play_delay * self.rng.uniform(0.3, 0.6)
        if self.search is not None:
            try:
                next(self.search)
                return
            except StopIteration:
                self.search = None
                self.step = self.play_delay * 0.5 / max(1, len(self.plan))
        self.wait -= dt
        while self.plan and self.wait <= 0.0:
            act(self.plan.pop(0))
            self.wait += self.step
