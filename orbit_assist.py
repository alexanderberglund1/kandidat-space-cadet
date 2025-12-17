import pygame


def _dominant_star(pos, stars):
    if not stars:
        return None
    best = None
    best_score = -1.0
    for s in stars:
        dx = s.pos.x - pos.x
        dy = s.pos.y - pos.y
        r2 = dx * dx + dy * dy
        if r2 <= 0:
            continue
        score = s.mass / r2
        if score > best_score:
            best_score = score
            best = s
    return best


def classify_orbit(pos, vel, stars, G=1.0, softening=1200.0):
    star = _dominant_star(pos, stars)
    if star is None:
        return "UNKNOWN"

    r = (star.pos - pos).length()
    if r <= 0:
        return "UNKNOWN"

    mu = G * star.mass
    v2 = vel.length_squared()

    eps = 0.5 * v2 - mu / (r + softening * 0.001)
    return "BOUND" if eps < 0 else "ESCAPE"


def predict_orbit(start_pos, start_vel, stars, steps=400, dt=0.06, G=1.0, softening=1200.0):
    pos = pygame.Vector2(start_pos)
    vel = pygame.Vector2(start_vel)

    pts = []
    for _ in range(steps):
        acc = pygame.Vector2(0, 0)

        for s in stars:
            dx = s.pos.x - pos.x
            dy = s.pos.y - pos.y
            dist_sq = dx * dx + dy * dy + softening
            dist = dist_sq ** 0.5
            if dist == 0.0:
                continue

            inv_dist = 1.0 / dist
            a_mag = (G * s.mass) / dist_sq
            acc.x += dx * inv_dist * a_mag
            acc.y += dy * inv_dist * a_mag

        vel += acc * dt
        pos += vel * dt
        pts.append(pos.copy())

    return pts


def draw_faded_orbit(screen, overlay, points, camera_offset, zoom, color):
    if len(points) < 2:
        return

    overlay.fill((0, 0, 0, 0))

    n = len(points) - 1
    for i in range(n):
        p1 = (points[i] - camera_offset) * zoom
        p2 = (points[i + 1] - camera_offset) * zoom

        t = i / max(1, n)
        alpha = int(160 * (1.0 - t))
        if alpha <= 0:
            break

        pygame.draw.line(
            overlay,
            (color[0], color[1], color[2], alpha),
            (int(p1.x), int(p1.y)),
            (int(p2.x), int(p2.y)),
            2 if zoom > 1.2 else 1,
        )

    screen.blit(overlay, (0, 0))
