import pygame


class Body:
    def __init__(self, pos, vel, mass, radius, color, is_star=False, name=None):
        self.pos = pygame.Vector2(pos)
        self.vel = pygame.Vector2(vel)
        self.mass = mass
        self.radius = radius
        self.color = color
        self.is_star = is_star
        self.name = name

        self.trail = []
        self.max_trail_length = 250

    def apply_force(self, force, dt):
        if self.is_star:
            return
        self.vel += (force / self.mass) * dt

    def update(self, dt):
        if not self.is_star:
            self.pos += self.vel * dt
        self._update_trail()

    def _update_trail(self):
        self.trail.append(self.pos.copy())
        if len(self.trail) > self.max_trail_length:
            self.trail.pop(0)

    def draw(self, surface, camera_offset, zoom, draw_trail=True):
        if draw_trail and len(self.trail) > 1 and not self.is_star:
            pts = []
            for p in self.trail:
                sp = (p - camera_offset) * zoom
                pts.append((int(sp.x), int(sp.y)))
            pygame.draw.lines(surface, self.color, False, pts, 1)

        sp = (self.pos - camera_offset) * zoom
        pygame.draw.circle(
            surface,
            self.color,
            (int(sp.x), int(sp.y)),
            max(1, int(self.radius * zoom)),
        )
