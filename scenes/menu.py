import math
import random
import pygame
from starfield import Starfield

LOW_W = 640
LOW_H = 360


def _clamp_i(x, a, b):
    return a if x < a else b if x > b else x


def _make_vignette(size):
    w, h = size
    surf = pygame.Surface((w, h), pygame.SRCALPHA)
    steps = 14
    for i in range(steps):
        t = i / (steps - 1)
        a = int(18 + 90 * (t ** 1.6))
        pad_x = int(t * w * 0.18)
        pad_y = int(t * h * 0.18)
        rect = pygame.Rect(pad_x, pad_y, w - 2 * pad_x, h - 2 * pad_y)
        pygame.draw.rect(surf, (0, 0, 0, a), rect, border_radius=40)
    return surf


def _blend_plot(surf, x, y, col):
    if x < 0 or y < 0 or x >= LOW_W or y >= LOW_H:
        return
    if len(col) == 3:
        r, g, b = col
        a = 255
    else:
        r, g, b, a = col
    if a <= 0:
        return
    old = surf.get_at((x, y))
    nr = max(old.r, int(r))
    ng = max(old.g, int(g))
    nb = max(old.b, int(b))
    na = max(old.a, int(a))
    surf.set_at((x, y), (nr, ng, nb, na))


def _draw_segment(surf, a, b, col, thickness=0):
    ax, ay = a
    bx, by = b
    dx = bx - ax
    dy = by - ay
    steps = int(max(abs(dx), abs(dy)))
    if steps <= 0:
        _blend_plot(surf, int(ax), int(ay), col)
        return
    for i in range(steps + 1):
        t = i / steps
        x = int(ax + dx * t)
        y = int(ay + dy * t)
        _blend_plot(surf, x, y, col)
        if thickness >= 1:
            _blend_plot(surf, x + 1, y, col)
            _blend_plot(surf, x - 1, y, col)
            _blend_plot(surf, x, y + 1, col)
            _blend_plot(surf, x, y - 1, col)


class Flyby:
    def __init__(self, kind, pos, vel, rng):
        self.kind = kind
        self.pos = pygame.Vector2(pos)
        self.vel = pygame.Vector2(vel)
        self.rng = rng
        self.age = 0.0
        self.twinkle = 0.0

        self.trail = []
        self.trail_max = {
            "rocket": 10,
            "meteor": 16,
            "shooting_star": 22,
            "comet": 34,
        }[kind]

        self.max_age = 22.0 if kind == "comet" else 12.0

    def update(self, dt):
        self.age += dt
        self.twinkle += dt
        self.pos += self.vel * dt
        self.trail.append(self.pos.copy())
        if len(self.trail) > self.trail_max:
            self.trail.pop(0)

    def alive(self):
        margin = 80 if self.kind == "comet" else 40
        if (
            self.pos.x < -margin
            or self.pos.x > LOW_W + margin
            or self.pos.y < -margin
            or self.pos.y > LOW_H + margin
        ):
            return False
        return self.age < self.max_age

    def _safe_norm(self, v):
        if v.length_squared() < 1e-8:
            return pygame.Vector2(1, 0)
        return v.normalize()

    def draw(self, surf):
        if self.kind == "rocket":
            self._draw_rocket(surf)
        elif self.kind == "meteor":
            self._draw_meteor(surf)
        elif self.kind == "shooting_star":
            self._draw_shooting_star(surf)
        else:
            self._draw_comet(surf)

    def _draw_rocket(self, surf):
        d = self._safe_norm(self.vel)
        p = pygame.Vector2(-d.y, d.x)

        x, y = self.pos.x, self.pos.y
        tip = pygame.Vector2(x, y) + d * 5
        left = pygame.Vector2(x, y) - d * 3 + p * 2
        right = pygame.Vector2(x, y) - d * 3 - p * 2

        pygame.draw.polygon(
            surf,
            (235, 235, 245),
            [(int(tip.x), int(tip.y)), (int(left.x), int(left.y)), (int(right.x), int(right.y))],
        )

        _blend_plot(surf, int(x + d.x * 1), int(y + d.y * 1), (200, 210, 230))

        base = pygame.Vector2(x, y) - d * 3
        for i in range(4):
            off = p * self.rng.uniform(-0.7, 0.7) + (-d) * (2 + i)
            fx = int(base.x + off.x)
            fy = int(base.y + off.y)
            col = (255, 210, 140) if i < 2 else (255, 160, 120)
            _blend_plot(surf, fx, fy, col)

    def _draw_meteor(self, surf):
        d = self._safe_norm(self.vel)
        p = pygame.Vector2(-d.y, d.x)

        hx, hy = int(self.pos.x), int(self.pos.y)
        _blend_plot(surf, hx, hy, (255, 210, 150))
        _blend_plot(surf, hx + 1, hy, (255, 190, 140))
        _blend_plot(surf, hx, hy + 1, (255, 175, 125))

        n = len(self.trail)
        if n < 2:
            return

        for i in range(n - 1):
            t = i / max(1, n - 2)
            strength = (1.0 - t) ** 2.2
            a = int(210 * strength)
            if a <= 0:
                continue

            warm = (255, 170, 120, a) if t < 0.55 else (255, 125, 105, int(a * 0.9))
            a_pt = self.trail[i]
            b_pt = self.trail[i + 1]
            _draw_segment(surf, (a_pt.x, a_pt.y), (b_pt.x, b_pt.y), warm, thickness=0)

            if t < 0.45:
                w = 1 + int(2 * (t ** 0.7))
                for _ in range(w):
                    s = self.rng.uniform(-1.2, 1.2) * (0.6 + 1.4 * t)
                    off = p * s
                    _draw_segment(
                        surf,
                        (a_pt.x + off.x, a_pt.y + off.y),
                        (b_pt.x + off.x, b_pt.y + off.y),
                        (255, 110, 95, int(a * 0.55)),
                        thickness=0,
                    )

    def _draw_shooting_star(self, surf):
        d = self._safe_norm(self.vel)
        p = pygame.Vector2(-d.y, d.x)

        hx, hy = int(self.pos.x), int(self.pos.y)

        _blend_plot(surf, hx, hy, (245, 250, 255))
        for ox, oy in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
            _blend_plot(surf, hx + ox, hy + oy, (210, 235, 255, 210))
        for ox, oy in [(2, 0), (-2, 0), (0, 2), (0, -2)]:
            _blend_plot(surf, hx + ox, hy + oy, (190, 220, 255, 140))

        n = len(self.trail)
        if n >= 2:
            for i in range(n - 1):
                t = i / max(1, n - 2)
                strength = (1.0 - t) ** 2.0
                a = int(180 * strength)
                if a <= 0:
                    continue
                col = (200, 230, 255, a)
                a_pt = self.trail[i]
                b_pt = self.trail[i + 1]
                _draw_segment(surf, (a_pt.x, a_pt.y), (b_pt.x, b_pt.y), col, thickness=0)

                if t < 0.35 and self.rng.random() < 0.22:
                    s = self.rng.uniform(-1.2, 1.2) * (0.5 + 1.2 * t)
                    off = p * s
                    _draw_segment(
                        surf,
                        (a_pt.x + off.x, a_pt.y + off.y),
                        (b_pt.x + off.x, b_pt.y + off.y),
                        (170, 210, 255, int(a * 0.55)),
                        thickness=0,
                    )

        if self.twinkle >= 0.14:
            self.twinkle = 0.0
            if self.rng.random() < 0.25:
                _blend_plot(surf, hx + 1, hy + 1, (245, 250, 255, 160))
                _blend_plot(surf, hx - 1, hy - 1, (245, 250, 255, 160))

    def _draw_comet(self, surf):
        d = self._safe_norm(self.vel)
        p = pygame.Vector2(-d.y, d.x)

        hx, hy = int(self.pos.x), int(self.pos.y)

        _blend_plot(surf, hx, hy, (255, 245, 225))
        _blend_plot(surf, hx + 1, hy, (255, 225, 195, 220))
        _blend_plot(surf, hx, hy + 1, (255, 225, 195, 220))
        _blend_plot(surf, hx - 1, hy, (220, 235, 255, 140))
        _blend_plot(surf, hx, hy - 1, (220, 235, 255, 140))

        n = len(self.trail)
        if n < 2:
            return

        for i in range(n - 1):
            t = i / max(1, n - 2)
            far = t
            strength = (1.0 - t)

            a_pt = self.trail[i]
            b_pt = self.trail[i + 1]

            ion_a = int(165 * (strength ** 1.9))
            if ion_a > 0:
                _draw_segment(
                    surf,
                    (a_pt.x, a_pt.y),
                    (b_pt.x, b_pt.y),
                    (165, 225, 255, ion_a),
                    thickness=0,
                )

            spread = 0.9 + 5.6 * (far ** 1.35)
            layers = 3 + int(8 * (far ** 1.08))
            dust_base_a = int(120 * (strength ** 1.25))
            if dust_base_a <= 0:
                continue

            for _ in range(layers):
                s = self.rng.uniform(-spread, spread)
                w = 1.0 - abs(s) / max(0.001, spread)
                a = int(dust_base_a * (w ** 1.6))
                if a <= 0:
                    continue

                off = p * s + (-d) * self.rng.uniform(0.0, 0.7)
                col = (255, 205, 165, a) if abs(s) > spread * 0.32 else (200, 230, 255, int(a * 0.85))
                _draw_segment(
                    surf,
                    (a_pt.x + off.x, a_pt.y + off.y),
                    (b_pt.x + off.x, b_pt.y + off.y),
                    col,
                    thickness=0,
                )


class MenuScene:
    def __init__(self, fonts, size):
        self.font_title = fonts["title"]
        self.font = fonts["ui"]
        self.w, self.h = size

        self.low = pygame.Surface((LOW_W, LOW_H), pygame.SRCALPHA)
        self.starfield = Starfield(LOW_W, LOW_H, count=170, seed=1337)

        self._t = 0.0
        self._rng = random.Random(2025)

        self.flybys = []
        self._spawn_timer = 0.0
        self._next_spawn = 2.5

        self.hover = None
        self._rect_sandbox = pygame.Rect(0, 0, 0, 0)
        self._rect_demo = pygame.Rect(0, 0, 0, 0)
        self._rect_quit = pygame.Rect(0, 0, 0, 0)

        self.pad_x = 16
        self.pad_y = 9
        self.gap = 10

        self.block_w = 320
        self.title_offset_y = 140

        self.bg = (18, 22, 35)

        self.fade = 1.0
        self.fade_speed = 1.3

        self._vignette = None
        self._vignette_size = None

        self.version = "v0.4.0"

        self.twinkles = []
        for _ in range(18):
            self.twinkles.append(
                {
                    "x": self._rng.randint(18, LOW_W - 18),
                    "y": self._rng.randint(18, LOW_H - 18),
                    "phase": self._rng.uniform(0.0, 6.28),
                    "rate": self._rng.uniform(0.45, 1.15),
                    "amp": self._rng.uniform(20, 50),
                    "base": self._rng.uniform(135, 180),
                }
            )

        self.planet_r = 140
        self.planet_cx = -35
        self.planet_cy = LOW_H + 35

    def set_size(self, size):
        self.w, self.h = size

    def _get_vignette(self, size):
        if self._vignette is None or self._vignette_size != size:
            self._vignette = _make_vignette(size)
            self._vignette_size = size
        return self._vignette

    def _schedule_next_spawn(self):
        self._next_spawn = self._rng.uniform(2.6, 6.8)

    def _spawn_flyby(self):
        r = self._rng.random()
        if r < 0.10:
            kind = "comet"
        elif r < 0.28:
            kind = "shooting_star"
        elif r < 0.76:
            kind = "meteor"
        else:
            kind = "rocket"

        side = self._rng.choice(["left", "right", "top", "bottom"])
        margin = 30

        speed = self._rng.uniform(70, 130)
        if kind == "shooting_star":
            speed = self._rng.uniform(120, 175)
        if kind == "comet":
            speed = self._rng.uniform(55, 90)

        if side == "left":
            pos = (-margin, self._rng.uniform(0, LOW_H))
            vel = (speed, self._rng.uniform(-18, 18))
        elif side == "right":
            pos = (LOW_W + margin, self._rng.uniform(0, LOW_H))
            vel = (-speed, self._rng.uniform(-18, 18))
        elif side == "top":
            pos = (self._rng.uniform(0, LOW_W), -margin)
            vel = (self._rng.uniform(-28, 28), speed)
        else:
            pos = (self._rng.uniform(0, LOW_W), LOW_H + margin)
            vel = (self._rng.uniform(-28, 28), -speed)

        if kind == "comet":
            v = pygame.Vector2(vel)
            if v.length_squared() > 0:
                v = v.normalize() * speed
            v += pygame.Vector2(self._rng.uniform(-10, 10), self._rng.uniform(-7, 7))
            vel = (v.x, v.y)

        self.flybys.append(Flyby(kind, pos, vel, self._rng))

    def _hit_test(self, pos):
        if self._rect_sandbox.collidepoint(pos):
            return "SANDBOX"
        if self._rect_demo.collidepoint(pos):
            return "DEMO"
        if self._rect_quit.collidepoint(pos):
            return "QUIT"
        return None

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            return "QUIT"

        if event.type == pygame.MOUSEMOTION:
            self.hover = self._hit_test(event.pos)

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            hit = self._hit_test(event.pos)
            if hit:
                return hit

        return None

    def update(self, dt):
        self._t += dt
        self.fade = max(0.0, self.fade - dt * self.fade_speed)

        self._spawn_timer += dt
        if self._spawn_timer >= self._next_spawn:
            self._spawn_timer = 0.0
            self._spawn_flyby()
            self._schedule_next_spawn()

        for f in self.flybys:
            f.update(dt)
        self.flybys = [f for f in self.flybys if f.alive()]

    def _draw_option(self, screen, label, x, y, hovered, out_rect):
        col = (240, 240, 240) if hovered else (190, 190, 190)
        surf = self.font.render(label, True, col)

        r = pygame.Rect(
            x - self.pad_x,
            y - self.pad_y,
            surf.get_width() + self.pad_x * 2,
            surf.get_height() + self.pad_y * 2,
        )
        out_rect.update(r)

        if hovered:
            box = pygame.Surface((r.w, r.h), pygame.SRCALPHA)
            pygame.draw.rect(box, (255, 255, 255, 18), (0, 0, r.w, r.h), border_radius=12)
            pygame.draw.rect(box, (255, 255, 255, 45), (0, 0, r.w, r.h), width=1, border_radius=12)
            screen.blit(box, (r.x, r.y))

        screen.blit(surf, (x, y))
        return y + r.h + self.gap

    def _draw_planet(self, surf):
        r = self.planet_r
        cx, cy = self.planet_cx, self.planet_cy

        pygame.draw.circle(surf, (6, 8, 14, 255), (cx, cy), r)

        arc_start = 4.20
        arc_len = 0.75
        points = 24

        for i in range(points):
            t = i / (points - 1)
            ang = arc_start + t * arc_len
            v = pygame.Vector2(1, 0).rotate_rad(ang)
            x = int(cx + (r - 1) * v.x)
            y = int(cy + (r - 1) * v.y)

            jitter = self._rng.random()
            a = int((16 + 55 * (1.0 - abs(t - 0.5) * 1.9)) * (0.65 + 0.45 * jitter))
            _blend_plot(surf, x, y, (160, 195, 240, a))

            if self._rng.random() < 0.22:
                _blend_plot(surf, x + 1, y, (110, 145, 210, int(a * 0.55)))

    def _draw_twinkles(self, surf):
        for s in self.twinkles:
            v = s["base"] + s["amp"] * (0.5 + 0.5 * math.sin(s["phase"] + self._t * s["rate"]))
            b = int(_clamp_i(v, 90, 235))
            x, y = int(s["x"]), int(s["y"])
            _blend_plot(surf, x, y, (b, b, b, 220))
            if b > 205 and self._rng.random() < 0.12:
                _blend_plot(surf, x + 1, y, (b, b, b, 120))
                _blend_plot(surf, x - 1, y, (b, b, b, 120))

    def draw(self, screen):
        self.low.fill(self.bg)

        drift = pygame.Vector2(self._t * 3.5, self._t * 2.0)
        self.starfield.draw(self.low, drift, zoom=1.0)

        self._draw_twinkles(self.low)
        self._draw_planet(self.low)

        for f in self.flybys:
            f.draw(self.low)

        pygame.transform.scale(self.low, (self.w, self.h), screen)
        screen.blit(self._get_vignette((self.w, self.h)), (0, 0))

        cx = self.w // 2
        cy = self.h // 2

        title_text = "SPACE CADET"
        glow1 = self.font_title.render(title_text, True, (255, 255, 255))
        glow2 = self.font_title.render(title_text, True, (255, 255, 255))
        glow1.set_alpha(28)
        glow2.set_alpha(18)

        title = self.font_title.render(title_text, True, (230, 230, 230))
        title_x = cx - title.get_width() // 2
        title_y = cy - self.title_offset_y

        screen.blit(glow1, (title_x - 1, title_y))
        screen.blit(glow2, (title_x + 1, title_y + 1))
        screen.blit(title, (title_x, title_y))

        x0 = cx - self.block_w // 2
        y = title_y + 90

        y = self._draw_option(screen, "Sandbox", x0 + 20, y, self.hover == "SANDBOX", self._rect_sandbox)
        y = self._draw_option(screen, "Galaxy Demo", x0 + 20, y, self.hover == "DEMO", self._rect_demo)
        y = self._draw_option(screen, "Quit", x0 + 20, y, self.hover == "QUIT", self._rect_quit)

        ver = self.font.render(self.version, True, (160, 160, 170))
        screen.blit(ver, (self.w - ver.get_width() - 18, self.h - ver.get_height() - 14))

        if self.fade > 0.0:
            overlay = pygame.Surface((self.w, self.h), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, int(255 * self.fade)))
            screen.blit(overlay, (0, 0))
