from bodies import Body


def resolve_collisions(bodies):
    new_bodies = []
    merged = set()

    for i in range(len(bodies)):
        if i in merged:
            continue

        a = bodies[i]

        for j in range(i + 1, len(bodies)):
            if j in merged:
                continue

            b = bodies[j]

            # stjärna + stjärna: ignorera (dem ska inte äta varandra)
            if a.is_star and b.is_star:
                continue

            dist = (b.pos - a.pos).length()
            if dist > a.radius + b.radius:
                continue

            # stjärna absorberar planet (stjärnan ändras inte)
            if a.is_star and not b.is_star:
                merged.add(j)
                continue
            if b.is_star and not a.is_star:
                merged.add(i)
                a = b
                continue

            # planet + planet -> slå ihop
            total_mass = a.mass + b.mass
            if total_mass == 0:
                continue

            new_vel = (a.vel * a.mass + b.vel * b.mass) / total_mass
            new_pos = (a.pos * a.mass + b.pos * b.mass) / total_mass
            new_radius = int((a.radius ** 3 + b.radius ** 3) ** (1 / 3))
            color = a.color if a.mass >= b.mass else b.color
            name = a.name if (a.mass >= b.mass) else b.name

            a = Body(new_pos, new_vel, total_mass, new_radius, color, name=name)
            merged.add(j)

        new_bodies.append(a)

    return new_bodies


def remove_far_bodies(bodies, despawn_distance=4000):
    if not bodies:
        return bodies

    center = None
    for b in bodies:
        if b.is_star:
            center = b.pos
            break
    if center is None:
        center = bodies[0].pos

    kept = []
    for b in bodies:
        if b.is_star:
            kept.append(b)
            continue
        if (b.pos - center).length() < despawn_distance:
            kept.append(b)
    return kept
