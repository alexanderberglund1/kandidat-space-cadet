import math
import pygame

from physics import G, SOFTENING


class InspectorPanel:
    def __init__(self, font, size):
        self.font = font
        self.w, self.h = size

        self.enabled = True
        self.selected = None

        self.show_velocity_vector = True
        self.show_acceleration_vector = True

        self.panel_w = 320
        self.pad = 14

        self.mode = "demo"
        self._stars = []

        self._rect = pygame.Rect(self.w - self.panel_w - 14, 14, self.panel_w, 10)
        self._btn_vel = pygame.Rect(0, 0, 0, 0)
        self._btn_acc = pygame.Rect(0, 0, 0, 0)
        self._btn_close = pygame.Rect(0, 0, 0, 0)

        self._vx_minus = self._vx_plus = pygame.Rect(0, 0, 0, 0)
        self._vy_minus = self._vy_plus = pygame.Rect(0, 0, 0, 0)
        self._tx_minus = self._tx_plus = pygame.Rect(0, 0, 0, 0)
        self._ty_minus = self._ty_plus = pygame.Rect(0, 0, 0, 0)
        self._reset_tweaks = pygame.Rect(0, 0, 0, 0)

        self.vel_step = 5.0
        self.acc_step = 1.0

        self._row_h = 32
        self._toggle_h = 34
        self._gap = 10

    def set_size(self, size):
        self.w, self.h = size
        self._rect.x = self.w - self.panel_w - 14
        self._rect.y = 14
        self._rect.width = self.panel_w

    def set_mode(self, mode):
        self.mode = mode

    def set_context_stars(self, stars):
        self._stars = stars or []

    def set_selected(self, body):
        self.selected = body

    def clear(self):
        self.selected = None

    def _has_tweaks(self, body):
        return hasattr(body, "user_acc") and not getattr(body, "is_star", False)

    def handle_event(self, event):
        if not self.enabled or self.selected is None:
            return False

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            p = event.pos

            if self._btn_close.collidepoint(p):
                self.clear()
                return True

            if self._btn_vel.collidepoint(p):
                self.show_velocity_vector = not self.show_velocity_vector
                return True

            if self._btn_acc.collidepoint(p):
                self.show_acceleration_vector = not self.show_acceleration_vector
                return True

            b = self.selected
            if self.mode == "sandbox" and self._has_tweaks(b):
                if self._vx_minus.collidepoint(p):
                    b.vel.x -= self.vel_step
                    return True
                if self._vx_plus.collidepoint(p):
                    b.vel.x += self.vel_step
                    return True
                if self._vy_minus.collidepoint(p):
                    b.vel.y -= self.vel_step
                    return True
                if self._vy_plus.collidepoint(p):
                    b.vel.y += self.vel_step
                    return True

                if self._tx_minus.collidepoint(p):
                    b.user_acc.x -= self.acc_step
                    return True
                if self._tx_plus.collidepoint(p):
                    b.user_acc.x += self.acc_step
                    return True
                if self._ty_minus.collidepoint(p):
                    b.user_acc.y -= self.acc_step
                    return True
                if self._ty_plus.collidepoint(p):
                    b.user_acc.y += self.acc_step
                    return True

                if self._reset_tweaks.collidepoint(p):
                    b.user_acc.update(0, 0)
                    return True

        return False

    def _text(self, s, color=(230, 230, 230)):
        return self.font.render(s, True, color)

    def _panel_bg(self, surf):
        pygame.draw.rect(
            surf,
            (0, 0, 0, 165),
            (0, 0, surf.get_width(), surf.get_height()),
            border_radius=16,
        )
        pygame.draw.rect(
            surf,
            (255, 255, 255, 45),
            (0, 0, surf.get_width(), surf.get_height()),
            width=1,
            border_radius=16,
        )

    def _draw_toggle(self, screen, rect, label, on):
        pygame.draw.rect(screen, (0, 0, 0, 160), rect, border_radius=10)
        pygame.draw.rect(screen, (255, 255, 255, 40), rect, width=1, border_radius=10)
        tag = "ON" if on else "OFF"
        c = (120, 220, 160) if on else (190, 190, 190)
        t = self._text(f"{label}: {tag}", c)
        screen.blit(t, (rect.x + 12, rect.y + 7))

    def _draw_icon_button(self, screen, rect, symbol):
        pygame.draw.rect(screen, (0, 0, 0, 160), rect, border_radius=9)
        pygame.draw.rect(screen, (255, 255, 255, 40), rect, width=1, border_radius=9)
        t = self._text(symbol, (230, 230, 230))
        screen.blit(t, (rect.centerx - t.get_width() // 2, rect.centery - t.get_height() // 2))

    def _draw_value_row(self, screen, y_local, label, value, minus_rect, plus_rect):
        x = self._rect.x + self.pad
        right_x = self._rect.x + self.panel_w - self.pad
        bw = 28

        t = self._text(label, (210, 210, 210))
        screen.blit(t, (x, self._rect.y + y_local + 7))

        v = self._text(f"{value:,.2f}".replace(",", " "), (230, 230, 230))
        screen.blit(v, (x + 140, self._rect.y + y_local + 7))

        minus_rect.update(right_x - (bw * 2 + 10), self._rect.y + y_local + 2, bw, self._row_h - 4)
        plus_rect.update(right_x - bw, self._rect.y + y_local + 2, bw, self._row_h - 4)

        self._draw_icon_button(screen, minus_rect, "–")
        self._draw_icon_button(screen, plus_rect, "+")

        return y_local + self._row_h

    def _find_primary_star(self, body):
        star = getattr(body, "parent_star", None)
        if star is not None:
            return star
        if not self._stars:
            return None

        best = None
        best_score = -1.0
        for s in self._stars:
            dx = s.pos.x - body.pos.x
            dy = s.pos.y - body.pos.y
            r2 = dx * dx + dy * dy
            if r2 <= 0:
                continue
            score = s.mass / r2
            if score > best_score:
                best_score = score
                best = s
        return best

    def _orbit_params_about_star(self, body, star):
       
        r = pygame.Vector2(body.pos) - pygame.Vector2(star.pos)
        v = pygame.Vector2(getattr(body, "vel", (0, 0))) - pygame.Vector2(getattr(star, "vel", (0, 0)))

        r_len = r.length()
        if r_len <= 1e-6:
            return None

        mu = G * float(getattr(star, "mass", 0.0))
        if mu <= 1e-9:
            return None

        soft_r = math.sqrt(r_len * r_len + SOFTENING)
        v2 = v.length_squared()

        
        eps = 0.5 * v2 - mu / soft_r

        
        h = r.x * v.y - r.y * v.x
        h2 = h * h

        
        e2 = 1.0 + (2.0 * eps * h2) / (mu * mu)
        if e2 < 0.0:
            
            e2 = 0.0
        e = math.sqrt(e2)

        
        denom = mu * (1.0 + e)
        rp = (h2 / denom) if denom > 1e-12 else None

        
        a = None
        ra = None
        if eps < 0.0:
            a = -mu / (2.0 * eps)
            
            ra = a * (1.0 + e)

        return {
            "eps": eps,
            "e": e,
            "a": a,
            "rp": rp,
            "ra": ra,
        }

    def draw(self, screen):
        if not self.enabled or self.selected is None:
            return

        b = self.selected
        name = b.name if b.name else "Body"

        vel = getattr(b, "vel", pygame.Vector2(0, 0))
        acc = getattr(b, "last_acc", pygame.Vector2(0, 0))
        user_acc = getattr(b, "user_acc", pygame.Vector2(0, 0))

        speed = vel.length()
        accel_mag = acc.length()

        heading = 0.0
        if speed > 1e-6:
            heading = (math.degrees(math.atan2(-vel.y, vel.x)) + 360.0) % 360.0

        star = self._find_primary_star(b)
        dist = (star.pos - b.pos).length() if star is not None else None
        star_name = getattr(star, "name", "Star") if star is not None else None

        
        has_energy = star is not None and getattr(b, "mass", 0) > 0 and dist is not None and dist > 0
        KE = PE = TE = None
        bound_tag = None

        if has_energy:
            m = float(b.mass)
            v2 = vel.length_squared()
            soft_r = math.sqrt(dist * dist + SOFTENING)

            KE = 0.5 * m * v2
            PE = -(G * m * float(star.mass)) / soft_r
            TE = KE + PE
            bound_tag = "BOUND" if TE < 0 else "UNBOUND"

        
        orbit = None
        if star is not None and not getattr(b, "is_star", False):
            orbit = self._orbit_params_about_star(b, star)

        has_tweaks = self.mode == "sandbox" and self._has_tweaks(b)

        
        base_text_lines = 2 + 1 + 5 + 1 + 3  
        if dist is not None:
            base_text_lines += 1
        if has_energy:
            base_text_lines += 1 + 4  
        if orbit is not None:
            base_text_lines += 1 + 4  

        base_h = self.pad * 2 + 26 + (base_text_lines * 20) + 10
        toggles_h = self._toggle_h * 2 + self._gap * 2

        tweaks_h = 0
        if has_tweaks:
            tweaks_h = 22 + (self._row_h * 4) + self._gap + self._toggle_h + 14

        self._rect.height = base_h + toggles_h + tweaks_h
        self._rect.x = self.w - self.panel_w - 14

        panel = pygame.Surface((self._rect.width, self._rect.height), pygame.SRCALPHA)
        self._panel_bg(panel)

        y = self.pad
        panel.blit(self._text("Selected", (255, 255, 255)), (self.pad, y))
        y += 22
        panel.blit(self._text(name, (230, 230, 230)), (self.pad, y))
        y += 28

        panel.blit(self._text("Motion", (255, 255, 255)), (self.pad, y))
        y += 22

        def line(txt, col=(210, 210, 210)):
            nonlocal y
            panel.blit(self._text(txt, col), (self.pad, y))
            y += 20

        line(f"Velocity X: {vel.x:,.2f}".replace(",", " "))
        line(f"Velocity Y: {vel.y:,.2f}".replace(",", " "))
        line(f"Speed:      {speed:,.2f}".replace(",", " "))
        line(f"Heading:    {heading:,.1f}°".replace(",", " "))
        if dist is not None:
            line(f"Distance to {star_name}: {dist:,.2f}".replace(",", " "))

        y += 6
        panel.blit(self._text("Acceleration", (255, 255, 255)), (self.pad, y))
        y += 22
        line(f"Accel X:    {acc.x:,.3f}".replace(",", " "))
        line(f"Accel Y:    {acc.y:,.3f}".replace(",", " "))
        line(f"Strength:   {accel_mag:,.3f}".replace(",", " "))

        if has_energy:
            y += 6
            panel.blit(self._text("Energy", (255, 255, 255)), (self.pad, y))
            y += 22
            line(f"Kinetic:    {KE:,.2f}".replace(",", " "))
            line(f"Potential:  {PE:,.2f}".replace(",", " "))
            line(f"Total:      {TE:,.2f}".replace(",", " "))

            tag_col = (120, 220, 160) if bound_tag == "BOUND" else (255, 130, 120)
            line(f"Status:     {bound_tag}", tag_col)

        if orbit is not None:
            y += 6
            panel.blit(self._text("Orbit", (255, 255, 255)), (self.pad, y))
            y += 22

            e = orbit["e"]
            a = orbit["a"]
            rp = orbit["rp"]
            ra = orbit["ra"]

            line(f"Eccentricity: {e:,.4f}".replace(",", " "))

            if a is None:
                line("Semi-major a:  N/A")
                line(f"Periapsis:     {rp:,.2f}".replace(",", " ") if rp is not None else "Periapsis:     N/A")
                line("Apoapsis:      N/A")
            else:
                line(f"Semi-major a:  {a:,.2f}".replace(",", " "))
                line(f"Periapsis:     {rp:,.2f}".replace(",", " ") if rp is not None else "Periapsis:     N/A")
                line(f"Apoapsis:      {ra:,.2f}".replace(",", " ") if ra is not None else "Apoapsis:      N/A")

        screen.blit(panel, self._rect.topleft)

        
        self._btn_close = pygame.Rect(self._rect.x + self.panel_w - 34, self._rect.y + 10, 24, 24)
        pygame.draw.circle(screen, (255, 255, 255), self._btn_close.center, 10, 1)
        x1, y1 = self._btn_close.centerx - 4, self._btn_close.centery - 4
        x2, y2 = self._btn_close.centerx + 4, self._btn_close.centery + 4
        pygame.draw.line(screen, (255, 255, 255), (x1, y1), (x2, y2), 1)
        pygame.draw.line(screen, (255, 255, 255), (x1, y2), (x2, y1), 1)

        
        y_screen = self._rect.y + y + 10
        self._btn_vel = pygame.Rect(self._rect.x + self.pad, y_screen, self.panel_w - self.pad * 2, self._toggle_h)
        self._btn_acc = pygame.Rect(
            self._rect.x + self.pad,
            y_screen + self._toggle_h + self._gap,
            self.panel_w - self.pad * 2,
            self._toggle_h,
        )
        self._draw_toggle(screen, self._btn_vel, "Velocity vector", self.show_velocity_vector)
        self._draw_toggle(screen, self._btn_acc, "Acceleration vector", self.show_acceleration_vector)

        y_screen = y_screen + (self._toggle_h * 2) + self._gap + 14

        
        if has_tweaks:
            screen.blit(self._text("Sandbox tweaks", (255, 255, 255)), (self._rect.x + self.pad, y_screen))
            y_local = (y_screen - self._rect.y) + 22

            y_local = self._draw_value_row(screen, y_local, "Velocity X", b.vel.x, self._vx_minus, self._vx_plus)
            y_local = self._draw_value_row(screen, y_local, "Velocity Y", b.vel.y, self._vy_minus, self._vy_plus)
            y_local = self._draw_value_row(screen, y_local, "Thruster X", user_acc.x, self._tx_minus, self._tx_plus)
            y_local = self._draw_value_row(screen, y_local, "Thruster Y", user_acc.y, self._ty_minus, self._ty_plus)

            reset_y = self._rect.y + y_local + self._gap
            self._reset_tweaks = pygame.Rect(self._rect.x + self.pad, reset_y, self.panel_w - self.pad * 2, self._toggle_h)

            pygame.draw.rect(screen, (0, 0, 0, 160), self._reset_tweaks, border_radius=10)
            pygame.draw.rect(screen, (255, 255, 255, 40), self._reset_tweaks, width=1, border_radius=10)
            rt = self._text("Reset thruster", (230, 230, 230))
            screen.blit(rt, (self._reset_tweaks.centerx - rt.get_width() // 2, self._reset_tweaks.centery - rt.get_height() // 2))
