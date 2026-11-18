import math
import random
import turtle
from tkinter import TclError

WIDTH, HEIGHT = 1000, 700
TICK_MS = 33            # ~30 fps
HORIZON = -112          # donde empieza el pasto
FEET_Y = -178           # donde pisan los personajes

screen = turtle.Screen()
screen.setup(WIDTH, HEIGHT)
screen.title("El pequeño reino de la princesa")
screen.bgcolor("#8ED4FF")
screen.tracer(0)


# =====================================================================
#  UTILIDADES: color y geometria
# =====================================================================

def _rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def _hex(c):
    return "#%02x%02x%02x" % tuple(max(0, min(255, int(v))) for v in c)


def mix(a, b, t):
    ra, rb = _rgb(a), _rgb(b)
    return _hex([ra[i] + (rb[i] - ra[i]) * t for i in range(3)])


def shade(c, f):
    """f<1 oscurece, f>1 aclara."""
    return mix(c, "#000000", 1 - f) if f < 1 else mix(c, "#ffffff", f - 1)


def ellipse_pts(cx, cy, rx, ry, rot=0, n=40):
    r = math.radians(rot)
    cr, sr = math.cos(r), math.sin(r)
    pts = []
    for i in range(n):
        a = 2 * math.pi * i / n
        x, y = rx * math.cos(a), ry * math.sin(a)
        pts.append((cx + x * cr - y * sr, cy + x * sr + y * cr))
    return pts


def smooth(pts, n=8, closed=True):
    """Spline Catmull-Rom: convierte puntos toscos en curvas suaves."""
    P = list(pts)
    m = len(P)
    out = []
    for i in range(m if closed else m - 1):
        if closed:
            p0, p1, p2, p3 = P[(i - 1) % m], P[i], P[(i + 1) % m], P[(i + 2) % m]
        else:
            p0 = P[i - 1] if i > 0 else P[0]
            p1, p2 = P[i], P[i + 1]
            p3 = P[i + 2] if i + 2 < m else P[-1]
        for k in range(n):
            t = k / n
            t2, t3 = t * t, t * t * t
            x = 0.5 * (2 * p1[0] + (-p0[0] + p2[0]) * t
                       + (2 * p0[0] - 5 * p1[0] + 4 * p2[0] - p3[0]) * t2
                       + (-p0[0] + 3 * p1[0] - 3 * p2[0] + p3[0]) * t3)
            y = 0.5 * (2 * p1[1] + (-p0[1] + p2[1]) * t
                       + (2 * p0[1] - 5 * p1[1] + 4 * p2[1] - p3[1]) * t2
                       + (-p0[1] + 3 * p1[1] - 3 * p2[1] + p3[1]) * t3)
            out.append((x, y))
    if not closed:
        out.append(P[-1])
    return out


def stroke_poly(pts, w):
    """Convierte una linea en un poligono con grosor w."""
    L, R = [], []
    for i, (x, y) in enumerate(pts):
        a = pts[max(i - 1, 0)]
        b = pts[min(i + 1, len(pts) - 1)]
        dx, dy = b[0] - a[0], b[1] - a[1]
        d = math.hypot(dx, dy) or 1
        nx, ny = -dy / d * w / 2, dx / d * w / 2
        L.append((x + nx, y + ny))
        R.append((x - nx, y - ny))
    return L + R[::-1]


def heart_pts(cx, cy, s):
    pts = []
    for i in range(0, 360, 10):
        t = math.radians(i)
        x = 16 * math.sin(t) ** 3
        y = (13 * math.cos(t) - 5 * math.cos(2 * t)
             - 2 * math.cos(3 * t) - math.cos(4 * t))
        pts.append((cx + x * s / 16, cy + (y + 2.5) * s / 16))
    return pts


def rrect_pts(x0, y0, x1, y1, r, n=8):
    """Rectangulo redondeado (y0 abajo, y1 arriba)."""
    pts = []
    for cx, cy, a0 in [(x1 - r, y1 - r, 0), (x0 + r, y1 - r, 90),
                       (x0 + r, y0 + r, 180), (x1 - r, y0 + r, 270)]:
        for i in range(n + 1):
            a = math.radians(a0 + 90 * i / n)
            pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


# =====================================================================
#  DIBUJO ESTATICO (fondo y mensajes)
# =====================================================================

def make_pen():
    p = turtle.Turtle(visible=False)
    p.speed(0)
    p.penup()
    return p


bg = make_pen()
msg = make_pen()


def soften(c, a=.15):
    r, g, b = _rgb(c)
    l = int(.3 * r + .59 * g + .11 * b)
    return mix(c, _hex((l, l, l)), a)


def fill_poly(p, pts, fill=None, edge=None, w=1):
    if p is bg:
        fill = soften(fill) if fill else fill
        edge = soften(edge) if edge else edge
    p.penup()
    p.goto(pts[0])
    p.pensize(w)
    p.pencolor(edge or fill or "#000000")
    if fill:
        p.fillcolor(fill)
        p.begin_fill()
    p.pendown()
    for q in pts[1:]:
        p.goto(q)
    p.goto(pts[0])
    if fill:
        p.end_fill()
    p.penup()


def fill_ell(p, cx, cy, rx, ry, fill, edge=None, w=1, rot=0):
    fill_poly(p, ellipse_pts(cx, cy, rx, ry, rot), fill, edge, w)


def write(p, x, y, s, size, color, style="bold", font="Arial", align="center"):
    p.penup()
    p.goto(x, y)
    p.pencolor(color)
    p.write(s, align=align, font=(font, size, style))


def static_heart(p, cx, cy, s, fill, edge=None):
    fill_poly(p, heart_pts(cx, cy, s), fill, edge or shade(fill, .8), 1)


# ---- cielo, sol y colinas -------------------------------------------

def draw_sky():
    top, bot = "#5BB6F6", "#D4F0FF"
    bands = 30
    y_top = 350
    for i in range(bands):
        ya = y_top - (y_top - HORIZON) * i / bands
        yb = y_top - (y_top - HORIZON) * (i + 1) / bands
        c = mix(top, bot, i / (bands - 1))
        fill_poly(bg, [(-510, ya + 1), (510, ya + 1), (510, yb), (-510, yb)], c)


def draw_sun():
    for r, c in [(74, "#FFF6C4"), (60, "#FFEE96"), (46, "#FFE15A")]:
        fill_ell(bg, 415, 285, r, r, c)
    fill_ell(bg, 415, 285, 34, 34, "#FFD23F", "#F2B705", 2)


def hill(cx, base, rx, ry, col, edge, eyes=True):
    pts = [(cx + rx * math.cos(math.radians(a)),
            base + ry * math.sin(math.radians(a))) for a in range(0, 181, 5)]
    fill_poly(bg, pts, col, edge, 3)
    # manchas de la colina
    for dx, dy, r in [(-.55, .25, .09), (.58, .22, .08), (-.35, .62, .06)]:
        fill_ell(bg, cx + dx * rx, base + dy * ry, r * rx * .5, r * ry * .55,
                 shade(col, .9), None)
    if eyes:
        ey = base + ry * .48
        for dx in (-.13, .13):
            fill_ell(bg, cx + dx * rx, ey, 7, 14, "#25303B")
            fill_ell(bg, cx + dx * rx - 2, ey + 5, 2.6, 4.5, "#FFFFFF")


def draw_hills():
    for cx, rx, ry, c in [(-420, 230, 95, "#BDEBB0"), (-60, 260, 80, "#B2E8A5"),
                          (300, 250, 100, "#BDEBB0")]:
        fill_ell(bg, cx, HORIZON - 25, rx, ry, c, None)
    hill(430, HORIZON, 175, 150, "#82DA6C", "#4DA94B")
    hill(-120, HORIZON, 125, 88, "#6FCE5C", "#3F9B45")


# ---- castillo ---------------------------------------------------------

def tower(cx, b, w, h, roof_h, wall, roof):
    fill_poly(bg, [(cx - w / 2, b), (cx - w / 2, b + h),
                   (cx + w / 2, b + h), (cx + w / 2, b)], wall, "#D9A98C", 2)
    fill_poly(bg, [(cx - w / 2 - 7, b + h - 2), (cx, b + h + roof_h),
                   (cx + w / 2 + 7, b + h - 2)], roof, shade(roof, .72), 2)
    fill_poly(bg, [(cx - w / 2 - 7, b + h - 2), (cx, b + h + roof_h),
                   (cx - 2, b + h - 2)], shade(roof, 1.18), None)
    fill_ell(bg, cx, b + h * .55, w * .15, w * .24, "#78BBFA", "#3B78B8", 2)


def draw_castle(cx=-335, b=HORIZON):
    fill_poly(bg, [(cx - 90, b), (cx - 90, b + 82),
                   (cx + 90, b + 82), (cx + 90, b)], "#FFF1E0", "#D9A98C", 2)
    wall, roof = "#FFF3E4", "#EE4D78"
    tower(cx - 84, b, 52, 108, 58, wall, roof)
    tower(cx + 84, b, 52, 108, 58, wall, roof)
    tower(cx, b, 92, 150, 86, wall, roof)
    # puerta
    fill_poly(bg, [(cx - 17, b), (cx - 17, b + 34), (cx + 17, b + 34),
                   (cx + 17, b)], "#8E4F37", "#5E311F", 2)
    fill_ell(bg, cx, b + 34, 17, 17, "#8E4F37", "#5E311F", 2)
    fill_ell(bg, cx + 9, b + 18, 2.5, 2.5, "#F7C531")
    # vitral con corazon
    fill_ell(bg, cx, b + 98, 20, 20, "#F7C531", "#B8861A", 2)
    fill_ell(bg, cx, b + 98, 15, 15, "#7DB9FF", "#3B78B8", 1)
    static_heart(bg, cx, b + 98, 8, "#FF86B1")
    # banderas
    for fx, fy in [(cx, b + 236), (cx - 84, b + 166), (cx + 84, b + 166)]:
        fill_poly(bg, [(fx, fy), (fx, fy + 28)], None, "#7A5B3A", 2)
        fill_poly(bg, [(fx, fy + 28), (fx + 20, fy + 22), (fx, fy + 15)],
                  "#FF5C8A", "#C23B66", 1)
    # arbustos
    for bx in (-440, -400, -270, -235):
        fill_ell(bg, bx, b + 4, 24, 18, "#5FC453", "#3F9B45", 2)


# ---- pasto, camino y flores ------------------------------------------

def draw_ground():
    n = 12
    y_bot = -352
    for i in range(n):
        ya = HORIZON - (HORIZON - y_bot) * i / n
        yb = HORIZON - (HORIZON - y_bot) * (i + 1) / n
        c = mix("#9DEB6E", "#5DB947", i / (n - 1))
        fill_poly(bg, [(-510, ya + 1), (510, ya + 1), (510, yb), (-510, yb)], c)
    fill_poly(bg, [(-510, HORIZON), (510, HORIZON)], None, "#4FA845", 3)
    # camino al castillo
    fill_poly(bg, [(-352, HORIZON), (-318, HORIZON), (-240, -200), (-440, -200)],
              "#F5DFA8", "#D9BC7D", 2)

    random.seed(7)
    for _ in range(26):
        x = random.randint(-480, 480)
        y = random.randint(-196, -126)
        if -450 < x < -230:
            continue
        r = random.choice([5, 6, 7])
        petal = random.choice(["#FF8FBF", "#FFFFFF", "#FFD36B", "#FFB3D1"])
        for k in range(5):
            a = math.radians(90 + 72 * k)
            fill_ell(bg, x + r * math.cos(a), y + r * math.sin(a),
                     r * .85, r * .85, petal, shade(petal, .85))
        fill_ell(bg, x, y, r * .6, r * .6, "#FFE04A", "#D9A800")
    for _ in range(40):
        x = random.randint(-490, 490)
        y = random.randint(-200, -118)
        fill_poly(bg, [(x - 4, y), (x - 1, y + 9), (x + 1, y), (x + 4, y + 8),
                       (x + 6, y)], "#4DAE3E", None)


# ---- titulo (arriba) y bloques de Mario -----------------------------

def draw_title_banner():
    for sx in (-1, 1):
        fill_poly(bg, [(sx * 235, 270), (sx * 270, 270), (sx * 254, 293),
                       (sx * 270, 316), (sx * 235, 316)], "#F06FA6", "#B83F78", 2)
    fill_poly(bg, rrect_pts(-245, 262, 245, 324, 18), "#FFF8EC", "#F06FA6", 4)
    fill_poly(bg, rrect_pts(-238, 269, 238, 317, 14), None, "#F7C531", 2)
    static_heart(bg, -220, 293, 9, "#FF86B1")
    static_heart(bg, 220, 293, 9, "#FF86B1")
    write(bg, 0, 282, "WELCOME TO YOUR LITTLE KINGDOM", 14, "#D9467F")


def draw_blocks():
    y = 80
    for i, x in enumerate((-154, -110, -66)):
        q = (i == 1)
        fill = "#F7B731" if q else "#D9743A"
        edge = "#8A5A12" if q else "#7A3A18"
        fill_poly(bg, [(x - 22, y - 22), (x - 22, y + 22), (x + 22, y + 22),
                       (x + 22, y - 22)], fill, edge, 3)
        if q:
            for dx, dy in [(-16, -16), (16, -16), (-16, 16), (16, 16)]:
                fill_ell(bg, x + dx, y + dy, 2.2, 2.2, "#8A5A12")
            write(bg, x, y - 15, "?", 22, "#FFFFFF")
        else:
            fill_poly(bg, [(x - 22, y), (x + 22, y)], None, edge, 2)
            fill_poly(bg, [(x, y), (x, y + 22)], None, edge, 2)
            fill_poly(bg, [(x - 11, y - 22), (x - 11, y)], None, edge, 2)
            fill_poly(bg, [(x + 11, y - 22), (x + 11, y)], None, edge, 2)


def draw_background():
    draw_sky()
    draw_sun()
    draw_hills()
    draw_castle()
    draw_ground()
    draw_title_banner()
    draw_blocks()


# ---- dedicatoria (abajo): se va revelando linea por linea -------------

# (frame de aparicion, texto, tamano, estilo, color, y)
DEDICATION = [
    (190, "PARA MI PRINCESA", 19, "bold", "#E0508E", -235),
    (235, "No necesitas un castillo para ser una princesa...", 14, "italic", "#9C4F78", -262),
    (275, "porque convertiste mi corazón en tu reino.", 14, "italic", "#9C4F78", -284),
    (330, "Siempre serás mi princesa preciosa", 16, "bold", "#E0508E", -314),
    (365, "- Lae", 13, "italic", "#9C4F78", -314),
]


def render_messages(count):
    msg.clear()
    fill_poly(msg, rrect_pts(-405, -328, 405, -198, 22), "#FFF8EC", "#F06FA6", 4)
    fill_poly(msg, rrect_pts(-397, -320, 397, -206, 17), None, "#F7C531", 2)
    for sx in (-1, 1):
        static_heart(msg, sx * 380, -225, 8, "#FF86B1")
        static_heart(msg, sx * 380, -301, 8, "#FFB3D1")
    for i, (_, text, size, style, color, y) in enumerate(DEDICATION[:count]):
        if i == 4:      # la firma va a la derecha
            write(msg, 345, y, text, size, color, style, "Georgia", "center")
        elif style == "italic":
            write(msg, 0, y, text, size, color, style, "Georgia")
        else:
            write(msg, 0, y, text, size, color, style)
    if count >= 4:
        static_heart(msg, -245, -300, 9, "#FF6FA3")
        static_heart(msg, 245, -300, 9, "#FF6FA3")
    if count >= 1:
        static_heart(msg, -235, -226, 9, "#FF6FA3")
        static_heart(msg, 235, -226, 9, "#FF6FA3")


# =====================================================================
#  SPRITES (formas compuestas de turtle)
# =====================================================================

class Sprite:
    """Acumula poligonos de color y los registra como una forma de turtle.
    Se dibuja en orden: lo primero queda atras.  `shaded*` apila capas cada
    vez mas claras y pequenas para dar volumen (estilo render de videojuego)."""

    def __init__(self, scale=1.0):
        self.s = scale
        self.parts = []

    def poly(self, pts, fill, edge=None, line=True):
        pts = tuple((x * self.s, y * self.s) for x, y in pts)
        if edge is None:
            edge = shade(fill, .8)
        if not line:
            edge = fill
        self.parts.append((pts, fill, edge))

    def ell(self, cx, cy, rx, ry, fill, edge=None, line=True, rot=0):
        self.poly(ellipse_pts(cx, cy, rx, ry, rot), fill, edge, line)

    def blob(self, pts, fill, edge=None, line=True, closed=True):
        self.poly(smooth(pts, 8, closed), fill, edge, line)

    def stroke(self, pts, w, fill):
        p = smooth(pts, 8, False) if len(pts) > 2 else pts
        self.poly(stroke_poly(p, w), fill, fill, False)

    def limb(self, a, b, w, fill, edge=None):
        self.poly(stroke_poly([a, b], w), fill, edge)
        self.ell(a[0], a[1], w / 2, w / 2, fill, line=False)
        self.ell(b[0], b[1], w / 2, w / 2, fill, line=False)

    def spike(self, cx, cy, ang, w, h, fill, edge=None):
        r = math.radians(ang)

        def rot(x, y):
            return (cx + x * math.cos(r) - y * math.sin(r),
                    cy + x * math.sin(r) + y * math.cos(r))
        self.poly([rot(-w / 2, 0), rot(0, h), rot(w / 2, 0)], fill, edge)

    def shaded(self, pts, base, edge=None, steps=4, k=.07, light=(-.5, .8)):
        cx = sum(x for x, _ in pts) / len(pts)
        cy = sum(y for _, y in pts) / len(pts)
        w = max(x for x, _ in pts) - min(x for x, _ in pts)
        h = max(y for _, y in pts) - min(y for _, y in pts)
        dark, lite = shade(base, .93), shade(base, 1.07)
        for i in range(steps):
            t = i / (steps - 1) if steps > 1 else 0
            sc = 1 - .14 * i
            ox, oy = light[0] * k * w * t, light[1] * k * h * t
            q = [(cx + (x - cx) * sc + ox, cy + (y - cy) * sc + oy) for x, y in pts]
            self.poly(q, mix(dark, lite, t), (edge or shade(base, .7)) if i == 0 else None,
                      line=(i == 0))

    def shaded_ell(self, cx, cy, rx, ry, base, edge=None, steps=4, rot=0):
        self.shaded(ellipse_pts(cx, cy, rx, ry, rot), base, edge, steps)

    def shaded_blob(self, pts, base, edge=None, steps=4):
        self.shaded(smooth(pts, 8), base, edge, steps)

    def register(self, name):
        shape = turtle.Shape("compound")
        for pts, fill, edge in self.parts:
            shape.addcomponent(pts, fill, edge)
        screen.register_shape(name, shape)


# ---- Princesa Peach ---------------------------------------------------

PEACH_HANDS = [(78, 146), (88, 168), (92, 190)]    # saludo con la mano derecha


def build_peach(name, reach, hand):
    SKIN, SKIN_D = "#F7D9C4", "#D9AC90"
    HAIR, HAIR_D, HAIR_L = "#EDC75A", "#B98E30", "#F9E2A0"
    PINK, PINK_D, PINK_L = "#F1A8C7", "#CF7AA2", "#FAD4E4"
    GOLD, GOLD_D = "#E3B646", "#A97F1C"
    BLUE, BLUE_D = "#3F78C4", "#24508F"
    WHITE, WHITE_D = "#F8F8FA", "#B4B7C6"
    p = Sprite(1.1)

    # --- cabello largo de atras
    back = [(0, 252), (-38, 245), (-58, 220), (-63, 185), (-60, 150), (-64, 120),
            (-58, 95), (-46, 84), (-36, 98), (-40, 125), (-38, 150), (0, 162),
            (38, 150), (40, 125), (36, 98), (46, 84), (58, 95), (64, 120),
            (60, 150), (63, 185), (58, 220), (38, 245)]
    p.shaded_blob(back, HAIR, HAIR_D, 3)
    for sx in (-1, 1):
        p.stroke([(sx * 50, 218), (sx * 57, 180), (sx * 54, 140), (sx * 57, 104)],
                 2.4, mix(HAIR, "#FFFFFF", .45))
        p.stroke([(sx * 44, 230), (sx * 50, 190), (sx * 47, 150)], 1.8,
                 mix(HAIR, HAIR_D, .5))

    # --- falda de campana
    left = smooth([(-24, 108), (-34, 86), (-62, 52), (-92, 30), (-108, 14)], 6, False)
    right = [(-x, y) for x, y in reversed(left)]
    n, sub = 7, 7
    hem = []
    for i in range(n * sub + 1):
        x = -108 + 216 * i / (n * sub)
        ph = (i / sub) % 1
        hem.append((x, 14 - 12 * math.sin(math.pi * ph)))
    p.poly(left + hem[1:-1] + right, PINK, PINK_D)
    p.poly([(-12, 106), (-58, 20), (58, 20), (12, 106)],
           mix(PINK, "#FFFFFF", .28), line=False)
    for x in (-72, -40, 40, 72):
        p.poly([(x * .3, 104), (x - 7, 18), (x + 7, 18)],
               mix(PINK, PINK_D, .5), line=False)
    top = [(x * .76, y + 20) for x, y in hem]
    p.poly(hem + top[::-1], mix(PINK, "#FFFFFF", .6), PINK_D)

    # --- corpino y cintura
    p.poly([(-25, 102), (-30, 150), (30, 150), (25, 102)], PINK, PINK_D)
    p.poly([(-26, 100), (-25, 112), (25, 112), (26, 100)], PINK_D, shade(PINK_D, .8))
    p.blob([(-15, 146), (-18, 126), (-9, 121), (-7, 140)], PINK_L, line=False)

    # --- brazos y guantes
    def glove(h, s):
        p.shaded_ell(h[0], h[1], 10.5, 11.5, WHITE, WHITE_D, 3)
        p.ell(h[0] + s * 8, h[1] - 3, 4.2, 5.6, WHITE, WHITE_D, rot=-s * 30)

    def cuff(a, b):
        t = .74
        cx, cy = a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t
        rot = math.degrees(math.atan2(b[1] - a[1], b[0] - a[0])) + 90
        p.ell(cx, cy, 8, 4, WHITE, WHITE_D, rot=rot)

    lh = (-82, 124) if reach else (-70, 100)
    for sh, hd, s in (((-46, 140), lh, -1), ((46, 140), hand, 1)):
        p.poly(stroke_poly([sh, hd], 10.5), SKIN, SKIN_D)
        cuff(sh, hd)
        glove(hd, s)

    # --- escote, cuello y mangas abombadas
    p.ell(0, 154, 26, 10, SKIN, SKIN_D)
    p.poly([(-9, 158), (9, 158), (8, 178), (-8, 178)], SKIN, SKIN_D)
    p.ell(0, 173, 9, 3.5, "#E8C3AA", line=False)
    for sx in (-1, 1):
        p.shaded_ell(sx * 45, 146, 24, 21, PINK, PINK_D, 3)
        p.ell(sx * 45, 128, 17.5, 5, PINK_L, PINK_D)

    # --- broche
    p.ell(0, 142, 10, 10, GOLD, GOLD_D)
    p.shaded_ell(0, 142, 6.8, 6.8, BLUE, BLUE_D, 3)
    p.ell(-2, 144.5, 2, 2, "#D6E8FF", line=False)

    # --- cara
    face = [(0, 157), (-17, 163), (-31, 177), (-37, 198), (-34, 218), (-22, 231),
            (0, 236), (22, 231), (34, 218), (37, 198), (31, 177), (17, 163)]
    p.shaded_blob(face, SKIN, SKIN_D, 3)
    for sx in (-1, 1):
        ex = sx * 13.5
        p.ell(sx * 23, 182, 7.5, 4, "#F4B6B0", line=False)                  # rubor
        p.ell(ex, 196, 8, 10, WHITE, "#6A5A63")                              # ojo
        p.ell(ex + sx * .4, 195, 6.4, 8.6, BLUE_D, BLUE_D)                   # iris
        p.ell(ex + sx * .4, 194, 5.2, 7, BLUE, line=False)
        p.ell(ex + sx * .4, 192, 4, 4.8, "#79AEE8", line=False)
        p.ell(ex + sx * .4, 196, 3.2, 4.6, "#14264A", line=False)           # pupila
        p.ell(ex - 1.5, 199, 2.1, 2.5, WHITE, line=False)                    # brillos
        p.ell(ex + 2, 191.5, 1.1, 1.1, WHITE, line=False)
        p.stroke([(ex - sx * 7, 199), (ex, 206.5), (ex + sx * 7, 203)], 1.8, "#4A382F")
        p.poly([(ex + sx * 6, 201), (ex + sx * 13, 204.5), (ex + sx * 8.5, 198)],
               "#4A382F", line=False)
        p.stroke([(ex - sx * 7, 211), (ex, 214), (ex + sx * 7, 212.5)], 1.8, "#B98E3E")
    p.ell(0, 186, 2, 1.4, SKIN_D, line=False)                                # nariz
    p.blob([(-7, 181), (-3.5, 179.5), (3.5, 179.5), (7, 181), (4, 176.5),
            (0, 175.5), (-4, 176.5)], "#D6637A", "#9C3A52")                  # boca

    # --- flequillo y mechones
    p.shaded_blob([(-38, 198), (-37, 224), (-22, 243), (2, 250), (26, 244), (38, 225),
                   (38, 198), (30, 214), (14, 226), (-4, 228), (-20, 222), (-31, 210)],
                  HAIR, HAIR_D, 3)
    p.stroke([(-24, 238), (-4, 242), (18, 236)], 1.6, HAIR_L)
    for sx in (-1, 1):
        p.shaded_blob([(sx * 37, 205), (sx * 43, 186), (sx * 44, 160), (sx * 37, 146),
                       (sx * 33, 160), (sx * 34, 186)], HAIR, HAIR_D, 3)

    # --- corona
    p.poly([(-25, 236), (25, 236), (24, 247), (-24, 247)], GOLD, GOLD_D)
    p.poly([(-24, 244), (-29, 268), (-13, 256), (0, 277), (13, 256), (29, 268),
            (24, 244)], GOLD, GOLD_D)
    p.poly([(-20, 247), (-24, 263), (-12, 254), (-4, 262)],
           shade(GOLD, 1.15), line=False)
    p.ell(0, 242, 5, 5, "#CC3B4C", "#8E1F2E")
    for sx in (-1, 1):
        p.ell(sx * 14, 241.5, 3.6, 3.6, BLUE, BLUE_D)
    for x, y in [(-29, 269), (0, 279), (29, 269)]:
        p.ell(x, y, 2.8, 2.8, WHITE, WHITE_D)

    # --- aretes
    for sx in (-1, 1):
        p.ell(sx * 39, 189, 3.2, 3.2, GOLD, GOLD_D)
        p.shaded_ell(sx * 39, 181, 4.8, 6.2, BLUE, BLUE_D, 3)

    p.register(name)


# ---- Yoshi ------------------------------------------------------------

LEGS = {                         # (pie trasero), (pie delantero)
    "idle": ((-30, 0), (26, 0)),
    "a": ((-34, 0), (42, 9)),
    "b": ((-16, 9), (26, 0)),
}


def build_yoshi(name, pose):
    G, G_D, G_L = "#6AC04B", "#3E8E30", "#A0DC82"
    BELLY, BELLY_D = "#F7F2DC", "#D2C89F"
    OR, OR_D = "#EE8C2E", "#A9560F"
    RED, RED_D = "#D63B35", "#8F221F"
    CREAM, CREAM_D = "#F5EDCB", "#CDBF92"
    bpos, fpos = LEGS[pose]
    y = Sprite(1.25)

    # --- cola con puas
    y.shaded_blob([(-36, 64), (-68, 82), (-104, 84), (-126, 62), (-108, 52),
                   (-86, 60), (-62, 50), (-34, 40)], G, G_D, 3)
    for cx, cy, ang in [(-60, 74, 20), (-82, 82, 28), (-104, 80, 36)]:
        y.spike(cx, cy, ang, 13, 15, CREAM, CREAM_D)

    # --- piernas
    for hx, foot in ((-24, bpos), (22, fpos)):
        y.poly(stroke_poly([(hx, 48), (foot[0], foot[1] + 22)], 22), G, G_D)

    # --- cuerpo, panza y silla
    y.shaded_blob([(0, 146), (-36, 136), (-54, 104), (-50, 68), (-30, 40), (10, 32),
                   (42, 44), (56, 78), (50, 116), (28, 140)], G, G_D, 4)
    y.shaded_blob([(30, 130), (12, 118), (6, 92), (10, 64), (26, 44), (44, 52),
                   (50, 82), (46, 112)], BELLY, BELLY_D, 3)
    y.shaded_blob([(-52, 104), (-48, 128), (-28, 142), (-4, 142), (6, 124),
                   (-8, 104), (-30, 92)], RED, RED_D, 3)
    y.poly(smooth([(-53, 104), (-30, 88), (-7, 103), (7, 125)], 6, False)
           + smooth([(0, 126), (-12, 109), (-30, 96), (-47, 108)], 6, False),
           "#F4F1E8", "#BDB9AA")

    # --- zapatos
    for fx, fy in (bpos, fpos):
        y.ell(fx + 4, fy + 4, 30, 7, "#F4F1E8", "#B5B1A2")
        y.shaded_ell(fx + 6, fy + 15, 31, 16, OR, OR_D, 3)

    # --- brazo con flor
    y.limb((20, 94), (86, 80), 13, G, G_D)
    y.shaded_ell(90, 78, 9, 8, G, G_D, 3)
    y.limb((90, 82), (106, 104), 3.4, "#3E8E30", "#2A6B20")
    y.ell(97, 93, 9, 3.4, "#5DAE4A", "#3E8E30", rot=40)
    for k in range(5):
        a = math.radians(90 + 72 * k)
        y.ell(106 + 10 * math.cos(a), 108 + 10 * math.sin(a), 8, 8,
              "#F08FB4", "#C96A92")
    y.ell(106, 108, 6.3, 6.3, "#F2D24E", "#B8982A")

    # --- puas del cuello
    for cx, cy, ang in [(-8, 188, 50), (-17, 168, 62), (-26, 148, 74)]:
        y.spike(cx, cy, ang, 13, 17, CREAM, CREAM_D)

    # --- cabeza con hocico grande
    y.shaded_blob([(-16, 150), (-10, 180), (10, 199), (38, 202), (60, 190), (88, 188),
                   (110, 176), (118, 152), (108, 128), (82, 118), (50, 120), (24, 124),
                   (2, 130)], G, G_D, 4)
    y.ell(100, 168, 3.2, 5, G_D, line=False, rot=10)                 # fosas nasales
    y.ell(111, 160, 2.8, 4.4, G_D, line=False, rot=-10)
    y.stroke([(46, 134), (66, 127), (90, 129), (106, 141)], 2.4, "#27591F")
    y.ell(60, 140, 6, 4, G_L, line=False)                            # cachete
    y.shaded_ell(34, 192, 17, 25, G, G_D, 3)                         # parpado
    y.shaded_ell(36, 196, 13.5, 22, "#FAFAF6", "#262626", 3)         # ojo
    y.ell(42, 196, 6.5, 12, "#111111", line=False)
    y.ell(44, 203, 2.8, 4, "#FFFFFF", line=False)

    y.register(name)


# ---- formas sencillas ---------------------------------------------------

def build_small_shapes():
    screen.register_shape("heart", tuple(heart_pts(0, 0, 10)))
    screen.register_shape("spark", ((0, 10), (2.5, 2.5), (10, 0), (2.5, -2.5),
                                    (0, -10), (-2.5, -2.5), (-10, 0), (-2.5, 2.5)))
    screen.register_shape("shadow_peach", tuple(ellipse_pts(0, 0, 130, 8, 0)))
    screen.register_shape("shadow_yoshi", tuple(ellipse_pts(0, 0, 150, 7, 0)))
    c = Sprite(1.0)
    c.ell(0, -8, 58, 14, "#FFFFFF", "#C6E4FA")
    c.ell(-32, 4, 22, 18, "#FFFFFF", "#C6E4FA")
    c.ell(2, 14, 28, 26, "#FFFFFF", "#C6E4FA")
    c.ell(34, 4, 24, 20, "#FFFFFF", "#C6E4FA")
    c.ell(0, -6, 52, 12, "#FFFFFF", line=False)
    c.register("cloud")


# =====================================================================
#  ARMADO DE LA ESCENA
# =====================================================================

draw_background()
screen.update()

build_small_shapes()
for r in (0, 1):
    for i, h in enumerate(PEACH_HANDS):
        build_peach("peach_%d_%d" % (r, i), bool(r), h)
for pose in LEGS:
    build_yoshi("yoshi_" + pose, pose)


def make_actor(shape, x=0, y=0):
    t = turtle.Turtle()
    t.penup()
    t.speed(0)
    t.setheading(90)             # las formas se dibujan "de pie"
    t.resizemode("user")
    t.shapesize(1, 1, 1)
    t.shape(shape)
    t.goto(x, y)
    return t


# El orden de creacion define quien queda delante
shadow_y = make_actor("shadow_yoshi")
shadow_p = make_actor("shadow_peach")
for sh in (shadow_y, shadow_p):
    sh.color("#58AE45", "#58AE45")

clouds = []
for cx, cy, sp, sc in [(-380, 205, .35, 1.0), (-60, 182, .25, .8),
                       (230, 215, .30, 1.15), (440, 178, .22, .9)]:
    c = make_actor("cloud", cx, cy)
    c.shapesize(sc, sc, 1)
    clouds.append([c, cx, cy, sp])

yoshi = make_actor("yoshi_a", -620, FEET_Y)
peach = make_actor("peach_0_0", 225, FEET_Y)

PINKS = [("#E8497E", "#FF86B1"), ("#E0508E", "#FFB3D1"),
         ("#F06FA6", "#FF9EC6"), ("#D9467F", "#FF6FA3")]


class Floaty:
    """Corazoncito que sube flotando."""

    def __init__(self):
        t = make_actor("heart")
        t.hideturtle()
        self.t = t
        self.age = -random.randint(0, 100)
        self.reset()

    def reset(self):
        self.x0 = random.uniform(-40, 330)
        self.y0 = random.uniform(-40, 40)
        self.life = random.randint(90, 150)
        self.size = random.uniform(.7, 1.5)
        self.ph = random.uniform(0, 6.28)
        self.edge, self.fill = random.choice(PINKS)
        self.age = 0

    def update(self, active):
        t = self.t
        if not active:
            t.hideturtle()
            return
        self.age += 1
        if self.age < 0:
            t.hideturtle()
            return
        if self.age > self.life:
            self.reset()
            self.age = -random.randint(0, 40)
            t.hideturtle()
            return
        prog = self.age / self.life
        s = self.size * min(1, self.age / 10) * (1 - prog ** 3)
        t.goto(self.x0 + math.sin(self.age / 11 + self.ph) * 16,
               self.y0 + prog * 235)
        t.shapesize(max(s, .05), max(s, .05), 1)
        t.color(self.edge, self.fill)
        t.showturtle()


hearts = [Floaty() for _ in range(14)]

SPARKS = [(-445, 120), (-250, 232), (-30, 232), (150, 215), (300, 205),
          (455, 150), (360, 60), (110, 150), (-190, 150), (460, -20)]
sparks = []
for sx, sy in SPARKS:
    t = make_actor("spark", sx, sy)
    t.color("#F2B705", "#FFE15A")
    t.hideturtle()
    sparks.append(t)


# =====================================================================
#  ANIMACION
# =====================================================================

ARRIVE = 170                    # frame en que Yoshi llega
YOSHI_X0, YOSHI_X1 = -640, -5
frame = 0
shown = 0
cache = {"yoshi": None, "peach": None}


def set_shape(key, turtle_obj, name):
    if cache[key] != name:
        turtle_obj.shape(name)
        cache[key] = name


def tick():
    global frame, shown
    frame += 1
    f = frame

    # nubes a la deriva
    for c in clouds:
        c[1] += c[3]
        if c[1] > 560:
            c[1] = -560
        c[0].goto(c[1], c[2])

    # Yoshi camina hasta Peach
    if f < ARRIVE:
        p = f / ARRIVE
        x = YOSHI_X0 + (YOSHI_X1 - YOSHI_X0) * (1 - (1 - p) ** 2.2)
        hop = abs(math.sin(f * .45)) * 8 * (1 - p * .6)
        set_shape("yoshi", yoshi, "yoshi_a" if (f // 6) % 2 == 0 else "yoshi_b")
    else:
        x = YOSHI_X1
        hop = (math.sin(f / 9) + 1) * 1.6
        set_shape("yoshi", yoshi, "yoshi_idle")
    yoshi.goto(x, FEET_Y + hop)
    s = max(.55, 1 - hop / 40)
    shadow_y.goto(x - 8, FEET_Y - 4)
    shadow_y.shapesize(s, s, 1)

    # Peach saluda y estira la mano cuando Yoshi se acerca
    reach = 1 if f > ARRIVE - 30 else 0
    wave = [0, 1, 2, 1][(f // 7) % 4]
    set_shape("peach", peach, "peach_%d_%d" % (reach, wave))
    peach.goto(225, FEET_Y + math.sin(f / 14) * 2.5)
    shadow_p.goto(225, FEET_Y - 4)

    # corazones y destellos
    active = f > ARRIVE - 15
    for h in hearts:
        h.update(active)
    for i, st in enumerate(sparks):
        if f > 25 + i * 8:
            k = .35 + .6 * abs(math.sin(f / 9 + i))
            st.shapesize(k, k, 1)
            st.setheading(90 + f * 2 + i * 15)
            st.showturtle()

    # dedicatoria revelada poco a poco
    if shown < len(DEDICATION) and f >= DEDICATION[shown][0]:
        shown += 1
        render_messages(shown)

    screen.update()
    screen.ontimer(tick, TICK_MS)


try:
    tick()
    screen.mainloop()
except (TclError, turtle.Terminator):
    pass