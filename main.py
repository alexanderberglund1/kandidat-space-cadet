import sys
import pygame

from physics import compute_gravity
from scenes.menu import MenuScene
from scenes.sandbox import SandboxScene
from scenes.demo import DemoScene

WIDTH = 1920
HEIGHT = 1080
FPS = 60


def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Space Cadet")
    clock = pygame.time.Clock()

    fonts = {
        "title": pygame.font.SysFont(None, 64),
        "ui": pygame.font.SysFont(None, 20),
        "label": pygame.font.SysFont(None, 18),
    }

    menu = MenuScene(fonts, (WIDTH, HEIGHT))

    state = "MENU"
    sandbox = None
    demo = None

    running = True
    while running:
        dt = clock.tick(FPS) / 1000.0

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                break

            if state == "MENU":
                next_state = menu.handle_event(event)
                if next_state == "QUIT":
                    running = False
                    break

                if next_state == "SANDBOX":
                    sandbox = SandboxScene(fonts, (WIDTH, HEIGHT))
                    state = "SANDBOX"

                elif next_state == "DEMO":
                    demo = DemoScene(fonts, (WIDTH, HEIGHT))
                    state = "DEMO"

            elif state == "SANDBOX":
                next_state = sandbox.handle_event(event)
                if next_state == "MENU":
                    state = "MENU"
                elif next_state == "QUIT":
                    running = False
                    break

            elif state == "DEMO":
                next_state = demo.handle_event(event)
                if next_state == "MENU":
                    state = "MENU"
                elif next_state == "QUIT":
                    running = False
                    break

        if not running:
            break

        if state == "MENU":
            menu.update(dt)
            menu.draw(screen)

        elif state == "SANDBOX":
            sandbox.update(dt, compute_gravity)
            sandbox.draw(screen)

        elif state == "DEMO":
            demo.update(dt)
            demo.draw(screen)

        pygame.display.flip()

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
