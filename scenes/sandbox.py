import pygame

from bodies import Body
from camera import (
    world_to_screen,
    screen_to_world,
    clamp_zoom,
    desired_camera_offset_for_target,
    smooth_follow,
)
from sim import resolve_collisions, remove_far_bodies
from orbit_assist import predict_orbit, draw_faded_orbit

try:
    from orbit_assist import classify_orbit
except ImportError:
    def classify_orbit(*args, **kwargs):
        return "UNKNOWN"

from starfield import Starfield
from hud import HUD
from physics import G
from inspector import InspectorPanel
from scenes.pause_menu import PauseMenu


PLANET_PRESETS = {
    1: {"mass": 30, "radius": 6, "color": (160, 190, 255)},
    2: {"mass": 80, "radius": 10, "color": (180, 255, 200)},
    3: {"mass": 150, "radius": 14, "color": (255, 180, 140)},
}

MIN_DRAG_DISTANCE = 15
VELOCITY_SCALE = 0.4
DESPAWN_DISTANCE = 4000
DOUBLECLICK_MS = 320


def create_central_star(w, h):
    return Body(
        (w / 2, h / 2),
        (0, 0),
        mass=5000,
        radius=18,
        color=(250, 220, 120),
        is_star=True,
        name="Sun",
    )


def create_sandbox_demo(w, h):
    star = create_central_star(w, h)
    center = star.pos

    result = [star]
    distances = [130, 200, 270]
    speeds = [62, 50, 43]
    presets = [1, 2, 3]

    for d, v, preset in zip(distances, speeds, presets):
        pos = pygame.Vector2(center.x + d, center.y)
        vel = pygame.Vector2(0, -v)
        p = PLANET_PRESETS[preset]
        result.append(Body(pos, vel, p["mass"], p["radius"], p["color"]))
    return result


class SandboxScene:
    def __init__(self, fonts, size):
        self.font_ui = fonts["ui"]
        self.font_label = fonts["label"]
        self.w, self.h = size

        self.starfield = Starfield(self.w, self.h, count=300, seed=1337)
        self.hud = HUD(self.font_ui)

        self.inspector = InspectorPanel(self.font_ui, (self.w, self.h))
        self.inspector.set_mode("sandbox")

        # Pause/options overlay (ESC)
        self.pause_menu = PauseMenu(fonts, (self.w, self.h))
        self._paused_before_menu = False

        self.time_scale = 1.0
        self.current_preset = 2

        self.camera_offset = pygame.Vector2(0, 0)
        self.zoom = 1.0

        self.bodies = [create_central_star(self.w, self.h)]

        self.dragging = False
        self.drag_start_world = None
        self.drag_current_world = None

        self.panning = False
        self.pan_start_screen = None
        self.pan_start_offset = None

        self.orbit_overlay = pygame.Surface((self.w, self.h), pygame.SRCALPHA)
        self.predicted_cache = []
        self.last_predict_pos = None
        self.last_predict_vel = None
        self.last_orbit_kind = "UNKNOWN"

        self.show_labels = False
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
        # ESC togglar options overlay (alltid prio)
        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            if self.pause_menu.open:
                self._close_pause_menu()
            else:
                self._open_pause_menu()
            return None

        # När options är öppet: ät ALL input och hantera bara menyn
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

        # Inspector först
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
            elif event.key == pygame.K_t:
                self.show_trails = not self.show_trails

            elif event.key == pygame.K_1:
                self.current_preset = 1
            elif event.key == pygame.K_2:
                self.current_preset = 2
            elif event.key == pygame.K_3:
                self.current_preset = 3

            elif event.key in (pygame.K_RIGHTBRACKET, pygame.K_PERIOD):
                self.time_scale = min(15.0, self.time_scale * 1.3)
            elif event.key in (pygame.K_LEFTBRACKET, pygame.K_COMMA):
                self.time_scale = max(0.1, self.time_scale / 1.3)

            elif event.key == pygame.K_r:
                self.bodies = [create_central_star(self.w, self.h)]
                self.time_scale = 1.0
                self.follow_target = None
                self.inspector.clear()

            elif event.key == pygame.K_d:
                self.bodies = create_sandbox_demo(self.w, self.h)
                self.follow_target = None
                self.inspector.clear()

            elif event.key == pygame.K_f:
                self._cycle_follow()

            elif event.key == pygame.K_c:
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
            self.hover_target = self._pick_body_at_screen(event.pos) if not self.dragging else None

            if self.dragging:
                self.drag_current_world = screen_to_world(pygame.Vector2(event.pos), self.camera_offset, self.zoom)

            elif self.panning:
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

                self.dragging = False
                self.drag_start_world = None
                self.drag_current_world = None
                self.predicted_cache = []
                self.last_predict_pos = None
                self.last_predict_vel = None
            else:
                self.inspector.clear()
                self._double_clicked(None)

                self.dragging = True
                self.drag_start_world = screen_to_world(pygame.Vector2(event.pos), self.camera_offset, self.zoom)
                self.drag_current_world = self.drag_start_world
                self.predicted_cache = []
                self.last_predict_pos = None
                self.last_predict_vel = None

        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1 and self.dragging:
            drag_end_world = screen_to_world(pygame.Vector2(event.pos), self.camera_offset, self.zoom)
            direction = drag_end_world - self.drag_start_world

            if direction.length() >= MIN_DRAG_DISTANCE:
                preset = PLANET_PRESETS[self.current_preset]
                vel = direction * VELOCITY_SCALE
                self.bodies.append(Body(self.drag_start_world, vel, preset["mass"], preset["radius"], preset["color"]))

            self.dragging = False
            self.drag_start_world = None
            self.drag_current_world = None
            self.predicted_cache = []
            self.last_predict_pos = None
            self.last_predict_vel = None
            self.last_orbit_kind = "UNKNOWN"

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 3:
            self.panning = True
            self.pan_start_screen = pygame.Vector2(event.pos)
            self.pan_start_offset = self.camera_offset.copy()
            self.follow_target = None

        elif event.type == pygame.MOUSEBUTTONUP and event.button == 3:
            self.panning = False

        return None

    def update(self, dt, compute_gravity):
        stars = [b for b in self.bodies if getattr(b, "is_star", False)]
        self.inspector.set_context_stars(stars)

        if self.paused:
            if self.follow_target is not None:
                ui_dt = max(0.0, min(1 / 30, dt))
                self.camera_offset = smooth_follow(
                    self.camera_offset,
                    self.follow_target.pos,
                    (self.w, self.h),
                    self.zoom,
                    ui_dt,
                    strength=12.0,
                )
            return None

        dt *= self.time_scale

        forces = compute_gravity(self.bodies)
        for body, force in zip(self.bodies, forces):
            body.apply_force(force, dt)

        for body in self.bodies:
            body.update(dt)

        self.bodies = resolve_collisions(self.bodies)
        self.bodies = remove_far_bodies(self.bodies, despawn_distance=DESPAWN_DISTANCE)

        if self.follow_target is not None and self.follow_target not in self.bodies:
            self.follow_target = None

        if self.inspector.selected is not None and self.inspector.selected not in self.bodies:
            self.inspector.clear()

        if self.follow_target is not None:
            ui_dt = max(0.0, min(1 / 30, dt / max(0.0001, self.time_scale)))
            self.camera_offset = smooth_follow(
                self.camera_offset,
                self.follow_target.pos,
                (self.w, self.h),
                self.zoom,
                ui_dt,
                strength=12.0,
            )

        return None

    def draw(self, screen):
        screen.fill((5, 5, 15))
        self.starfield.draw(screen, self.camera_offset, self.zoom)

        for body in self.bodies:
            body.draw(screen, self.camera_offset, self.zoom, draw_trail=self.show_trails)

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

        orbit_kind = "UNKNOWN"
        orbit_color = (120, 140, 255)

        if self.dragging and self.drag_start_world and self.drag_current_world:
            direction = self.drag_current_world - self.drag_start_world
            initial_velocity = direction * VELOCITY_SCALE

            need_recalc = (
                self.last_predict_pos is None
                or self.last_predict_vel is None
                or (self.drag_start_world - self.last_predict_pos).length() >= 3.0
                or (initial_velocity - self.last_predict_vel).length() >= 0.8
            )

            stars = [b for b in self.bodies if getattr(b, "is_star", False)]

            if need_recalc:
                orbit_kind = classify_orbit(self.drag_start_world, initial_velocity, stars, G=G)
                self.last_orbit_kind = orbit_kind
                self.predicted_cache = predict_orbit(self.drag_start_world, initial_velocity, stars, G=G)
                self.last_predict_pos = self.drag_start_world.copy()
                self.last_predict_vel = initial_velocity.copy()
            else:
                orbit_kind = self.last_orbit_kind

            if orbit_kind == "BOUND":
                orbit_color = (120, 220, 160)
            elif orbit_kind == "ESCAPE":
                orbit_color = (255, 130, 120)

            draw_faded_orbit(
                screen,
                self.orbit_overlay,
                self.predicted_cache,
                self.camera_offset,
                self.zoom,
                orbit_color,
            )

        follow_text = "Off" if self.follow_target is None else (self.follow_target.name or "Object")
        orbit_text = {"BOUND": "Bound", "ESCAPE": "Escape", "UNKNOWN": "-"}[orbit_kind] if self.dragging else "-"

        status = [
            f"Zoom {self.zoom:.2f}   Time x{self.time_scale:.1f}   Preset {self.current_preset}   Follow {follow_text}",
            f"Orbit {orbit_text}" + ("   PAUSED" if self.paused else ""),
        ]

        controls = (
            "LMB drag create / click inspect+follow   Doubleclick: center   RMB pan   Scroll zoom   "
            "SPACE pause   F cycle   C center   T trails   L labels   R reset   D demo   TAB help   ESC options"
        )

        right_margin = self.inspector.panel_w + 30 if self.inspector.selected is not None else 0
        if right_margin > 0:
            clip_w = max(200, screen.get_width() - right_margin - 10)
            screen.set_clip(pygame.Rect(0, 0, clip_w, screen.get_height()))
        else:
            screen.set_clip(None)

        self.hud.draw(screen, "SANDBOX", status, controls_line=controls, right_margin=right_margin)
        screen.set_clip(None)

        self.inspector.draw(screen)

        # IMPORTANT: ensure no clipping affects the overlay
        screen.set_clip(None)
        self.pause_menu.draw(screen, title="OPTIONS")
