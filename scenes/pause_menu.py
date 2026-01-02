import pygame


class PauseMenu:
    def __init__(self, fonts, size):
        self.font_title = fonts["title"]
        self.font_ui = fonts["ui"]
        self.w, self.h = size

        self.open = False

        # Screen-space rects (VIKTIGT!)
        self.panel_rect = pygame.Rect(0, 0, 0, 0)
        self.btn_resume = pygame.Rect(0, 0, 0, 0)
        self.btn_menu = pygame.Rect(0, 0, 0, 0)
        self.btn_quit = pygame.Rect(0, 0, 0, 0)

    def set_size(self, size):
        self.w, self.h = size

    def toggle(self):
        self.open = not self.open

    def close(self):
        self.open = False

    def handle_event(self, event):
        if not self.open:
            return None

        if event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
            self.close()
            return "RESUME"

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            p = event.pos
            if self.btn_resume.collidepoint(p):
                self.close()
                return "RESUME"
            if self.btn_menu.collidepoint(p):
                self.close()
                return "MENU"
            if self.btn_quit.collidepoint(p):
                self.close()
                return "QUIT"

        return None

    def _layout(self, screen):
        w, h = screen.get_width(), screen.get_height()
        cx, cy = w // 2, h // 2

        pw, ph = 360, 240
        self.panel_rect = pygame.Rect(cx - pw // 2, cy - ph // 2, pw, ph)

        bw, bh = 260, 40
        gap = 14
        x = self.panel_rect.x + (pw - bw) // 2
        y = self.panel_rect.y + 90

        self.btn_resume = pygame.Rect(x, y, bw, bh)
        self.btn_menu = pygame.Rect(x, y + (bh + gap), bw, bh)
        self.btn_quit = pygame.Rect(x, y + 2 * (bh + gap), bw, bh)

    def draw(self, screen, title="OPTIONS"):
        if not self.open:
            return

        # Layout måste ske varje frame (ifall resolution ändras)
        self._layout(screen)

        w, h = screen.get_width(), screen.get_height()

        # Dim overlay
        dim = pygame.Surface((w, h), pygame.SRCALPHA)
        dim.fill((0, 0, 0, 140))
        screen.blit(dim, (0, 0))

        # Panel
        panel = pygame.Surface((self.panel_rect.w, self.panel_rect.h), pygame.SRCALPHA)
        pygame.draw.rect(panel, (0, 0, 0, 190), (0, 0, self.panel_rect.w, self.panel_rect.h), border_radius=18)
        pygame.draw.rect(panel, (255, 255, 255, 45), (0, 0, self.panel_rect.w, self.panel_rect.h), width=1, border_radius=18)

        # Title
        t = self.font_title.render(title, True, (235, 235, 235))
        panel.blit(t, (self.panel_rect.w // 2 - t.get_width() // 2, 22))

        # Buttons (draw in panel-local coords, but rects are screen-space)
        mx, my = pygame.mouse.get_pos()

        def draw_button(btn_rect, label):
            hovered = btn_rect.collidepoint((mx, my))
            # Convert to panel-local for drawing
            local = btn_rect.move(-self.panel_rect.x, -self.panel_rect.y)

            bg_a = 30 if hovered else 18
            bd_a = 55 if hovered else 40

            pygame.draw.rect(panel, (255, 255, 255, bg_a), local, border_radius=12)
            pygame.draw.rect(panel, (255, 255, 255, bd_a), local, width=1, border_radius=12)

            s = self.font_ui.render(label, True, (235, 235, 235))
            panel.blit(s, (local.centerx - s.get_width() // 2, local.centery - s.get_height() // 2))

        draw_button(self.btn_resume, "Resume")
        draw_button(self.btn_menu, "Main Menu")
        draw_button(self.btn_quit, "Quit")

        screen.blit(panel, self.panel_rect.topleft)
