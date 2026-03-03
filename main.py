from __future__ import annotations

import sys
from typing import NoReturn

import pygame

from simulation.config import WINDOW_CONFIG
from simulation.environment import PCBAEnvironment
from simulation.embodied_agent import EmbodiedAgent


def run() -> None:
    pygame.init()
    try:
        screen = pygame.display.set_mode(
            (WINDOW_CONFIG.width, WINDOW_CONFIG.height)
        )
        pygame.display.set_caption(WINDOW_CONFIG.title)

        clock = pygame.time.Clock()

        environment = PCBAEnvironment(screen)
        agent = EmbodiedAgent(environment=environment)

        running: bool = True
        while running:
            dt_ms: float = clock.tick(WINDOW_CONFIG.fps)
            dt_seconds: float = dt_ms / 1000.0

            pressed = pygame.key.get_pressed()
            agent.handle_continuous_keyboard(pressed)

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    running = False
                else:
                    agent.handle_discrete_event(event)

            agent.step(dt_seconds)

            gantry_rect = agent.get_gantry_rect()
            overlay = agent.build_overlay_lines()
            environment.draw(
                gantry_rect=gantry_rect,
                overlay_lines=overlay,
                camera_patch=agent.last_camera_patch,
                detections=agent.last_detections,
                inspection_results=agent.inspection_results,
            )
            pygame.display.flip()
    finally:
        pygame.quit()


def main() -> NoReturn:
    try:
        run()
    except Exception as exc:
        # Top-level mission-critical guard: fail closed with a clear message.
        print(f"Fatal error in simulation: {exc}", file=sys.stderr)
        sys.exit(1)
    else:
        sys.exit(0)


if __name__ == "__main__":
    main()

