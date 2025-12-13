import pygame


class HUD:
    def __init__(self, font, pad=10, gap=4, alpha=150, radius=12):
        self.font = font
        self.pad = pad
        self.gap = gap
        self.alpha = alpha
        self.radius = radius

        self.enabled = True
        self.show_controls = False

    def toggle(self):
        self.enabled = not self.enabled

    def toggle_controls(self):
        self.show_controls = not self.show_controls

    def draw(self, screen, title, status_lines, controls_line=None, pos=(12, 12)):
        if not self.enabled:
            return

        title_surf = self.font.render(title, True, (255, 255, 255))
        status_surfs = [self.font.render(line, True, (210, 210, 210)) for line in status_lines]

        controls_surf = None
        if self.show_controls and controls_line:
            controls_surf = self.font.render(controls_line, True, (185, 185, 185))

        all_surfs = [title_surf] + status_surfs + ([controls_surf] if controls_surf else [])
        w = max(s.get_width() for s in all_surfs) + self.pad * 2

        h = self.pad * 2 + title_surf.get_height()
        if status_surfs:
            h += self.gap + sum(s.get_height() for s in status_surfs) + self.gap * (len(status_surfs) - 1)
        if controls_surf:
            h += self.gap + controls_surf.get_height()

        panel = pygame.Surface((w, h), pygame.SRCALPHA)
        pygame.draw.rect(panel, (0, 0, 0, self.alpha), (0, 0, w, h), border_radius=self.radius)
        pygame.draw.rect(panel, (255, 255, 255, 40), (0, 0, w, h), width=1, border_radius=self.radius)

        y = self.pad
        panel.blit(title_surf, (self.pad, y))
        y += title_surf.get_height()

        if status_surfs:
            y += self.gap
            for s in status_surfs:
                panel.blit(s, (self.pad, y))
                y += s.get_height() + self.gap
            y -= self.gap

        if controls_surf:
            y += self.gap
            panel.blit(controls_surf, (self.pad, y))

        screen.blit(panel, pos)
