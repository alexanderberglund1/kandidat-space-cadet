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
from starfield import Starfield
from hud import HUD


PLANET_PRESETS = {
    1: {"mass": 30, "radius": 6, "color": (160, 190, 255)},
    2: {"mass": 80, "radius": 10, "color": (180, 255, 200)},
    3: {"mass": 150, "radius": 14, "color": (255, 180, 140)},
}

MIN_DRAG_DISTANCE = 15
VELOCITY_SCALE = 0.4
DESPAWN_DISTANCE = 4000


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

        self.show_labels = False
        self.show_trails = True

        self.follow_target = None

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

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                return "MENU"

            if event.key == pygame.K_h:
                self.hud.toggle()

            if event.key == pygame.K_TAB:
                self.hud.toggle_controls()

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

            elif event.key == pygame.K_d:
                self.bodies = create_sandbox_demo(self.w, self.h)
                self.follow_target = None

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

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            picked = self._pick_body_at_screen(event.pos)
            if picked is not None:
                self.follow_target = picked
                self.dragging = False
                self.drag_start_world = None
                self.drag_current_world = None
                self.predicted_cache = []
                self.last_predict_pos = None
                self.last_predict_vel = None
            else:
                self.dragging = True
                self.drag_start_world = screen_to_world(pygame.Vector2(event.pos), self.camera_offset, self.zoom)
                self.drag_current_world = self.drag_start_world
                self.predicted_cache = []
                self.last_predict_pos = None
                self.last_predict_vel = None

        elif event.type == pygame.MOUSEMOTION and self.dragging:
            self.drag_current_world = screen_to_world(pygame.Vector2(event.pos), self.camera_offset, self.zoom)

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

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 3:
            self.panning = True
            self.pan_start_screen = pygame.Vector2(event.pos)
            self.pan_start_offset = self.camera_offset.copy()
            self.follow_target = None

        elif event.type == pygame.MOUSEMOTION and self.panning:
            delta = pygame.Vector2(event.pos) - self.pan_start_screen
            self.camera_offset = self.pan_start_offset - delta / self.zoom

        elif event.type == pygame.MOUSEBUTTONUP and event.button == 3:
            self.panning = False

        return None

    def update(self, dt, compute_gravity):
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

        if self.follow_target is not None:
            sp = world_to_screen(self.follow_target.pos, self.camera_offset, self.zoom)
            r = max(6, int((getattr(self.follow_target, "radius", 10) + 8) * self.zoom))
            pygame.draw.circle(screen, (240, 240, 240), (int(sp.x), int(sp.y)), r, 2)

        if self.show_labels:
            for body in self.bodies:
                if not body.name:
                    continue
                sp = (body.pos - self.camera_offset) * self.zoom
                label = self.font_label.render(body.name, True, (230, 230, 230))
                screen.blit(label, (int(sp.x) + 10, int(sp.y) - 18))

        if self.dragging and self.drag_start_world and self.drag_current_world:
            direction = self.drag_current_world - self.drag_start_world
            initial_velocity = direction * VELOCITY_SCALE

            need_recalc = (
                self.last_predict_pos is None
                or self.last_predict_vel is None
                or (self.drag_start_world - self.last_predict_pos).length() >= 3.0
                or (initial_velocity - self.last_predict_vel).length() >= 0.8
            )

            if need_recalc:
                stars = [b for b in self.bodies if b.is_star]
                self.predicted_cache = predict_orbit(self.drag_start_world, initial_velocity, stars)
                self.last_predict_pos = self.drag_start_world.copy()
                self.last_predict_vel = initial_velocity.copy()

            draw_faded_orbit(
                screen,
                self.orbit_overlay,
                self.predicted_cache,
                self.camera_offset,
                self.zoom,
                (120, 140, 255),
            )

        if self.dragging and self.drag_start_world and self.drag_current_world:
            s_start = world_to_screen(self.drag_start_world, self.camera_offset, self.zoom)
            s_curr = world_to_screen(self.drag_current_world, self.camera_offset, self.zoom)

            preset = PLANET_PRESETS[self.current_preset]
            pygame.draw.circle(
                screen,
                preset["color"],
                (int(s_start.x), int(s_start.y)),
                max(1, int(preset["radius"] * self.zoom)),
            )
            pygame.draw.line(
                screen,
                (200, 200, 200),
                (int(s_start.x), int(s_start.y)),
                (int(s_curr.x), int(s_curr.y)),
                1,
            )

        follow_text = "Off" if self.follow_target is None else (self.follow_target.name or "Object")
        status = [
            f"Zoom {self.zoom:.2f}   Time x{self.time_scale:.1f}   Preset {self.current_preset}   Follow {follow_text}"
        ]
        controls = "LMB create / click body to follow   RMB pan   Scroll zoom   F follow   C center   T trails   L labels   R reset   D demo   TAB help   ESC menu"
        self.hud.draw(screen, "SANDBOX", status, controls_line=controls)
