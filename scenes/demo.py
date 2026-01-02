import pygame

from bodies import Body
from camera import (
    screen_to_world,
    clamp_zoom,
    desired_camera_offset_for_target,
    smooth_follow,
    world_to_screen,
)
from physics import G
from starfield import Starfield
from hud import HUD
from inspector import InspectorPanel
from scenes.pause_menu import PauseMenu


DOUBLECLICK_MS = 320


def circular_speed(star_mass, r):
    if r <= 0:
        return 0.0
    return (G * star_mass / r) ** 0.5


def create_solar_system(center):
    cx, cy = center

    sun = Body(
        (cx, cy),
        (0, 0),
        mass=12000,
        radius=24,
        color=(250, 220, 120),
        is_star=True,
        name="Sun",
    )

    planet_data = [
        ("Mercury", 120, (180, 190, 210), 6, 14),
        ("Venus", 170, (230, 210, 170), 7, 18),
        ("Earth", 220, (130, 175, 255), 8, 20),
        ("Mars", 270, (255, 170, 130), 7, 16),
        ("Jupiter", 360, (210, 190, 150), 12, 60),
        ("Saturn", 440, (235, 215, 160), 11, 50),
        ("Uranus", 520, (175, 225, 235), 9, 40),
        ("Neptune", 600, (130, 165, 255), 9, 40),
        ("Pluto", 680, (210, 210, 210), 6, 12),
    ]

    bodies = [sun]

    for name, r, col, radius, mass in planet_data:
        pos = pygame.Vector2(sun.pos.x + r, sun.pos.y)
        v = circular_speed(sun.mass, r)
        vel = pygame.Vector2(0, -v)

        planet = Body(pos, vel, mass=mass, radius=radius, color=col, name=name)
        planet.parent_star = sun
        bodies.append(planet)

    return bodies


def compute_demo_forces(bodies, softening=1200.0):
    forces = [pygame.Vector2(0, 0) for _ in bodies]

    for i, body in enumerate(bodies):
        if body.is_star:
            continue

        star = getattr(body, "parent_star", None)
        if star is None:
            continue

        dx = star.pos.x - body.pos.x
        dy = star.pos.y - body.pos.y

        dist_sq = dx * dx + dy * dy + softening
        dist = dist_sq ** 0.5
        if dist == 0.0:
            continue

        inv_dist = 1.0 / dist
        force_mag = G * body.mass * star.mass / dist_sq
        forces[i] = pygame.Vector2(dx * inv_dist * force_mag, dy * inv_dist * force_mag)

    return forces


class DemoScene:
    def __init__(self, fonts, size):
        self.font_ui = fonts["ui"]
        self.font_label = fonts["label"]
        self.w, self.h = size

        self.starfield = Starfield(self.w, self.h, count=300, seed=2024)
        self.hud = HUD(self.font_ui)

        self.inspector = InspectorPanel(self.font_ui, (self.w, self.h))
        self.inspector.set_mode("demo")

        
        self.pause_menu = PauseMenu(fonts, (self.w, self.h))
        self._paused_before_menu = False

        self.bodies = create_solar_system((self.w / 2, self.h / 2))

        self.zoom = 1.0
        self.camera_offset = pygame.Vector2(0, 0)

        self.panning = False
        self.pan_start_screen = None
        self.pan_start_offset = None

        self.show_labels = True
        self.show_trails = True

        self.follow_target = None
        self.hover_target = None

        self.paused = False  

        self._last_click_ms = 0
        self._last_click_body = None

    def _follow_candidates(self):
        planets = [b for b in self.bodies if not getattr(b, "is_star", False)]
        return planets if planets else list(self.bodies)

    def _cycle_follow(self):
        candidates = self._follow_candidates()
        if not candidates:
            self.follow_target = None
            return

        if self.follow_target not in candidates:
            self.follow_target = candidates[0]
            return

        i = candidates.index(self.follow_target)
        self.follow_target = candidates[(i + 1) % len(candidates)]
        self.inspector.set_selected(self.follow_target)

    def _center_on_target(self, target):
        if target is None:
            return
        self.camera_offset = desired_camera_offset_for_target(target.pos, (self.w, self.h), self.zoom)

    def _pick_body_at_screen(self, screen_pos):
        p = pygame.Vector2(screen_pos)
        best = None
        best_d = 1e9

        for b in self.bodies:
            if getattr(b, "is_star", False):
                continue
            sp = world_to_screen(b.pos, self.camera_offset, self.zoom)
            r = max(8, int((getattr(b, "radius", 10) + 6) * self.zoom))
            d = (sp - p).length()
            if d <= r and d < best_d:
                best = b
                best_d = d

        return best

    def _double_clicked(self, body):
        now = pygame.time.get_ticks()
        ok = body is not None and self._last_click_body is body and (now - self._last_click_ms) <= DOUBLECLICK_MS
        self._last_click_ms = now
        self._last_click_body = body
        return ok

    def _open_pause_menu(self):
        self._paused_before_menu = self.paused
        self.pause_menu.open = True
        self.paused = True

    def _close_pause_menu(self):
        self.pause_menu.close()
        self.paused = self._paused_before_menu

    def handle_event(self, event):
        
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            if self.pause_menu.open:
                self._close_pause_menu()
            else:
                self._open_pause_menu()
            return None

        
        if self.pause_menu.open:
            action = self.pause_menu.handle_event(event)
            if action == "RESUME":
                self._close_pause_menu()
                return None
            if action == "MENU":
                self._close_pause_menu()
                return "MENU"
            if action == "QUIT":
                self._close_pause_menu()
                return "QUIT"
            return None

        if self.inspector.handle_event(event):
            return None

        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_h:
                self.hud.toggle()

            if event.key == pygame.K_TAB:
                self.hud.toggle_controls()

            if event.key == pygame.K_SPACE:
                self.paused = not self.paused

            if event.key == pygame.K_l:
                self.show_labels = not self.show_labels
            if event.key == pygame.K_t:
                self.show_trails = not self.show_trails

            if event.key == pygame.K_f:
                self._cycle_follow()

            if event.key == pygame.K_c:
                target = self.follow_target
                if target is None:
                    stars = [b for b in self.bodies if getattr(b, "is_star", False)]
                    target = stars[0] if stars else (self.bodies[0] if self.bodies else None)
                self._center_on_target(target)

        if event.type == pygame.MOUSEWHEEL:
            mouse_screen = pygame.Vector2(pygame.mouse.get_pos())
            before = screen_to_world(mouse_screen, self.camera_offset, self.zoom)

            if event.y > 0:
                self.zoom *= 1.1
            elif event.y < 0:
                self.zoom /= 1.1
            self.zoom = clamp_zoom(self.zoom)

            after = screen_to_world(mouse_screen, self.camera_offset, self.zoom)
            self.camera_offset += before - after

        if event.type == pygame.MOUSEMOTION:
            self.hover_target = self._pick_body_at_screen(event.pos)

            if self.panning:
                delta = pygame.Vector2(event.pos) - self.pan_start_screen
                self.camera_offset = self.pan_start_offset - delta / self.zoom

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            picked = self._pick_body_at_screen(event.pos)
            if picked is not None:
                dbl = self._double_clicked(picked)
                self.follow_target = picked
                self.inspector.set_selected(picked)
                if dbl:
                    self._center_on_target(picked)

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 3:
            self.panning = True
            self.pan_start_screen = pygame.Vector2(event.pos)
            self.pan_start_offset = self.camera_offset.copy()
            self.follow_target = None

        elif event.type == pygame.MOUSEBUTTONUP and event.button == 3:
            self.panning = False

        return None

    def update(self, dt):
        dt = min(dt, 1 / 120)

        stars = [b for b in self.bodies if getattr(b, "is_star", False)]
        self.inspector.set_context_stars(stars)

        if self.paused:
            if self.follow_target is not None:
                self.camera_offset = smooth_follow(
                    self.camera_offset,
                    self.follow_target.pos,
                    (self.w, self.h),
                    self.zoom,
                    dt,
                    strength=10.0,
                )
            return None

        forces = compute_demo_forces(self.bodies)
        for body, force in zip(self.bodies, forces):
            body.apply_force(force, dt)

        for body in self.bodies:
            body.update(dt)

        if self.inspector.selected is not None and self.inspector.selected not in self.bodies:
            self.inspector.clear()

        if self.follow_target is not None:
            self.camera_offset = smooth_follow(
                self.camera_offset,
                self.follow_target.pos,
                (self.w, self.h),
                self.zoom,
                dt,
                strength=10.0,
            )

        return None

    def _draw_labels(self, screen):
        if not self.show_labels:
            return

        for body in self.bodies:
            if getattr(body, "is_star", False):
                continue

            name = getattr(body, "name", None)
            if not name:
                continue

            sp = world_to_screen(body.pos, self.camera_offset, self.zoom)
            r = max(6, int(getattr(body, "radius", 10) * self.zoom))

            label = self.font_label.render(str(name), True, (205, 205, 205))
            shadow = self.font_label.render(str(name), True, (20, 20, 25))

            x = int(sp.x - label.get_width() // 2)
            y = int(sp.y - r - 14)

            screen.blit(shadow, (x + 1, y + 1))
            screen.blit(label, (x, y))

    def draw(self, screen):
        screen.fill((5, 5, 15))
        self.starfield.draw(screen, self.camera_offset, self.zoom)

        for body in self.bodies:
            body.draw(screen, self.camera_offset, self.zoom, draw_trail=self.show_trails)

        self._draw_labels(screen)

        if self.hover_target is not None and self.hover_target is not self.follow_target:
            sp = world_to_screen(self.hover_target.pos, self.camera_offset, self.zoom)
            r = max(6, int((getattr(self.hover_target, "radius", 10) + 10) * self.zoom))
            pygame.draw.circle(screen, (180, 180, 180), (int(sp.x), int(sp.y)), r, 1)

        if self.follow_target is not None:
            sp = world_to_screen(self.follow_target.pos, self.camera_offset, self.zoom)
            r = max(6, int((getattr(self.follow_target, "radius", 10) + 8) * self.zoom))
            pygame.draw.circle(screen, (240, 240, 240), (int(sp.x), int(sp.y)), r, 2)

        if self.inspector.selected is not None:
            self.inspector.selected.draw_vectors(
                screen,
                self.camera_offset,
                self.zoom,
                show_vel=self.inspector.show_velocity_vector,
                show_acc=self.inspector.show_acceleration_vector,
            )

        follow_text = "Off" if self.follow_target is None else (self.follow_target.name or "Object")
        status = [f"Zoom {self.zoom:.2f}   Follow {follow_text}" + ("   PAUSED" if self.paused else "")]
        controls = (
            "Click planet inspect+follow   Doubleclick: center   Scroll zoom   RMB pan   SPACE pause   "
            "F cycle   C center   T trails   L labels   TAB help   ESC options"
        )

        right_margin = self.inspector.panel_w + 30 if self.inspector.selected is not None else 0
        if right_margin > 0:
            clip_w = max(200, screen.get_width() - right_margin - 10)
            screen.set_clip(pygame.Rect(0, 0, clip_w, screen.get_height()))
        else:
            screen.set_clip(None)

        self.hud.draw(screen, "SOLAR SYSTEM", status, controls_line=controls, right_margin=right_margin)
        screen.set_clip(None)

        self.inspector.draw(screen)

        
        self.pause_menu.draw(screen, title="OPTIONS")
