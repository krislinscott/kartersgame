import pygame
import asyncio
import random

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
WORLD_WIDTH = 12000  # Epic extended level - reach the end of the image!
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
    pygame.Rect(0, VIRTUAL_H - 40, 7000, 40),  # full ground floor extended to 7000px

    # === ZONE 1 (0-1000): Tutorial & Path Selection ===
    # Lower path (easy route)
    pygame.Rect(100,  VIRTUAL_H - 100, 200, 20),   # first step up
    pygame.Rect(400,  VIRTUAL_H - 120, 180, 20),   # gentle rise
    pygame.Rect(650,  VIRTUAL_H - 160, 200, 20),   # continue up
    pygame.Rect(900,  VIRTUAL_H - 140, 160, 20),   # slight drop
    
    # Upper path (challenge route)
    pygame.Rect(200,  VIRTUAL_H - 280, 140, 20),   # high jump start
    pygame.Rect(480,  VIRTUAL_H - 360, 160, 20),   # very high platform
    pygame.Rect(720,  VIRTUAL_H - 320, 180, 20),   # stay high
    pygame.Rect(980,  VIRTUAL_H - 400, 140, 20),   # sky platform

    # === ZONE 2 (1000-2000): Multi-Path Divergence ===
    # Lower-middle path
    pygame.Rect(1100, VIRTUAL_H - 180, 180, 20),
    pygame.Rect(1350, VIRTUAL_H - 200, 160, 20),
    pygame.Rect(1600, VIRTUAL_H - 160, 200, 20),
    pygame.Rect(1850, VIRTUAL_H - 220, 180, 20),
    
    # Middle path (main route)
    pygame.Rect(1200, VIRTUAL_H - 280, 160, 20),
    pygame.Rect(1450, VIRTUAL_H - 320, 180, 20),
    pygame.Rect(1700, VIRTUAL_H - 300, 160, 20),
    pygame.Rect(1900, VIRTUAL_H - 340, 180, 20),
    
    # Upper path (continues high)
    pygame.Rect(1150, VIRTUAL_H - 420, 140, 20),
    pygame.Rect(1400, VIRTUAL_H - 460, 160, 20),
    pygame.Rect(1650, VIRTUAL_H - 440, 180, 20),
    pygame.Rect(1950, VIRTUAL_H - 480, 140, 20),   # near ceiling

    # === ZONE 3 (2000-3000): Interconnected Maze ===
    # Connecting platforms (path switching opportunities)
    pygame.Rect(2100, VIRTUAL_H - 160, 120, 20),   # low connector
    pygame.Rect(2100, VIRTUAL_H - 260, 120, 20),   # mid connector  
    pygame.Rect(2100, VIRTUAL_H - 380, 120, 20),   # high connector
    
    # Lower maze section
    pygame.Rect(2300, VIRTUAL_H - 140, 180, 20),
    pygame.Rect(2550, VIRTUAL_H - 180, 160, 20),
    pygame.Rect(2800, VIRTUAL_H - 120, 200, 20),
    
    # Middle maze section
    pygame.Rect(2350, VIRTUAL_H - 280, 160, 20),
    pygame.Rect(2580, VIRTUAL_H - 320, 180, 20),
    pygame.Rect(2850, VIRTUAL_H - 260, 180, 20),
    
    # Upper maze section
    pygame.Rect(2280, VIRTUAL_H - 420, 140, 20),
    pygame.Rect(2500, VIRTUAL_H - 460, 160, 20),
    pygame.Rect(2750, VIRTUAL_H - 400, 180, 20),

    # === ZONE 4 (3000-4000): Vertical Challenge Tower ===
    # Multi-tier climbing section
    pygame.Rect(3100, VIRTUAL_H - 140, 160, 20),   # base level
    pygame.Rect(3350, VIRTUAL_H - 200, 140, 20),   # step up
    pygame.Rect(3200, VIRTUAL_H - 280, 160, 20),   # zigzag back
    pygame.Rect(3450, VIRTUAL_H - 340, 140, 20),   # continue up
    pygame.Rect(3300, VIRTUAL_H - 420, 160, 20),   # near top
    pygame.Rect(3550, VIRTUAL_H - 460, 140, 20),   # peak platform
    
    # Alternative lower route through zone 4
    pygame.Rect(3650, VIRTUAL_H - 160, 200, 20),   # bypass low
    pygame.Rect(3900, VIRTUAL_H - 200, 180, 20),   # gentle climb  # top “sky box”

    # === ZONE 5 (4000-5000): Final Approaches ===
    # Multiple final paths to flag
    
    # High dramatic approach
    pygame.Rect(4100, VIRTUAL_H - 400, 160, 20),   # high start
    pygame.Rect(4350, VIRTUAL_H - 360, 180, 20),   # descent begins
    pygame.Rect(4600, VIRTUAL_H - 280, 160, 20),   # coming down
    pygame.Rect(4820, VIRTUAL_H - 200, 180, 20),   # final high platform
    
    # Middle steady approach  
    pygame.Rect(4150, VIRTUAL_H - 260, 180, 20),   # mid-level start
    pygame.Rect(4400, VIRTUAL_H - 240, 160, 20),   # steady progress
    pygame.Rect(4650, VIRTUAL_H - 220, 180, 20),   # approach flag level
    
    # Lower safe approach
    pygame.Rect(4200, VIRTUAL_H - 160, 200, 20),   # low but safe
    pygame.Rect(4500, VIRTUAL_H - 140, 160, 20),   # easy progression
    pygame.Rect(4750, VIRTUAL_H - 120, 180, 20),   # safe final jump
    
    # Victory platform (where flag sits)
    pygame.Rect(4950, VIRTUAL_H - 200, 100, 20),   # flag platform

    # === ZONE 6 (5000-6000): Extended Challenge Gauntlet ===
    # Lower tier platforms
    pygame.Rect(5100, VIRTUAL_H - 120, 180, 20),   # continuation from zone 5
    pygame.Rect(5350, VIRTUAL_H - 140, 160, 20),   # gentle rise
    pygame.Rect(5600, VIRTUAL_H - 180, 200, 20),   # step up
    pygame.Rect(5850, VIRTUAL_H - 160, 180, 20),   # slight drop
    
    # Middle tier platforms
    pygame.Rect(5150, VIRTUAL_H - 240, 160, 20),   # mid-level progression
    pygame.Rect(5400, VIRTUAL_H - 280, 180, 20),   # climb higher
    pygame.Rect(5650, VIRTUAL_H - 320, 160, 20),   # peak middle
    pygame.Rect(5900, VIRTUAL_H - 260, 200, 20),   # descent back
    
    # Upper tier platforms (high skill)
    pygame.Rect(5200, VIRTUAL_H - 380, 140, 20),   # high start
    pygame.Rect(5450, VIRTUAL_H - 420, 160, 20),   # very high
    pygame.Rect(5700, VIRTUAL_H - 460, 140, 20),   # near ceiling
    pygame.Rect(5950, VIRTUAL_H - 400, 180, 20),   # high descent
    
    # Connector platforms for path switching
    pygame.Rect(5300, VIRTUAL_H - 200, 120, 20),   # low-mid connector
    pygame.Rect(5550, VIRTUAL_H - 340, 120, 20),   # mid-high connector
    pygame.Rect(5800, VIRTUAL_H - 220, 120, 20),   # another low-mid connector

    # === ZONE 7 (6000-7000): Final Epic Challenge ===
    # Epic staircase section (multiple routes to grand finale)
    
    # Lower epic route
    pygame.Rect(6100, VIRTUAL_H - 140, 160, 20),   # epic start low
    pygame.Rect(6350, VIRTUAL_H - 120, 180, 20),   # steady low
    pygame.Rect(6600, VIRTUAL_H - 160, 160, 20),   # rise slightly
    pygame.Rect(6850, VIRTUAL_H - 180, 200, 20),   # final low approach
    
    # Middle epic route
    pygame.Rect(6150, VIRTUAL_H - 260, 180, 20),   # epic start mid
    pygame.Rect(6400, VIRTUAL_H - 300, 160, 20),   # climb up
    pygame.Rect(6650, VIRTUAL_H - 280, 180, 20),   # plateau
    pygame.Rect(6900, VIRTUAL_H - 240, 160, 20),   # final mid approach
    
    # Upper epic route (extreme challenge)
    pygame.Rect(6120, VIRTUAL_H - 420, 140, 20),   # epic start high
    pygame.Rect(6380, VIRTUAL_H - 460, 160, 20),   # maximum height
    pygame.Rect(6620, VIRTUAL_H - 480, 140, 20),   # ceiling platform
    pygame.Rect(6870, VIRTUAL_H - 440, 180, 20),   # epic descent
    
    # Grand finale connecting platforms
    pygame.Rect(6050, VIRTUAL_H - 180, 120, 20),   # zone 6-7 connector low
    pygame.Rect(6050, VIRTUAL_H - 320, 120, 20),   # zone 6-7 connector mid
    pygame.Rect(6050, VIRTUAL_H - 380, 120, 20),   # zone 6-7 connector high
    
    # Final challenge zigzag
    pygame.Rect(6200, VIRTUAL_H - 340, 140, 20),   # zigzag start
    pygame.Rect(6450, VIRTUAL_H - 380, 120, 20),   # zigzag up
    pygame.Rect(6700, VIRTUAL_H - 360, 140, 20),   # zigzag middle
    pygame.Rect(6950, VIRTUAL_H - 320, 120, 20),   # zigzag final
    
    # Ultimate victory platforms leading to new flag position
    pygame.Rect(6980, VIRTUAL_H - 200, 100, 20),   # penultimate platform
    pygame.Rect(7050, VIRTUAL_H - 160, 100, 20),   # final victory platform

]




#FLAG_RECT = pygame.Rect(VIRTUAL_W - 70, VIRTUAL_H - 160, 20, 120)
FLAG_RECT = pygame.Rect(WORLD_WIDTH - 70, VIRTUAL_H - 160, 20, 120)


FOOTBALLS = []

# Game state variables
flag_reached = False
win_animation_time = 0.0
confetti_particles = []

# Death animation variables
death_animation_active = False
death_animation_time = 0.0
death_launch_velocity = -18  # Initial upward velocity for death launch

class ConfettiParticle:
    def __init__(self, x, y, img=None):
        self.x = x
        self.y = y
        self.vx = random.uniform(-2, 2)  # Horizontal drift
        self.vy = random.uniform(1, 4)   # Falling speed
        self.rotation = random.uniform(0, 360)  # Initial rotation
        self.rotation_speed = random.uniform(-5, 5)  # Rotation speed
        self.life_time = random.uniform(8, 12)  # How long it stays on screen
        self.age = 0
        
        # Make confetti smaller
        self.size_scale = random.uniform(0.3, 0.6)  # 30-60% of original size
        
        if img is not None:
            # Scale down the confetti image
            orig_w, orig_h = img.get_size()
            new_w = max(5, int(orig_w * self.size_scale))
            new_h = max(5, int(orig_h * self.size_scale))
            self.img = pygame.transform.smoothscale(img, (new_w, new_h))
        else:
            # Fallback rectangle size
            self.img = None
            self.size = random.randint(3, 8)  # Small rectangles
            self.color = random.choice([
                (255, 165, 0),   # Orange
                (255, 140, 0),   # Dark orange
                (255, 215, 0),   # Gold
                (255, 69, 0),    # Red-orange
                (255, 99, 71)    # Tomato
            ])
    
    def update(self, dt):
        # Update position
        self.x += self.vx * dt * 60  # Scale by fps for consistent movement
        self.y += self.vy * dt * 60
        
        # Update rotation
        self.rotation += self.rotation_speed * dt * 60
        
        # Add some air resistance and gravity variation
        self.vy += random.uniform(-0.1, 0.2) * dt * 60
        
        # Age the particle
        self.age += dt
        
        # Return True if particle should be removed
        return self.age >= self.life_time
    
    def draw(self, surf):
        if self.img is not None:
            # Rotate the image
            rotated_img = pygame.transform.rotate(self.img, self.rotation)
            # Calculate position to center the rotated image
            rect = rotated_img.get_rect(center=(int(self.x), int(self.y)))
            surf.blit(rotated_img, rect.topleft)
        else:
            # Draw simple rotating rectangle
            # Create a small surface for the rectangle
            rect_surf = pygame.Surface((self.size, self.size), pygame.SRCALPHA)
            pygame.draw.rect(rect_surf, self.color, (0, 0, self.size, self.size))
            # Rotate and blit
            rotated_rect = pygame.transform.rotate(rect_surf, self.rotation)
            rect_pos = rotated_rect.get_rect(center=(int(self.x), int(self.y)))
            surf.blit(rotated_rect, rect_pos.topleft)


def place_footballs():
    global FOOTBALLS
    FOOTBALLS = []
    
    # Place footballs on platforms throughout the extended 7000px level
    # Distribute evenly across all elevated platforms (skip ground floor platform[0])
    selected_platforms = [
        # Zone 1 platforms
        1, 2, 3, 4, 5, 6, 7, 8,
        # Zone 2 platforms  
        9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20,
        # Zone 3 platforms
        21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32,
        # Zone 4 platforms
        33, 34, 35, 36, 37, 38, 39, 40,
        # Zone 5 platforms  
        41, 42, 43, 44, 45, 46, 47, 48, 49, 50, 51,
        # Zone 6 platforms (NEW)
        52, 53, 54, 55, 56, 57, 58, 59, 60, 61, 62, 63, 64,
        # Zone 7 platforms (NEW)
        65, 66, 67, 68, 69, 70, 71, 72, 73, 74, 75, 76, 77, 78, 79, 80, 81
    ]
    
    # Select every 3rd platform to get good distribution (about 25-27 footballs total)
    football_platforms = selected_platforms[::3]  # Every 3rd platform
    
    for platform_idx in football_platforms:
        if platform_idx < len(PLATFORMS):
            platform = PLATFORMS[platform_idx]
            # Place football in center of platform, slightly above it
            football_x = platform.centerx - 9  # center the 18px wide football
            football_y = platform.top - 15     # place above platform
            FOOTBALLS.append(pygame.Rect(football_x, football_y, 18, 12))





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
    # Zone 1 - placed on lower path platforms for easier introduction
    Enemy(500,  PLATFORMS[2].top,  speed=1.1),   # on gentle rise platform (x=400)
    Enemy(750,  PLATFORMS[4].top,  speed=1.1),   # on slight drop platform (x=900)

    # Zone 2 - spread across different height paths  
    Enemy(1200, PLATFORMS[9].top,  speed=1.2),   # lower-middle path (x=1100)
    Enemy(1500, PLATFORMS[13].top, speed=1.3),   # middle path (x=1200)
    Enemy(1750, PLATFORMS[16].top, speed=1.2),   # middle path (x=1900)

    # Zone 3 - maze section enemies on connectors and main paths
    Enemy(2120, PLATFORMS[21].top, speed=1.3),   # low connector platform (x=2100)
    Enemy(2400, PLATFORMS[24].top, speed=1.3),   # lower maze section (x=2300)
    Enemy(2600, PLATFORMS[27].top, speed=1.4),   # middle maze section (x=2350)
    Enemy(2350, PLATFORMS[30].top, speed=1.3),   # upper maze section (x=2280)

    # Zone 4 - tower climbing challenges
    Enemy(3200, PLATFORMS[33].top, speed=1.4),   # base level (x=3100)
    Enemy(3400, PLATFORMS[34].top, speed=1.4),   # step up (x=3350)
    Enemy(3500, PLATFORMS[36].top, speed=1.4),   # continue up (x=3450)
    Enemy(3750, PLATFORMS[39].top, speed=1.3),   # bypass low (x=3650)

    # Zone 5 - final approach guards
    Enemy(4200, PLATFORMS[45].top, speed=1.4),   # middle steady approach (x=4150)
    Enemy(4550, PLATFORMS[49].top, speed=1.5),   # lower safe approach (x=4500)
    
    # Zone 6 - extended challenge gauntlet
    Enemy(5200, PLATFORMS[53].top, speed=1.3),   # lower tier (x=5100)
    Enemy(5450, PLATFORMS[55].top, speed=1.4),   # middle tier (x=5400)
    Enemy(5750, PLATFORMS[58].top, speed=1.5),   # upper tier (x=5700)
    Enemy(5320, PLATFORMS[62].top, speed=1.3),   # connector platform (x=5300)
    Enemy(5920, PLATFORMS[56].top, speed=1.4),   # middle tier end (x=5900)
    
    # Zone 7 - final epic challenge
    Enemy(6200, PLATFORMS[66].top, speed=1.4),   # epic start low (x=6100)
    Enemy(6450, PLATFORMS[68].top, speed=1.5),   # middle epic (x=6400)
    Enemy(6700, PLATFORMS[71].top, speed=1.6),   # upper epic (x=6620)
    Enemy(6250, PLATFORMS[76].top, speed=1.5),   # zigzag challenge (x=6200)
    Enemy(6850, PLATFORMS[67].top, speed=1.5),   # final mid approach (x=6900)
    Enemy(7000, PLATFORMS[80].top, speed=1.6),   # penultimate platform (x=6980)
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
        # Explicitly set football count for extended level
        self.coins_total = 27  # Updated for extended 7000px level with more footballs
        self.coins_collected = 0  # Track collected separately
        # Death animation state
        self.is_dying = False
        self.death_vx = 0
        self.death_vy = 0
        self.death_started = False
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
        # If dying, only update death animation
        if self.is_dying:
            return self.update_death_animation(dt)
        
        # Normal gameplay update
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
                self.coins_collected += 1  # Track collected count
                self.score += 100

        if self.invuln_timer > 0:
            self.invuln_timer -= 1
        
        return False  # Not dying, so return False

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
        if self.lives <= 0:
            self.lives = 0
            # Trigger death animation on final life lost
            if not self.is_dying:
                self.start_death_animation()

    def start_death_animation(self):
        """Start the Mario-style death animation"""
        global death_animation_active, death_animation_time
        self.is_dying = True
        self.death_started = True
        death_animation_active = True
        death_animation_time = 0.0
        # Launch Bevo upward with slight horizontal movement
        self.death_vy = death_launch_velocity
        self.death_vx = 2 if self.facing_right else -2  # Slight horizontal drift

    def update_death_animation(self, dt):
        """Update the death animation physics"""
        if not self.is_dying:
            return False
        
        # Apply gravity to death velocity
        self.death_vy += GRAVITY * 1.5  # Faster gravity for death fall
        
        # Update position
        self.rect.x += int(self.death_vx * dt * 60)
        self.rect.y += int(self.death_vy * dt * 60)
        
        # Return True if Bevo has fallen off screen
        return self.rect.top > VIRTUAL_H + 100

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
    global flag_reached, win_animation_time, confetti_particles, death_animation_active, death_animation_time, FOOTBALLS
    flag_reached = False
    win_animation_time = 0.0
    confetti_particles = []
    death_animation_active = False
    death_animation_time = 0.0
    
    # Reset player state
    player.lives = 3
    player.score = 0
    player.invuln_timer = 0
    player.is_dying = False
    player.death_started = False
    player.coins_collected = 0  # Reset collected count
    
    # Reset footballs ONCE and set the total count correctly
    place_footballs()
    # Always set to 27 - the correct total number of footballs for extended level
    player.coins_total = 27
    print(f"DEBUG: Reset game - footballs placed: {len(FOOTBALLS)}, player.coins_total set to: {player.coins_total}")
    player.spawn()

    # Reset enemies to original layout
    ENEMIES[:] = [
        # Zone 1 - placed on lower path platforms for easier introduction
        Enemy(500,  PLATFORMS[2].top,  speed=1.1),   # on gentle rise platform (x=400)
        Enemy(750,  PLATFORMS[4].top,  speed=1.1),   # on slight drop platform (x=900)

        # Zone 2 - spread across different height paths  
        Enemy(1200, PLATFORMS[9].top,  speed=1.2),   # lower-middle path (x=1100)
        Enemy(1500, PLATFORMS[13].top, speed=1.3),   # middle path (x=1200)
        Enemy(1750, PLATFORMS[16].top, speed=1.2),   # middle path (x=1900)

        # Zone 3 - maze section enemies on connectors and main paths
        Enemy(2120, PLATFORMS[21].top, speed=1.3),   # low connector platform (x=2100)
        Enemy(2400, PLATFORMS[24].top, speed=1.3),   # lower maze section (x=2300)
        Enemy(2600, PLATFORMS[27].top, speed=1.4),   # middle maze section (x=2350)
        Enemy(2350, PLATFORMS[30].top, speed=1.3),   # upper maze section (x=2280)

        # Zone 4 - tower climbing challenges
        Enemy(3200, PLATFORMS[33].top, speed=1.4),   # base level (x=3100)
        Enemy(3400, PLATFORMS[34].top, speed=1.4),   # step up (x=3350)
        Enemy(3500, PLATFORMS[36].top, speed=1.4),   # continue up (x=3450)
        Enemy(3750, PLATFORMS[39].top, speed=1.3),   # bypass low (x=3650)

        # Zone 5 - final approach guards
        Enemy(4200, PLATFORMS[45].top, speed=1.4),   # middle steady approach (x=4150)
        Enemy(4550, PLATFORMS[49].top, speed=1.5),   # lower safe approach (x=4500)
        
        # Zone 6 - extended challenge gauntlet
        Enemy(5200, PLATFORMS[53].top, speed=1.3),   # lower tier (x=5100)
        Enemy(5450, PLATFORMS[55].top, speed=1.4),   # middle tier (x=5400)
        Enemy(5750, PLATFORMS[58].top, speed=1.5),   # upper tier (x=5700)
        Enemy(5320, PLATFORMS[62].top, speed=1.3),   # connector platform (x=5300)
        Enemy(5920, PLATFORMS[56].top, speed=1.4),   # middle tier end (x=5900)
        
        # Zone 7 - final epic challenge
        Enemy(6200, PLATFORMS[66].top, speed=1.4),   # epic start low (x=6100)
        Enemy(6450, PLATFORMS[68].top, speed=1.5),   # middle epic (x=6400)
        Enemy(6700, PLATFORMS[71].top, speed=1.6),   # upper epic (x=6620)
        Enemy(6250, PLATFORMS[76].top, speed=1.5),   # zigzag challenge (x=6200)
        Enemy(6850, PLATFORMS[67].top, speed=1.5),   # final mid approach (x=6900)
        Enemy(7000, PLATFORMS[80].top, speed=1.6),   # penultimate platform (x=6980)
    ]

def reset_level(player):
    global flag_reached, win_animation_time, confetti_particles, death_animation_active, death_animation_time, FOOTBALLS
    flag_reached = False
    win_animation_time = 0.0
    confetti_particles = []
    death_animation_active = False
    death_animation_time = 0.0
    
    player.is_dying = False
    player.death_started = False
    player.coins_collected = 0  # Reset collected count
    
    # Reset footballs and update count
    place_footballs()
    # Always set to 27 - the correct total number of footballs for extended level
    player.coins_total = 27
    print(f"DEBUG: Reset level - footballs placed: {len(FOOTBALLS)}, player.coins_total set to: {player.coins_total}")
    player.spawn()
    
    ENEMIES[:] = [
        # Zone 1 - placed on lower path platforms for easier introduction
        Enemy(500,  PLATFORMS[2].top,  speed=1.1),   # on gentle rise platform (x=400)
        Enemy(750,  PLATFORMS[4].top,  speed=1.1),   # on slight drop platform (x=900)

        # Zone 2 - spread across different height paths  
        Enemy(1200, PLATFORMS[9].top,  speed=1.2),   # lower-middle path (x=1100)
        Enemy(1500, PLATFORMS[13].top, speed=1.3),   # middle path (x=1200)
        Enemy(1750, PLATFORMS[16].top, speed=1.2),   # middle path (x=1900)

        # Zone 3 - maze section enemies on connectors and main paths
        Enemy(2120, PLATFORMS[21].top, speed=1.3),   # low connector platform (x=2100)
        Enemy(2400, PLATFORMS[24].top, speed=1.3),   # lower maze section (x=2300)
        Enemy(2600, PLATFORMS[27].top, speed=1.4),   # middle maze section (x=2350)
        Enemy(2350, PLATFORMS[30].top, speed=1.3),   # upper maze section (x=2280)

        # Zone 4 - tower climbing challenges
        Enemy(3200, PLATFORMS[33].top, speed=1.4),   # base level (x=3100)
        Enemy(3400, PLATFORMS[34].top, speed=1.4),   # step up (x=3350)
        Enemy(3500, PLATFORMS[36].top, speed=1.4),   # continue up (x=3450)
        Enemy(3750, PLATFORMS[39].top, speed=1.3),   # bypass low (x=3650)

        # Zone 5 - final approach guards
        Enemy(4200, PLATFORMS[45].top, speed=1.4),   # middle steady approach (x=4150)
        Enemy(4550, PLATFORMS[49].top, speed=1.5),   # lower safe approach (x=4500)
        
        # Zone 6 - extended challenge gauntlet
        Enemy(5200, PLATFORMS[53].top, speed=1.3),   # lower tier (x=5100)
        Enemy(5450, PLATFORMS[55].top, speed=1.4),   # middle tier (x=5400)
        Enemy(5750, PLATFORMS[58].top, speed=1.5),   # upper tier (x=5700)
        Enemy(5320, PLATFORMS[62].top, speed=1.3),   # connector platform (x=5300)
        Enemy(5920, PLATFORMS[56].top, speed=1.4),   # middle tier end (x=5900)
        
        # Zone 7 - final epic challenge
        Enemy(6200, PLATFORMS[66].top, speed=1.4),   # epic start low (x=6100)
        Enemy(6450, PLATFORMS[68].top, speed=1.5),   # middle epic (x=6400)
        Enemy(6700, PLATFORMS[71].top, speed=1.6),   # upper epic (x=6620)
        Enemy(6250, PLATFORMS[76].top, speed=1.5),   # zigzag challenge (x=6200)
        Enemy(6850, PLATFORMS[67].top, speed=1.5),   # final mid approach (x=6900)
        Enemy(7000, PLATFORMS[80].top, speed=1.6),   # penultimate platform (x=6980)
    ]


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

        # --- Draw Win Animation if Bevo Reached Flag ---
    if flag_reached:
        draw_win_animation(surf)

# --- Win Animation Setup and Functions ---
try:
    GOLD_HAT_IMG = pygame.image.load("assets/gold_hat.png").convert_alpha()
except Exception:
    GOLD_HAT_IMG = None

try:
    CONFETTI_IMG = pygame.image.load("assets/orange_confetti.png").convert_alpha()
except Exception:
    CONFETTI_IMG = None

def spawn_confetti():
    """Initialize confetti animation when flag is reached."""
    global win_animation_time, confetti_particles
    win_animation_time = 0.0
    confetti_particles = []
    
    # Create initial burst of confetti particles at the top of screen
    screen_width = VIRTUAL_W  # Use virtual screen width
    num_particles = 50  # Number of confetti pieces
    
    for i in range(num_particles):
        # Spawn confetti across the top of the screen
        x = random.uniform(0, screen_width)
        y = random.uniform(-100, -20)  # Start above screen
        particle = ConfettiParticle(x, y, CONFETTI_IMG)
        confetti_particles.append(particle)

def draw_win_animation(surf):
    """Draw win animation on the screen with pulsing gold hat in center."""
    import math
    global confetti_particles
    
    sw, sh = surf.get_size()
    
    # Calculate pulsing scale using sine wave (creates smooth pulsing effect)
    pulse_speed = 3.0  # Speed of pulsing
    min_scale = 0.8    # Minimum size (80% of original)
    max_scale = 1.2    # Maximum size (120% of original)
    scale_range = (max_scale - min_scale) / 2
    base_scale = min_scale + scale_range
    pulse_scale = base_scale + scale_range * math.sin(win_animation_time * pulse_speed)
    
    # Draw animated confetti particles FIRST (so they appear behind the hat)
    for particle in confetti_particles:
        particle.draw(surf)
    
    # Draw gold hat in the center of the screen with pulsing effect (AFTER confetti, so it's in front)
    if GOLD_HAT_IMG is not None:
        # Calculate scaled dimensions - shrink by 100 pixels
        orig_w, orig_h = GOLD_HAT_IMG.get_size()
        # Reduce the base size by 100 pixels width (maintain aspect ratio)
        size_reduction = 100
        aspect_ratio = orig_h / orig_w
        reduced_w = max(50, orig_w - size_reduction)  # Ensure minimum size
        reduced_h = int(reduced_w * aspect_ratio)
        
        scaled_w = int(reduced_w * pulse_scale)
        scaled_h = int(reduced_h * pulse_scale)
        
        # Scale the image
        scaled_hat = pygame.transform.smoothscale(GOLD_HAT_IMG, (scaled_w, scaled_h))
        
        # Position in center of screen, moved up 150 pixels
        hat_x = sw // 2 - scaled_w // 2
        hat_y = sh // 2 - scaled_h // 2 - 150  # Move up 150 pixels
        
        surf.blit(scaled_hat, (hat_x, hat_y))
        
        # Add victory text underneath the hat - SIMPLER positioning
        victory_text = "Bevo Wins The Red River Rivalry"
        victory_font_size = 28  # Slightly larger for visibility
        victory_font = pygame.font.SysFont("arial", victory_font_size, bold=True)  # Try Arial font
        victory_surf = victory_font.render(victory_text, True, (255, 140, 0))  # Orange text
        victory_x = sw // 2 - victory_surf.get_width() // 2
        
        # Much simpler positioning: just place it in the bottom half of the screen
        victory_y = int(sh * 0.75) + 50  # 75% down the screen + 50 pixels lower
        
        # Draw a bright white background rectangle
        text_bg_rect = pygame.Rect(victory_x - 10, victory_y - 5, victory_surf.get_width() + 20, victory_surf.get_height() + 10)
        pygame.draw.rect(surf, (255, 255, 255), text_bg_rect)  # Bright white background
        
        surf.blit(victory_surf, (victory_x, victory_y))
        
    else:
        # Fallback text if no hat image - also pulsing and repositioned
        text_scale = int(20 * pulse_scale)
        pulsing_font = pygame.font.SysFont("consolas", text_scale)
        text_surf = pulsing_font.render("🏆 WINNER! 🏆", True, WHITE)
        text_x = sw // 2 - text_surf.get_width() // 2
        text_y = sh // 2 - text_surf.get_height() // 2 - 150  # Move up 150 pixels
        surf.blit(text_surf, (text_x, text_y))
        
        # Add victory text for fallback - simple positioning
        victory_text = "Bevo Wins The Red River Rivalry"
        victory_font_size = 28  # Fixed size
        victory_font = pygame.font.SysFont("arial", victory_font_size, bold=True)
        victory_surf = victory_font.render(victory_text, True, (255, 140, 0))  # Orange text
        victory_x = sw // 2 - victory_surf.get_width() // 2
        victory_y = int(sh * 0.75) + 50  # 75% down the screen + 50 pixels lower
        
        # Bright white background for visibility
        text_bg_rect = pygame.Rect(victory_x - 10, victory_y - 5, victory_surf.get_width() + 20, victory_surf.get_height() + 10)
        pygame.draw.rect(surf, (255, 255, 255), text_bg_rect)  # Bright white background
            
        surf.blit(victory_surf, (victory_x, victory_y))
        surf.blit(victory_surf, (victory_x, victory_y))
    
    # Occasionally spawn new confetti to keep the effect going
    if win_animation_time > 1.0 and random.random() < 0.3:  # 30% chance each frame after 1 second
        # Add new confetti occasionally
        for i in range(random.randint(1, 3)):
            x = random.uniform(0, sw)
            y = random.uniform(-50, -20)
            particle = ConfettiParticle(x, y, CONFETTI_IMG)
            confetti_particles.append(particle)

def draw_hud(surf, player, msg=None):
    draw_text(surf, f"Score: {player.score}", 12, 10)
    # Use explicit collected count instead of calculation
    draw_text(surf, f"Footballs: {player.coins_collected}/{player.coins_total}", 12, 34)
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
    global move_left, move_right, jump_pressed, started, mixer_ready, GRUNT_SFX, flag_reached, win_animation_time, confetti_particles, death_animation_active, death_animation_time

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
                    # Only allow reset if not in death animation, OR if death animation finished and player is dead
                    if not death_animation_active and (player.lives > 0 or player.lives == 0):
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
        # Only allow player movement if not in death animation
        player_input_left = move_left if not death_animation_active else False
        player_input_right = move_right if not death_animation_active else False
        player_input_jump = jump_pressed if not death_animation_active else False
        
        death_animation_finished = player.update(dt, player_input_left, player_input_right, player_input_jump)
        
        # Update death animation timer
        if death_animation_active:
            death_animation_time += dt
            # Check if death animation is complete (Bevo fell off screen)
            if death_animation_finished:
                death_animation_active = False
                death_animation_time = 0.0
        
        # Only update enemies if not in death animation
        if not death_animation_active:
            for e in ENEMIES:
                e.update(dt)

        # Update win animation timer if flag is reached
        if flag_reached:
            win_animation_time += dt
            
            # Update confetti particles
            particles_to_remove = []
            for particle in confetti_particles:
                if particle.update(dt):
                    particles_to_remove.append(particle)
            
            # Remove expired particles
            for particle in particles_to_remove:
                confetti_particles.remove(particle)

        # Only check collisions and failures if not in death animation
        if not death_animation_active:
            check_fail(player)
            m, delta = check_enemy_collisions(player)
            if m:
                message = m
                message_timer = int(FPS * 1.2)
                player.score += delta

            # Create bevo_rect alias for player rectangle
            bevo_rect = player.rect
            
            # Flag collision detection
            if bevo_rect.colliderect(FLAG_RECT):
                if not flag_reached:
                    flag_reached = True
                    spawn_confetti()

        won = flag_reached

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
        if player.lives == 0 and not death_animation_active:
            state_msg = "Game Over! Press R to retry"
        elif death_animation_active:
            state_msg = ""  # No message during death animation
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
