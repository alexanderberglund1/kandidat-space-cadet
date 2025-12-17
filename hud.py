import pygame


class HUD:
    def __init__(self, font):
        self.font = font
        self.enabled = True
        self.show_controls = True
        self.pad = 10
        self.gap = 6

    def toggle(self):
        self.enabled = not self.enabled

    def toggle_controls(self):
        self.show_controls = not self.show_controls

    def _wrap_text(self, text, max_width):
        if not text:
            return []

        words = text.split(" ")
        lines = []
        cur = ""

        for w in words:
            test = w if cur == "" else (cur + " " + w)
            if self.font.size(test)[0] <= max_width:
                cur = test
            else:
                if cur:
                    lines.append(cur)
                cur = w

        if cur:
            lines.append(cur)

        return lines

    def draw(self, screen, title, status_lines, controls_line=None, right_margin=0):
        if not self.enabled:
            return

        screen_w = screen.get_width()

        # left area available (avoid inspector area)
        available_w = max(220, screen_w - right_margin - 20)

        # build logical lines
        base_text = [str(title)] + [str(s) for s in (status_lines or [])]

        ctrl_text_lines = []
        if self.show_controls and controls_line:
            wrap_w = max(180, available_w - self.pad * 2)
            ctrl_text_lines = self._wrap_text(str(controls_line), wrap_w)

        # render surfaces and measure widths
        base_surfs = [self.font.render(t, True, (240, 240, 240)) if i == 0 else self.font.render(t, True, (210, 210, 210))
                      for i, t in enumerate(base_text)]

        ctrl_surfs = [self.font.render(t, True, (170, 170, 170)) for t in ctrl_text_lines]

        all_surfs = base_surfs + ctrl_surfs
        if not all_surfs:
            return

        max_line_w = max(s.get_width() for s in all_surfs)
        box_w = min(available_w, max_line_w + self.pad * 2)

        # height
        line_h = self.font.get_height()
        h = self.pad * 2

        # base lines
        for i, s in enumerate(base_surfs):
            h += s.get_height()
            if i != len(base_surfs) - 1:
                h += self.gap

        # controls block
        if ctrl_surfs:
            h += self.gap
            for i, s in enumerate(ctrl_surfs):
                h += s.get_height()
                if i != len(ctrl_surfs) - 1:
                    h += 4

        # draw box
        box = pygame.Surface((box_w, h), pygame.SRCALPHA)
        pygame.draw.rect(box, (0, 0, 0, 150), (0, 0, box_w, h), border_radius=12)
        pygame.draw.rect(box, (255, 255, 255, 40), (0, 0, box_w, h), width=1, border_radius=12)

        x = self.pad
        y = self.pad

        for i, surf in enumerate(base_surfs):
            box.blit(surf, (x, y))
            y += surf.get_height()
            if i != len(base_surfs) - 1:
                y += self.gap

        if ctrl_surfs:
            y += self.gap
            for i, surf in enumerate(ctrl_surfs):
                box.blit(surf, (x, y))
                y += surf.get_height()
                if i != len(ctrl_surfs) - 1:
                    y += 4

        screen.blit(box, (10, 10))
