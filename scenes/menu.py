import pygame


class MenuScene:
    def __init__(self, fonts):
        self.font_title = fonts["title"]
        self.font = fonts["ui"]

    def handle_event(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_1:
                return "SANDBOX"
            if event.key == pygame.K_2:
                return "DEMO"
            if event.key == pygame.K_ESCAPE:
                return "QUIT"
        return None

    def update(self, dt):
        return None

    def draw(self, screen):
        screen.fill((5, 5, 15))

        title = self.font_title.render("SPACE CADET", True, (230, 230, 230))
        screen.blit(title, (60, 60))

        y = 160
        for line in [
            "[1] Sandbox",
            "[2] Galaxy Demo",
            "[ESC] Quit",
        ]:
            surf = self.font.render(line, True, (190, 190, 190))
            screen.blit(surf, (70, y))
            y += 34
