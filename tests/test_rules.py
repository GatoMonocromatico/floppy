from game.rules import I, SPIN_FULL, T, Grid, Streaks, cells, lock_attack


def grid_with(rows):
    g = Grid(visible_rows=10)
    for i, row in enumerate(reversed(rows)):
        y = g.rows - 1 - i
        for x, c in enumerate(row):
            if c == "#":
                g.board.set_cell(x, y)
    return g


def test_rotations_add_up_to_nothing():
    g = grid_with([])
    g.spawn(T, False)
    start = cells(T, g.st)
    for _ in range(4):
        assert g.rotate(1)
    assert cells(T, g.st) == start


def test_tspin_double():
    g = grid_with([
        "##########",
        "#...######",
        "##.#######",
    ][1:])
    floor = g.rows - 1
    g.board.set_cell(1, floor - 2)
    want = {(1, floor - 1), (2, floor - 1), (3, floor - 1), (2, floor)}
    g.spawn(T, False)
    g.st = next((2, dx, dy) for dx in range(-5, 8) for dy in range(30)
                if set(cells(T, (2, dx, dy))) == want)
    g.rotated = True
    report = g.lock(None, True)
    assert report["lines"] == 2 and report["spin"] == SPIN_FULL
    assert report["attack"] == 4


def test_attack_table():
    s = Streaks()
    assert lock_attack(s, 4, 0, False) == 4
    assert lock_attack(s, 4, 0, False) == 6
    assert lock_attack(s, 0, 0, False) == 0 and s.combo == -1


def test_garbage_lands_and_cancels():
    a, b = Grid(), Grid()
    a.spawn(I, False)
    b.send(a, 3)
    assert a.incoming_lines() == 3
    a.send(b, 2)
    assert a.incoming_lines() == 1 and b.incoming_lines() == 0
    a.incoming[0].wait = 0.0
    assert a.land_garbage()
    assert a.board.rows[-1] != 0


def test_block_out_is_a_loss():
    g = grid_with([])
    g.board.rows = [g.board.full_row & ~1] * g.rows
    assert not g.spawn(T, False)
