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
        self.trail_timer = 0.0

        self.last_acc = pygame.Vector2(0, 0)

        
        self.user_acc = pygame.Vector2(0, 0)

    def apply_force(self, force, dt):
        if self.mass <= 0:
            self.last_acc.update(0, 0)
            return

        acc = (force / self.mass) + self.user_acc
        self.vel += acc * dt
        self.last_acc = acc

    def update(self, dt):
        self.pos += self.vel * dt

        self.trail_timer += dt
        if self.trail_timer >= 0.05:
            self.trail.append(self.pos.copy())
            self.trail_timer = 0.0
            if len(self.trail) > 200:
                self.trail.pop(0)

    def draw(self, screen, camera_offset, zoom, draw_trail=True):
        if draw_trail and len(self.trail) > 1:
            pts = [((p - camera_offset) * zoom) for p in self.trail]
            pygame.draw.lines(screen, self.color, False, pts, 1)

        sp = (self.pos - camera_offset) * zoom
        r = max(1, int(self.radius * zoom))
        pygame.draw.circle(screen, self.color, (int(sp.x), int(sp.y)), r)

    def _draw_arrow(self, screen, start, vec, color, width=2, max_len=220):
        length = vec.length()
        if length < 1e-6:
            return

        if length > max_len:
            vec = vec * (max_len / length)

        end = start + vec
        pygame.draw.line(screen, color, (int(start.x), int(start.y)), (int(end.x), int(end.y)), width)

        
        ang = vec.as_polar()[1]
        left = pygame.Vector2(12, 0).rotate(ang + 150)
        right = pygame.Vector2(12, 0).rotate(ang - 150)
        p1 = end + left
        p2 = end + right
        pygame.draw.line(screen, color, (int(end.x), int(end.y)), (int(p1.x), int(p1.y)), width)
        pygame.draw.line(screen, color, (int(end.x), int(end.y)), (int(p2.x), int(p2.y)), width)

    def draw_vectors(self, screen, camera_offset, zoom, show_vel, show_acc):
        origin = (self.pos - camera_offset) * zoom

        if show_vel:
            v_screen = self.vel * (0.12 * zoom)
            self._draw_arrow(screen, origin, v_screen, (120, 220, 160), width=2, max_len=220)

        if show_acc:
            a_screen = self.last_acc * (6.0 * zoom)
            self._draw_arrow(screen, origin, a_screen, (255, 120, 120), width=2, max_len=220)
