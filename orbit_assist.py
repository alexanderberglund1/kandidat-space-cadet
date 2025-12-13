import pygame
from physics import G


def predict_orbit(start_pos, start_vel, stars, steps=180, dt=0.06, softening=1000.0):
    temp_pos = start_pos.copy()
    temp_vel = start_vel.copy()
    points = []

    if not stars:
        return points

    star_data = [(s.pos.x, s.pos.y, s.mass) for s in stars]

    for _ in range(steps):
        ax = 0.0
        ay = 0.0

        px = temp_pos.x
        py = temp_pos.y

        for sx, sy, sm in star_data:
            dx = sx - px
            dy = sy - py
            dist_sq = dx * dx + dy * dy + softening
            dist = dist_sq ** 0.5
            if dist == 0.0:
                continue
            inv_dist = 1.0 / dist
            accel_mag = (G * sm) / dist_sq
            ax += dx * inv_dist * accel_mag
            ay += dy * inv_dist * accel_mag

        temp_vel.x += ax * dt
        temp_vel.y += ay * dt
        temp_pos.x += temp_vel.x * dt
        temp_pos.y += temp_vel.y * dt
        points.append(temp_pos.copy())

    return points


def draw_faded_orbit(surface, overlay, points, camera_offset, zoom, color_rgb):
    if len(points) < 2:
        return

    overlay.fill((0, 0, 0, 0))
    w, h = surface.get_size()
    total = len(points)

    for i in range(total - 1):
        if i % 2 != 0:
            continue

        alpha = int(190 * (1.0 - i / total))
        if alpha <= 0:
            break

        p1 = (points[i] - camera_offset) * zoom
        p2 = (points[i + 1] - camera_offset) * zoom

        if (p1.x < -200 and p2.x < -200) or (p1.x > w + 200 and p2.x > w + 200):
            continue
        if (p1.y < -200 and p2.y < -200) or (p1.y > h + 200 and p2.y > h + 200):
            continue

        pygame.draw.line(
            overlay,
            (color_rgb[0], color_rgb[1], color_rgb[2], alpha),
            (int(p1.x), int(p1.y)),
            (int(p2.x), int(p2.y)),
            1,
        )

    surface.blit(overlay, (0, 0))
