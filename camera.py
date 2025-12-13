import pygame
import math


def world_to_screen(pos, camera_offset, zoom):
    return (pos - camera_offset) * zoom


def screen_to_world(pos, camera_offset, zoom):
    return pos / zoom + camera_offset


def clamp_zoom(z):
    return max(0.2, min(z, 5.0))


def desired_camera_offset_for_target(target_pos, screen_size, zoom):
    w, h = screen_size
    half = pygame.Vector2(w / (2.0 * zoom), h / (2.0 * zoom))
    return pygame.Vector2(target_pos) - half


def smooth_follow(camera_offset, target_pos, screen_size, zoom, dt, strength=10.0):
    desired = desired_camera_offset_for_target(target_pos, screen_size, zoom)
    alpha = 1.0 - math.exp(-strength * max(0.0, dt))
    return camera_offset + (desired - camera_offset) * alpha
