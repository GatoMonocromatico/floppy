import pyxel

# ---------------------------------------------------------------------------
# Palette (sampled from assets/textures/bank1.png and bank2.png)
# ---------------------------------------------------------------------------
# Both banks are 256x256 -- exactly pyxel.IMAGE_SIZE -- so bank1 goes into
# images[0] and bank2 into images[1] untouched.
#
# The PNGs carry more RGB values than they look like they do (497 in bank1, 119
# in bank2): Krita exports antialiased edges and gradients that wobble a level
# or two, so bank2's orange lands on FA/FB/FC/FD4305 where bank1's is a clean
# FF4305. They are one colour, and the 16 below are the intended ones.
#
# Image.load() snaps every pixel to the nearest entry here, so that noise costs
# nothing -- it just means the PNGs on disk are not byte-identical to what
# pyxel renders. Four dimmer duplicates (727272, 006D6D, 00CBCB, 392D44) were
# folded into their neighbours to fit 16 slots; that shifts 4.2% of bank1's
# pixels, all of them inside the noisy backdrop art.
#
# Note pyxel ignores alpha on load and takes the RGB channels as they are.
# Two consequences. The transparent regions are only unused canvas (bank1 rows
# 223+, bank2's right margin) and are transparent *black*, so they arrive as
# index 0 -- but black is also every UI panel interior, so blitting the banks
# with colkey=0 would punch holes straight through the panels. And bank1's
# eighth swatch (x 212..242, y 192..222) is painted at 31% opacity in the .kra;
# pyxel renders it fully opaque, white on black.

# greys
COLOR_BLACK = 0         # panel interiors, and where alpha lands
COLOR_DARK_GREY = 1     # backdrop noise, bevels
COLOR_GREY = 2
COLOR_WHITE = 3         # UI text ("STATISTICS", "HOLD", "NEXT")

# greens -> cyans
COLOR_DARK_GREEN = 4    # bank2 backdrop
COLOR_TEAL = 5          # piece skin
COLOR_SPRING = 6        # piece skin
COLOR_CYAN = 7          # UI panel borders

# warms
COLOR_OLIVE = 8         # piece skin
COLOR_YELLOW = 9        # piece skin
COLOR_ORANGE = 10       # piece skin
COLOR_CRIMSON = 11      # backdrop

# purples
COLOR_PURPLE = 12       # backdrop
COLOR_SLATE = 13        # backdrop
COLOR_INDIGO = 14       # backdrop
COLOR_VIOLET = 15       # piece skin

# 24-bit RGB, indexed by the constants above.
PALETTE = [
    0x000000,   # 0  black
    0x262626,   # 1  dark grey
    0x939393,   # 2  grey
    0xFFFFFF,   # 3  white
    0x133D37,   # 4  dark green
    0x3CAA90,   # 5  teal
    0x04FFC4,   # 6  spring
    0x00FFFF,   # 7  cyan
    0x807D42,   # 8  olive
    0xFFF405,   # 9  yellow
    0xFF4305,   # 10 orange
    0x8C0943,   # 11 crimson
    0x793678,   # 12 purple
    0x514059,   # 13 slate
    0x33035F,   # 14 indigo
    0x6305FF,   # 15 violet
]

# The swatch strip along the bottom of bank1 (y 192..222), read left to right.
# Each swatch is 31px wide and painted as three concentric squares, so a skin
# is (border, ring, core). Six colours cover the seven real skins -- the same
# six the cubes in bank2 are drawn with. Skin 8 is the faded placeholder.
PIECE_SKINS = [
    (COLOR_OLIVE,  COLOR_SPRING, COLOR_ORANGE),
    (COLOR_TEAL,   COLOR_YELLOW, COLOR_SPRING),
    (COLOR_VIOLET, COLOR_OLIVE,  COLOR_SPRING),
    (COLOR_TEAL,   COLOR_ORANGE, COLOR_VIOLET),
    (COLOR_ORANGE, COLOR_TEAL,   COLOR_YELLOW),
    (COLOR_SPRING, COLOR_OLIVE,  COLOR_VIOLET),
    (COLOR_YELLOW, COLOR_TEAL,   COLOR_ORANGE),
    (COLOR_WHITE,  COLOR_BLACK,  COLOR_WHITE),
]


def apply() -> None:
    """Install PALETTE as pyxel's display colours. Call after pyxel.init()."""
    # Slice assignment, not the deprecated Colors.from_list(). pyxel accepts
    # 1..256 entries even though NUM_COLORS reads 16, so this list can grow.
    pyxel.colors[:] = PALETTE
