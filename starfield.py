import random
import pygame


class Starfield:
    def __init__(self, width, height, count=240, seed=1337):
        self.width = width
        self.height = height

        rng = random.Random(seed)
        self.stars = []

        for _ in range(count):
            x = rng.uniform(-width * 2, width * 3)
            y = rng.uniform(-height * 2, height * 3)

            layer = rng.choice([0, 1, 2])
            if layer == 0:
                size = 1
                alpha = 60
                parallax = 0.25
            elif layer == 1:
                size = 1
                alpha = 90
                parallax = 0.45
            else:
                size = 2
                alpha = 120
                parallax = 0.7

            self.stars.append((x, y, size, alpha, parallax))

        self._overlay = pygame.Surface((width, height), pygame.SRCALPHA)

    def draw(self, screen, camera_offset, zoom):
        self._overlay.fill((0, 0, 0, 0))

        w, h = self.width, self.height
        cx, cy = camera_offset.x, camera_offset.y
        ox, oy = w * 0.5, h * 0.5

        for x, y, size, alpha, parallax in self.stars:
            
            sx = ((x - cx * parallax) - ox) * zoom + ox
            sy = ((y - cy * parallax) - oy) * zoom + oy

            if sx < -10 or sy < -10 or sx > w + 10 or sy > h + 10:
                continue

            pygame.draw.circle(
                self._overlay,
                (255, 255, 255, alpha),
                (int(sx), int(sy)),
                size,
            )

        screen.blit(self._overlay, (0, 0))
