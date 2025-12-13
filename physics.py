import math
from pygame import Vector2

G = 100.0
SOFTENING = 1000.0


def compute_gravity(bodies):
    forces = [Vector2(0, 0) for _ in bodies]

    for i in range(len(bodies)):
        for j in range(i + 1, len(bodies)):
            a = bodies[i]
            b = bodies[j]

            direction = b.pos - a.pos
            dist_sq = direction.length_squared() + SOFTENING
            dist = math.sqrt(dist_sq)

            if dist == 0:
                continue

            force_mag = G * a.mass * b.mass / dist_sq
            force = direction / dist * force_mag

            forces[i] += force
            forces[j] -= force

    return forces
