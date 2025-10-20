import pygame
import asyncio

"""
Bevo vs. OU — Web/HTML5 Build (PyGBag ready)
=============================================
- Runs in desktop & mobile browsers (iPhone/iPad Safari supported).
- Responsive: renders to a virtual canvas (900x540) then scales to the window.
- On‑screen mobile controls (Left / Right / Jump) + keyboard support.
- Audio (grunt.wav) is initialized AFTER first tap (required by iOS Safari).

File layout for web build:
  main.py
  assets/
    bevo.png
    ou_defender.png
    football.png
    grunt.wav

Build for the web:
  pip install pygbag
  pygbag main.py
  # Deploy the generated ./build folder as a static site (e.g., Render Static Site)
"""

# ------------------------------
# Config
# ------------------------------
WORLD_WIDTH = 5000
VIRTUAL_W, VIRTUAL_H = 900, 540
FPS = 60
GRAVITY = 0.7
MOVE_SPEED = 4.2
JUMP_VEL = -15  # higher jump
MAX_FALL_SPEED = 18

# Colors
SKY = (138, 202, 240)
GROUND_BROWN = (155, 118, 83)
BLOCK = (200, 170, 120)
FLAG = (34, 139, 34)
WHITE = (255, 255, 255)
UI = (30, 30, 30)
BTN_BG = (0, 0, 0, 90)
BTN_BORDER = (255, 255, 255)

# Asset paths (PyGBag expects files in ./assets and referenced with 'assets/...')
AS_BEVO = "assets/bevo.png"
AS_ENEMY = "assets/ou_defender.png"
AS_FOOTBALL = "assets/football.png"
AS_GRUNT = "assets/grunt.wav"
AS_BG = "assets/stadium_background.png"  # <-- your stadium image
BG_IMG_SLOW = None
BG_IMG_FAST = None


pygame.init()

# Display surface is dynamic/responsive; we render to a fixed virtual surface
screen = pygame.display.set_mode((VIRTUAL_W, VIRTUAL_H), pygame.SCALED | pygame.RESIZABLE)
virtual = pygame.Surface((VIRTUAL_W, VIRTUAL_H)).convert_alpha()
clock = pygame.time.Clock()
font = pygame.font.SysFont("consolas", 20)

# ------------------------------
# Assets (loaded on start; grunt sound deferred until first tap)
# ------------------------------
PLAYER_HEIGHT = 72
ENEMY_HEIGHT = 64
FOOTBALL_HEIGHT = 24

BEVO_RIGHT = BEVO_LEFT = None
ENEMY_RIGHT = ENEMY_LEFT = None
FOOTBALL_IMG = None
GRUNT_SFX = None
mixer_ready = False  # set True after first tap


def load_images():
    global BEVO_RIGHT, BEVO_LEFT, ENEMY_RIGHT, ENEMY_LEFT, FOOTBALL_IMG
    try:
        bevo_raw = pygame.image.load(AS_BEVO).convert_alpha()
        s = PLAYER_HEIGHT / bevo_raw.get_height()
        w = max(16, int(bevo_raw.get_width() * s))
        BEVO_RIGHT = pygame.transform.smoothscale(bevo_raw, (w, PLAYER_HEIGHT))
        BEVO_LEFT = pygame.transform.flip(BEVO_RIGHT, True, False)
    except Exception:
        BEVO_RIGHT = BEVO_LEFT = None

    try:
        e_raw = pygame.image.load(AS_ENEMY).convert_alpha()
        s = ENEMY_HEIGHT / e_raw.get_height()
        w = max(16, int(e_raw.get_width() * s))
        ENEMY_RIGHT = pygame.transform.smoothscale(e_raw, (w, ENEMY_HEIGHT))
        ENEMY_LEFT = pygame.transform.flip(ENEMY_RIGHT, True, False)
    except Exception:
        ENEMY_RIGHT = ENEMY_LEFT = None

    try:
        fb_raw = pygame.image.load(AS_FOOTBALL).convert_alpha()
        s = FOOTBALL_HEIGHT / fb_raw.get_height()
        w = max(10, int(fb_raw.get_width() * s))
        FOOTBALL_IMG = pygame.transform.smoothscale(fb_raw, (w, FOOTBALL_HEIGHT))
    except Exception:
        FOOTBALL_IMG = None
    
    global BG_IMG_SLOW, BG_IMG_FAST
    try:
        bg_raw = pygame.image.load(AS_BG).convert()
        # Use WORLD_WIDTH if you added it; otherwise fall back to screen width
        bg_w = int(globals().get("WORLD_WIDTH", VIRTUAL_W))
        BG_IMG_SLOW = pygame.transform.scale(bg_raw, (bg_w, VIRTUAL_H))
        BG_IMG_FAST = pygame.transform.scale(bg_raw, (bg_w, VIRTUAL_H))
    except Exception:
        BG_IMG_SLOW = BG_IMG_FAST = None




load_images()

# ------------------------------
# Utility
# ------------------------------

def draw_text(surf, text, x, y, color=UI):
    surf.blit(font.render(text, True, color), (x, y))

# ------------------------------
# Level geometry
# ------------------------------
PLATFORMS = [
    pygame.Rect(0, VIRTUAL_H - 40, WORLD_WIDTH, 40),              # extend full ground length
    pygame.Rect(80, VIRTUAL_H - 120, 120, 20),
    pygame.Rect(260, VIRTUAL_H - 190, 120, 20),
    pygame.Rect(460, VIRTUAL_H - 150, 120, 20),
    pygame.Rect(640, VIRTUAL_H - 220, 140, 20),
    pygame.Rect(300, VIRTUAL_H - 320, 180, 20),
    pygame.Rect(700, VIRTUAL_H - 410, 180, 20),
    pygame.Rect(800, VIRTUAL_H - 300, 180, 20),
    pygame.Rect(900, VIRTUAL_H - 150, 180, 20),
    pygame.Rect(1000, VIRTUAL_H - 400, 180, 20),
    pygame.Rect(1200, VIRTUAL_H - 275, 180, 20),
    pygame.Rect(1400, VIRTUAL_H - 320, 180, 20),
    pygame.Rect(1650, VIRTUAL_H - 215, 180, 20),
    pygame.Rect(1800, VIRTUAL_H - 100, 180, 20),
    pygame.Rect(2050, VIRTUAL_H - 420, 180, 20),
    pygame.Rect(2300, VIRTUAL_H - 293, 180, 20),
    pygame.Rect(2450, VIRTUAL_H - 360, 180, 20),
]

#FLAG_RECT = pygame.Rect(VIRTUAL_W - 70, VIRTUAL_H - 160, 20, 120)
FLAG_RECT = pygame.Rect(WORLD_WIDTH - 70, VIRTUAL_H - 160, 20, 120)


FOOTBALLS = []


def place_footballs():
    global FOOTBALLS
    FOOTBALLS = [
        pygame.Rect(120, VIRTUAL_H - 155, 18, 12),  # near first platform
        pygame.Rect(300, VIRTUAL_H - 225, 18, 12),
        pygame.Rect(520, VIRTUAL_H - 185, 18, 12),
        pygame.Rect(700, VIRTUAL_H - 255, 18, 12),
        pygame.Rect(380, VIRTUAL_H - 355, 18, 12),
        pygame.Rect(60, VIRTUAL_H - 80, 18, 12),
        pygame.Rect(460, VIRTUAL_H - 80, 18, 12),
        pygame.Rect(820, VIRTUAL_H - 80, 18, 12),
    ]


place_footballs()

# ------------------------------
# Enemy with advanced patrol + flex/grunt
# ------------------------------
try:
    pygame.mixer.pre_init(44100, -16, 2, 512)
except Exception:
    pass


class Enemy:
    def __init__(self, start_x, y, speed=1.4):
        # Find platform (match y to platform top)
        self.platform = None
        for p in PLATFORMS:
            if abs(y - p.top) <= 1:
                self.platform = p
                break
        if self.platform is None:
            self.platform = PLATFORMS[0]
            y = self.platform.top

        # Sprite / rect
        if ENEMY_RIGHT is not None:
            self.img_r = ENEMY_RIGHT
            self.img_l = ENEMY_LEFT
            self.rect = self.img_r.get_rect()
        else:
            self.img_r = self.img_l = None
            self.rect = pygame.Rect(0, 0, 28, 24)

        # Edge‑to‑edge bounds with no overhang
        self.left_bound = self.platform.left
        self.right_bound = self.platform.right - self.rect.width

        self.rect.left = max(self.left_bound, min(start_x, self.right_bound))
        self.rect.bottom = y

        self.vx = speed
        self.facing_right = True

        # Pause / flex state
        self.state = "move"          # or "pause"
        self.pause_timer = 0.0       # seconds
        self.flex_this_pause = False
        self.next_flex_toggle = True  # every other turn

    def _start_pause(self):
        self.state = "pause"
        self.pause_timer = 1.0  # seconds
        self.flex_this_pause = self.next_flex_toggle
        self.next_flex_toggle = not self.next_flex_toggle
        # Play grunt if allowed and available
        if self.flex_this_pause and mixer_ready and (GRUNT_SFX is not None):
            try:
                GRUNT_SFX.play()
            except Exception:
                pass

    def _end_pause_and_turn(self):
        self.vx = -self.vx
        self.facing_right = self.vx > 0
        self.state = "move"
        self.pause_timer = 0.0
        self.flex_this_pause = False

    def update(self, dt):
        if self.state == "pause":
            self.pause_timer -= dt
            if self.pause_timer <= 0:
                self._end_pause_and_turn()
            return

        next_left = self.rect.left + self.vx
        if self.vx > 0:
            if next_left >= self.right_bound:
                self.rect.left = self.right_bound
                self._start_pause()
            else:
                self.rect.left = next_left
        else:
            if next_left <= self.left_bound:
                self.rect.left = self.left_bound
                self._start_pause()
            else:
                self.rect.left = next_left

    def draw(self, surf):
        if self.img_r is not None:
            img = self.img_r if self.facing_right else self.img_l
            if self.state == "pause" and self.flex_this_pause:
                scale = 1.12
                w = int(img.get_width() * scale)
                h = int(img.get_height() * scale)
                flex_img = pygame.transform.smoothscale(img, (w, h))
                draw_x = self.rect.centerx - flex_img.get_width() // 2
                draw_y = self.rect.bottom - flex_img.get_height()
                surf.blit(flex_img, (draw_x, draw_y))
            else:
                surf.blit(img, self.rect.topleft)
        else:
            pygame.draw.rect(surf, (50, 50, 50), self.rect)

    def draw_offset(self, surf, camera_x):
        if self.img_r is not None:
            img = self.img_r if self.facing_right else self.img_l
            if self.state == "pause" and self.flex_this_pause:
                scale = 1.12
                w = int(img.get_width() * scale)
                h = int(img.get_height() * scale)
                flex_img = pygame.transform.smoothscale(img, (w, h))
                draw_x = self.rect.centerx - flex_img.get_width() // 2 - camera_x
                draw_y = self.rect.bottom - flex_img.get_height()
                surf.blit(flex_img, (draw_x, draw_y))
            else:
                surf.blit(img, (self.rect.x - camera_x, self.rect.y))
        else:
            pygame.draw.rect(surf, (50, 50, 50), pygame.Rect(self.rect.x - camera_x, self.rect.y, self.rect.w, self.rect.h))


ENEMIES = [
    Enemy(100, PLATFORMS[0].top, speed=1.4),
    Enemy(PLATFORMS[1].left + 10, PLATFORMS[1].top, speed=1.4),
    Enemy(PLATFORMS[2].left + 10, PLATFORMS[2].top, speed=1.4),
]

# ------------------------------
# Player
# ------------------------------
class Player:
    def __init__(self):
        self.lives = 3
        self.score = 0
        self.facing_right = True
        self.invuln_timer = 0
        self.coins_total = len(FOOTBALLS)
        self.spawn()

    def spawn(self):
        if BEVO_RIGHT is not None:
            self.img_r = BEVO_RIGHT
            self.img_l = BEVO_LEFT
            self.rect = self.img_r.get_rect()
        else:
            self.img_r = self.img_l = None
            self.rect = pygame.Rect(30, VIRTUAL_H - 100, 28, 36)
        self.vx = 0
        self.vy = 0
        self.on_ground = False
        self.rect.topleft = (30, VIRTUAL_H - 180)
        self.rect.bottom = PLATFORMS[0].top

    def handle_input(self, left, right, jump):
        self.vx = 0
        if left:
            self.vx -= MOVE_SPEED
            self.facing_right = False
        if right:
            self.vx += MOVE_SPEED
            self.facing_right = True
        if jump and self.on_ground:
            self.vy = JUMP_VEL
            self.on_ground = False

    def apply_gravity(self):
        self.vy = min(self.vy + GRAVITY, MAX_FALL_SPEED)

    def collide_axis(self, rects, axis):
        for r in rects:
            if self.rect.colliderect(r):
                if axis == 'x':
                    if self.vx > 0:
                        self.rect.right = r.left
                    elif self.vx < 0:
                        self.rect.left = r.right
                    self.vx = 0
                else:
                    if self.vy > 0:
                        self.rect.bottom = r.top
                        self.on_ground = True
                    elif self.vy < 0:
                        self.rect.top = r.bottom
                    self.vy = 0

    def update(self, dt, left, right, jump):
        self.handle_input(left, right, jump)
        self.apply_gravity()
        self.rect.x += int(self.vx)
        self.collide_axis(PLATFORMS, 'x')
        self.rect.y += int(self.vy)
        self.on_ground = False
        self.collide_axis(PLATFORMS, 'y')

        global FOOTBALLS
        for fb in FOOTBALLS[:]:
            if self.rect.colliderect(fb):
                FOOTBALLS.remove(fb)
                self.score += 100

        if self.invuln_timer > 0:
            self.invuln_timer -= 1

    def draw(self, surf):
        if self.invuln_timer > 0 and (self.invuln_timer // 4) % 2 == 0:
            return
        if BEVO_RIGHT is not None:
            img = self.img_r if self.facing_right else self.img_l
            surf.blit(img, self.rect.topleft)
        else:
            pygame.draw.rect(surf, (220, 20, 60), self.rect)

    def hurt(self):
        if self.invuln_timer > 0:
            return
        self.lives -= 1
        self.invuln_timer = FPS
        self.rect.y -= 10
        if self.lives < 0:
            self.lives = 0

    def draw_offset(self, surf, camera_x):
        if self.invuln_timer > 0 and (self.invuln_timer // 4) % 2 == 0:
            return
        if BEVO_RIGHT is not None:
            img = self.img_r if self.facing_right else self.img_l
            surf.blit(img, (self.rect.x - camera_x, self.rect.y))
        else:
            pygame.draw.rect(surf, (220, 20, 60), pygame.Rect(self.rect.x - camera_x, self.rect.y, self.rect.w, self.rect.h))

# ------------------------------
# Game helpers
# ------------------------------

def reset_game(player):
    """Fully reset the game state: lives, score, enemies, footballs, etc."""
    player.lives = 3
    player.score = 0
    player.invuln_timer = 0
    place_footballs()
    player.coins_total = len(FOOTBALLS)
    player.spawn()

    ENEMIES[:] = [
        Enemy(100, PLATFORMS[0].top, speed=1.4),
        Enemy(PLATFORMS[1].left + 10, PLATFORMS[1].top, speed=1.4),
        Enemy(PLATFORMS[2].left + 10, PLATFORMS[2].top, speed=1.4),
    ]
    place_footballs()

def reset_level(player):
    player.spawn()
    ENEMIES[:] = [
        Enemy(100, PLATFORMS[0].top, speed=1.4),
        Enemy(PLATFORMS[1].left + 10, PLATFORMS[1].top, speed=1.4),
        Enemy(PLATFORMS[2].left + 10, PLATFORMS[2].top, speed=1.4),
    ]
    place_footballs()


def draw_world(surf, camera_x):
    # Parallax background (two layers at different speeds)
    if BG_IMG_SLOW:
        # Slow layer (far background, e.g. distant stadium/sky)
        offset_slow = int(camera_x * 0.3)
        surf.blit(BG_IMG_SLOW, (-offset_slow, 0))

    if BG_IMG_FAST:
        # Faster layer (closer background, e.g. crowd/walls)
        offset_fast = int(camera_x * 0.6)
        surf.blit(BG_IMG_FAST, (-offset_fast, 0))

    # Platforms
    for p in PLATFORMS:
        pygame.draw.rect(surf, BLOCK, (p.x - camera_x, p.y, p.w, p.h))
        top = pygame.Rect(p.x - camera_x, p.y, p.w, 4)
        pygame.draw.rect(surf, (170, 140, 100), top)

    # Ground
    pygame.draw.rect(surf, GROUND_BROWN, (PLATFORMS[0].x - camera_x, PLATFORMS[0].y, PLATFORMS[0].w, PLATFORMS[0].h))

    # Footballs
    for r in FOOTBALLS:
        if FOOTBALL_IMG is not None:
            pos = (r.centerx - FOOTBALL_IMG.get_width() // 2 - camera_x, r.centery - FOOTBALL_IMG.get_height() // 2)
            surf.blit(FOOTBALL_IMG, pos)
        else:
            pygame.draw.ellipse(surf, (200, 120, 40), pygame.Rect(r.x - camera_x, r.y, r.w, r.h))

    # Flag
    pygame.draw.rect(surf, FLAG, (FLAG_RECT.x - camera_x, FLAG_RECT.y, FLAG_RECT.w, FLAG_RECT.h))
    pole = pygame.Rect(FLAG_RECT.centerx - 2 - camera_x, FLAG_RECT.top - 100, 4, 100)
    pygame.draw.rect(surf, (200, 255, 200), pole)




def draw_hud(surf, player, msg=None):
    draw_text(surf, f"Score: {player.score}", 12, 10)
    draw_text(surf, f"Footballs: {player.coins_total - len(FOOTBALLS)}/{player.coins_total}", 12, 34)
    draw_text(surf, f"Lives: {player.lives}", 12, 58)
    if msg:
        draw_text(surf, msg, VIRTUAL_W//2 - 200, 10, color=WHITE)


def check_fail(player):
    if player.rect.top > VIRTUAL_H + 80:
        player.hurt()
        player.spawn()


def check_enemy_collisions(player):
    for e in ENEMIES:
        if player.rect.colliderect(e.rect):
            if player.vy > 0 and player.rect.bottom - e.rect.top < 16:
                player.vy = int(JUMP_VEL * 0.7)
                ENEMIES.remove(e)
                return "Stomped a Sooner! +200", 200
            else:
                player.hurt()
                return "Hit by OU Defender! -1 life", 0
    return None, 0


def check_win(player):
    return player.rect.colliderect(FLAG_RECT) and len(FOOTBALLS) == 0


# ------------------------------
# Mobile controls (screen-space)
# ------------------------------
# We render buttons on the *final* scaled screen, but handle input via flags.
move_left = False
move_right = False
jump_pressed = False

# Tap-to-start gating for audio on iOS
started = False


def screen_buttons(rect):
    """Return (left_rect, right_rect, jump_rect) in screen coords based on current size."""
    sw, sh = rect.size
    pad = int(0.02 * sw)
    btn_w = int(0.2 * sw)
    btn_h = int(0.18 * sh)
    y = sh - btn_h - pad
    left_rect = pygame.Rect(pad, y, btn_w, btn_h)
    right_rect = pygame.Rect(pad + btn_w + pad, y, btn_w, btn_h)
    jump_size = int(0.16 * sh)
    jr = pygame.Rect(int(sw - jump_size - pad), int(sh - jump_size - pad), jump_size, jump_size)
    return left_rect, right_rect, jr


def draw_buttons(surf):
    sw, sh = surf.get_size()
    left_r, right_r, jump_r = screen_buttons(surf.get_rect())
    # Draw semi-transparent rects
    overlay = pygame.Surface((left_r.w, left_r.h), pygame.SRCALPHA)
    overlay.fill(BTN_BG)
    surf.blit(overlay, left_r.topleft)
    surf.blit(overlay, right_r.topleft)
    # Jump circle
    circ = pygame.Surface((jump_r.w, jump_r.h), pygame.SRCALPHA)
    pygame.draw.ellipse(circ, BTN_BG, circ.get_rect())
    surf.blit(circ, jump_r.topleft)
    # Labels
    lbl = pygame.font.SysFont("consolas", max(14, int(0.04 * sh)))
    surf.blit(lbl.render("LEFT", True, BTN_BORDER), (left_r.x + 10, left_r.y + left_r.h//2 - 10))
    surf.blit(lbl.render("RIGHT", True, BTN_BORDER), (right_r.x + 10, right_r.y + right_r.h//2 - 10))
    surf.blit(lbl.render("JUMP", True, BTN_BORDER), (jump_r.x + 8, jump_r.y + jump_r.h//2 - 12))


# ------------------------------
# Async main loop (PyGBag friendly)
# ------------------------------
async def main():
    global move_left, move_right, jump_pressed, started, mixer_ready, GRUNT_SFX

    player = Player()
    message = None
    message_timer = 0

    running = True
    while running:
        dt_ms = clock.tick(FPS)
        dt = dt_ms / 1000.0

        # --- Events ---
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                if event.key == pygame.K_r:
                    reset_game(player)
                    message = "Game reset - good luck, Bevo!"
                    message_timer = FPS
                if event.key in (pygame.K_LEFT, pygame.K_a):
                    move_left = True
                if event.key in (pygame.K_RIGHT, pygame.K_d):
                    move_right = True
                if event.key in (pygame.K_UP, pygame.K_w, pygame.K_SPACE):
                    jump_pressed = True
                # First key press also starts audio on mobile
                if not started:
                    started = True
                    # Lazy mixer init for iOS
                    try:
                        pygame.mixer.init()
                        GRUNT_SFX = pygame.mixer.Sound(AS_GRUNT)
                        GRUNT_SFX.set_volume(1.0)
                        mixer_ready = True
                    except Exception:
                        mixer_ready = False

            elif event.type == pygame.KEYUP:
                if event.key in (pygame.K_LEFT, pygame.K_a):
                    move_left = False
                if event.key in (pygame.K_RIGHT, pygame.K_d):
                    move_right = False
                if event.key in (pygame.K_UP, pygame.K_w, pygame.K_SPACE):
                    jump_pressed = False

            elif event.type == pygame.MOUSEBUTTONDOWN:
                # First interaction => enable audio
                if not started:
                    started = True
                    try:
                        pygame.mixer.init()
                        GRUNT_SFX = pygame.mixer.Sound(AS_GRUNT)
                        GRUNT_SFX.set_volume(1.0)
                        mixer_ready = True
                    except Exception:
                        mixer_ready = False

                sw, sh = screen.get_size()
                left_r, right_r, jump_r = screen_buttons(screen.get_rect())
                mx, my = event.pos
                if left_r.collidepoint(mx, my):
                    move_left = True
                elif right_r.collidepoint(mx, my):
                    move_right = True
                elif jump_r.collidepoint(mx, my):
                    jump_pressed = True

            elif event.type == pygame.MOUSEBUTTONUP:
                sw, sh = screen.get_size()
                left_r, right_r, jump_r = screen_buttons(screen.get_rect())
                mx, my = event.pos
                if left_r.collidepoint(mx, my):
                    move_left = False
                if right_r.collidepoint(mx, my):
                    move_right = False
                if jump_r.collidepoint(mx, my):
                    jump_pressed = False

        # --- Update ---
        player.update(dt, move_left, move_right, jump_pressed)
        for e in ENEMIES:
            e.update(dt)

        check_fail(player)
        m, delta = check_enemy_collisions(player)
        if m:
            message = m
            message_timer = int(FPS * 1.2)
            player.score += delta

        won = check_win(player)

        # --- Draw to virtual surface ---
        # --- Camera logic ---
        camera_x = player.rect.centerx - VIRTUAL_W // 2
        camera_x = max(0, min(camera_x, WORLD_WIDTH - VIRTUAL_W))  # clamp camera

        # --- Draw to virtual surface ---
        draw_world(virtual, camera_x)

        # Draw enemies with offset
        for e in ENEMIES:
            e.draw_offset(virtual, camera_x)

        # Draw player with offset
        player.draw_offset(virtual, camera_x)


        state_msg = None
        if message_timer > 0:
            state_msg = message
            message_timer -= 1
        if player.lives == 0:
            state_msg = "Game Over! Press R to retry"
        elif won:
            state_msg = "🏆 Bevo Wins the Red River Showdown! Tap R to replay"

        draw_hud(virtual, player, state_msg)

        # If not started (mobile), show tap overlay
        if not started:
            overlay = pygame.Surface((VIRTUAL_W, VIRTUAL_H), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 120))
            virtual.blit(overlay, (0, 0))
            draw_text(virtual, "Tap to Start (enables sound)", VIRTUAL_W//2 - 170, VIRTUAL_H//2 - 10, WHITE)

        # --- Scale to screen & draw buttons ---
        sw, sh = screen.get_size()
        scaled = pygame.transform.smoothscale(virtual, (sw, sh))
        screen.blit(scaled, (0, 0))
        draw_buttons(screen)
        pygame.display.flip()

        # Clear virtual surface for next frame
        virtual.fill((0, 0, 0, 0))

        await asyncio.sleep(0)  # yield to browser

    # Don’t call pygame.quit() or sys.exit() in web build
    return


if __name__ == "__main__":
    # In desktop Python, run asyncio loop; in PyGBag, this is handled by runtime.
    try:
        asyncio.run(main())
    except RuntimeError:
        # If already in a running loop (pygbag sometimes), just call directly
        import sys
        if sys.platform.startswith("emscripten"):
            import asyncio as _a
            _a.get_event_loop().create_task(main())
        else:
            raise
