import pygame
import json
import sys
import math
import random
from enum import Enum

# --- ENGINE INITIALIZATION ---
pygame.init()
WINDOW_WIDTH, WINDOW_HEIGHT = 1200, 800
HUD_HEIGHT = 60
FPS = 60
GRID_SIZE = 50

# MOONDUST SETTINGS: Massive Level Bounds
LEVEL_WIDTH = 4000
LEVEL_HEIGHT = 2000

screen = pygame.display.set_mode((WINDOW_WIDTH, WINDOW_HEIGHT), pygame.DOUBLEBUF)
pygame.display.set_caption("PyMoondust Engine [SMBX Clone]")
clock = pygame.time.Clock()

# --- COLORS ---
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
SKY_BLUE = (100, 149, 237)
DARK_BLUE = (25, 25, 112)
MENU_BG = (40, 0, 60)
HUD_BG = (50, 50, 50)

# --- ASSET GENERATOR (Procedural Graphics) ---
# We generate assets in code so you don't need to download pngs
def create_block_texture(color, style="solid"):
    surf = pygame.Surface((GRID_SIZE, GRID_SIZE))
    surf.fill(color)
    if style == "brick":
        pygame.draw.rect(surf, (0,0,0), (0,0,GRID_SIZE,GRID_SIZE), 2)
        pygame.draw.line(surf, (0,0,0), (0, GRID_SIZE//2), (GRID_SIZE, GRID_SIZE//2), 2)
        pygame.draw.line(surf, (0,0,0), (GRID_SIZE//2, 0), (GRID_SIZE//2, GRID_SIZE//2), 2)
        pygame.draw.line(surf, (0,0,0), (GRID_SIZE//4, GRID_SIZE//2), (GRID_SIZE//4, GRID_SIZE), 2)
        pygame.draw.line(surf, (0,0,0), (GRID_SIZE*0.75, GRID_SIZE//2), (GRID_SIZE*0.75, GRID_SIZE), 2)
    elif style == "question":
        pygame.draw.rect(surf, (180, 130, 0), (5,5,GRID_SIZE-10, GRID_SIZE-10))
        # Draw '?'
        pygame.draw.circle(surf, BLACK, (GRID_SIZE//2, GRID_SIZE//3), 5)
        pygame.draw.circle(surf, BLACK, (GRID_SIZE//2, GRID_SIZE*0.7), 5)
    return surf

ASSETS = {
    "ground": create_block_texture((139, 69, 19)),
    "grass_top": create_block_texture((34, 139, 34)),
    "brick": create_block_texture((178, 34, 34), "brick"),
    "question": create_block_texture((255, 215, 0), "question"),
    "pipe": create_block_texture((0, 180, 0)),
    "goomba": pygame.Surface((40, 40)),
    "player": pygame.Surface((40, 50))
}
ASSETS["goomba"].fill((165, 42, 42)); pygame.draw.circle(ASSETS["goomba"], WHITE, (12, 15), 5); pygame.draw.circle(ASSETS["goomba"], WHITE, (28, 15), 5)
ASSETS["player"].fill((255, 0, 0)); pygame.draw.rect(ASSETS["player"], (0,0,255), (0, 25, 40, 25))

# --- CORE ENGINE CLASSES ---

class Camera:
    def __init__(self, width, height):
        self.camera = pygame.Rect(0, 0, width, height)
        self.width = width
        self.height = height

    def apply(self, entity):
        return entity.rect.move(self.camera.topleft)

    def apply_rect(self, rect):
        return rect.move(self.camera.topleft)

    def update(self, target_rect):
        x = -target_rect.centerx + int(WINDOW_WIDTH / 2)
        y = -target_rect.centery + int(WINDOW_HEIGHT / 2)

        # Limit scrolling to map size
        x = min(0, max(-(self.width - WINDOW_WIDTH), x))
        y = min(0, max(-(self.height - WINDOW_HEIGHT), y))
        self.camera = pygame.Rect(x, y, self.width, self.height)

    def simple_pan(self, dx, dy):
        # For Editor Mode
        x = self.camera.x + dx
        y = self.camera.y + dy
        x = min(0, max(-(self.width - WINDOW_WIDTH), x))
        y = min(0, max(-(self.height - WINDOW_HEIGHT), y))
        self.camera = pygame.Rect(x, y, self.width, self.height)

class Entity(pygame.sprite.Sprite):
    def __init__(self, x, y, type_name):
        super().__init__()
        self.type_name = type_name
        self.image = ASSETS.get(type_name, ASSETS["ground"])
        self.rect = self.image.get_rect(topleft=(x, y))

class Player(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.image = ASSETS["player"]
        self.rect = self.image.get_rect(topleft=(x, y))
        self.vel = pygame.math.Vector2(0, 0)
        self.on_ground = False
        self.facing_right = True

    def update(self, blocks):
        keys = pygame.key.get_pressed()
        
        # Horizontal Movement
        if keys[pygame.K_LEFT]:
            self.vel.x = -6
            self.facing_right = False
        elif keys[pygame.K_RIGHT]:
            self.vel.x = 6
            self.facing_right = True
        else:
            self.vel.x *= 0.8 # Friction

        # Jump
        if keys[pygame.K_SPACE] and self.on_ground:
            self.vel.y = -18
            self.on_ground = False

        # Gravity
        self.vel.y += 0.8
        
        # Move X
        self.rect.x += self.vel.x
        hits = pygame.sprite.spritecollide(self, blocks, False)
        for block in hits:
            if self.vel.x > 0: self.rect.right = block.rect.left
            elif self.vel.x < 0: self.rect.left = block.rect.right
            self.vel.x = 0

        # Move Y
        self.rect.y += self.vel.y
        self.on_ground = False
        hits = pygame.sprite.spritecollide(self, blocks, False)
        for block in hits:
            if self.vel.y > 0: 
                self.rect.bottom = block.rect.top
                self.vel.y = 0
                self.on_ground = True
            elif self.vel.y < 0:
                self.rect.top = block.rect.bottom
                self.vel.y = 0

        # World Bounds
        if self.rect.left < 0: self.rect.left = 0
        if self.rect.right > LEVEL_WIDTH: self.rect.right = LEVEL_WIDTH
        if self.rect.bottom > LEVEL_HEIGHT: 
            self.rect.bottom = LEVEL_HEIGHT
            self.on_ground = True
            self.vel.y = 0

# --- SCENE MANAGER & DATA ---

class GameState(Enum):
    MENU = 0
    EPISODE_SELECT = 1
    EDITOR = 2
    GAMEPLAY = 3

current_state = GameState.MENU
camera = Camera(LEVEL_WIDTH, LEVEL_HEIGHT)
font = pygame.font.SysFont("Arial", 24)
large_font = pygame.font.SysFont("Arial", 48)

# Level Data
sprites_group = pygame.sprite.Group()
blocks_group = pygame.sprite.Group()
player = None

# Mock Episodes Database
episodes = [
    {"name": "The Princess Caper", "desc": "Classic adventure!"},
    {"name": "Mushroom Kingdom Fusion", "desc": "Hardcore difficulty."},
    {"name": "Luigi's Vacation", "desc": "Puzzle based levels."},
    {"name": "My New Episode", "desc": "Empty template."}
]
selected_episode_index = 0

# Editor Tools
editor_tiles = ["ground", "grass_top", "brick", "question", "pipe", "goomba"]
selected_tool_idx = 0

def reset_level():
    global player
    sprites_group.empty()
    blocks_group.empty()
    player = Player(100, LEVEL_HEIGHT - 300)
    sprites_group.add(player)
    
    # Create floor
    for x in range(0, LEVEL_WIDTH, GRID_SIZE):
        b = Entity(x, LEVEL_HEIGHT - GRID_SIZE, "ground")
        blocks_group.add(b)
        sprites_group.add(b)

# --- DRAWING HELPERS ---
def draw_parallax_bg():
    screen.fill(SKY_BLUE)
    # Draw simple clouds that move based on camera x
    cam_x = camera.camera.x
    for i in range(10):
        cloud_x = (i * 400 + cam_x * 0.5) % (WINDOW_WIDTH + 200) - 100
        pygame.draw.ellipse(screen, WHITE, (cloud_x, 100 + (i%3)*50, 100, 60))

def draw_hud(text):
    hud_rect = pygame.Rect(0, 0, WINDOW_WIDTH, HUD_HEIGHT)
    pygame.draw.rect(screen, HUD_BG, hud_rect)
    pygame.draw.line(screen, WHITE, (0, HUD_HEIGHT), (WINDOW_WIDTH, HUD_HEIGHT), 2)
    label = font.render(text, True, WHITE)
    screen.blit(label, (20, 20))

# --- SCENE LOOPS ---

def menu_loop():
    global current_state, running
    screen.fill(MENU_BG)
    
    title = large_font.render("MOONDUST ENGINE PYTHON", True, WHITE)
    screen.blit(title, (WINDOW_WIDTH//2 - title.get_width()//2, 200))

    opts = ["Start Engine", "Level Editor", "Quit"]
    mouse = pygame.mouse.get_pos()
    
    for i, opt in enumerate(opts):
        rect = pygame.Rect(WINDOW_WIDTH//2 - 100, 400 + i * 60, 200, 50)
        color = (100, 100, 200) if rect.collidepoint(mouse) else (50, 50, 150)
        pygame.draw.rect(screen, color, rect)
        pygame.draw.rect(screen, WHITE, rect, 2)
        
        txt = font.render(opt, True, WHITE)
        screen.blit(txt, (rect.centerx - txt.get_width()//2, rect.centery - txt.get_height()//2))

        if pygame.mouse.get_pressed()[0] and rect.collidepoint(mouse):
            if i == 0: current_state = GameState.EPISODE_SELECT
            elif i == 1: 
                reset_level()
                current_state = GameState.EDITOR
            elif i == 2: running = False
            pygame.time.wait(200)

def episode_select_loop():
    global current_state, selected_episode_index
    screen.fill(DARK_BLUE)
    
    title = large_font.render("SELECT EPISODE", True, WHITE)
    screen.blit(title, (50, 50))
    
    for i, ep in enumerate(episodes):
        color = (255, 215, 0) if i == selected_episode_index else (150, 150, 150)
        txt = font.render(f"> {ep['name']}" if i == selected_episode_index else f"  {ep['name']}", True, color)
        screen.blit(txt, (100, 150 + i * 40))
        
        if i == selected_episode_index:
            desc = font.render(ep['desc'], True, (200, 200, 200))
            screen.blit(desc, (400, 150 + i * 40))

    inst = font.render("[UP/DOWN] Select   [ENTER] Start Game   [ESC] Back", True, WHITE)
    screen.blit(inst, (50, WINDOW_HEIGHT - 50))
    
    # Input
    keys = pygame.key.get_pressed()
    # (Simple debouncing logic needed for real app, simplified here)
    for event in pygame.event.get():
        if event.type == pygame.QUIT: sys.exit()
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_UP: selected_episode_index = (selected_episode_index - 1) % len(episodes)
            if event.key == pygame.K_DOWN: selected_episode_index = (selected_episode_index + 1) % len(episodes)
            if event.key == pygame.K_RETURN: 
                reset_level()
                current_state = GameState.GAMEPLAY
            if event.key == pygame.K_ESCAPE: current_state = GameState.MENU

def editor_loop():
    global current_state, selected_tool_idx
    
    # Input
    keys = pygame.key.get_pressed()
    
    # Camera Pan (WASD)
    pan_speed = 10
    if keys[pygame.K_w]: camera.simple_pan(0, pan_speed)
    if keys[pygame.K_s]: camera.simple_pan(0, -pan_speed)
    if keys[pygame.K_a]: camera.simple_pan(pan_speed, 0)
    if keys[pygame.K_d]: camera.simple_pan(-pan_speed, 0)
    
    # Tool Selection
    for event in pygame.event.get():
        if event.type == pygame.QUIT: sys.exit()
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE: current_state = GameState.MENU
            if event.key == pygame.K_e: current_state = GameState.GAMEPLAY # Quick test
            if event.key == pygame.K_TAB:
                selected_tool_idx = (selected_tool_idx + 1) % len(editor_tiles)
        
        # Placing Blocks
        if event.type == pygame.MOUSEBUTTONDOWN or (event.type == pygame.MOUSEMOTION and pygame.mouse.get_pressed()[0]):
            mx, my = pygame.mouse.get_pos()
            # Convert Screen Coords -> World Coords
            world_x = mx - camera.camera.x
            world_y = my - camera.camera.y
            
            grid_x = (world_x // GRID_SIZE) * GRID_SIZE
            grid_y = (world_y // GRID_SIZE) * GRID_SIZE
            
            if pygame.mouse.get_pressed()[2]: # Right click delete
                for s in sprites_group:
                    if s.rect.collidepoint(world_x, world_y) and s != player:
                        s.kill()
            else: # Left click place
                # Check occupancy
                occupied = False
                for s in sprites_group:
                    if s.rect.collidepoint(world_x + 10, world_y + 10): occupied = True
                
                if not occupied:
                    tile_type = editor_tiles[selected_tool_idx]
                    ent = Entity(grid_x, grid_y, tile_type)
                    sprites_group.add(ent)
                    if tile_type != "goomba":
                        blocks_group.add(ent)

    # Drawing
    draw_parallax_bg()
    
    # Grid
    cam_x, cam_y = camera.camera.x, camera.camera.y
    start_x = -(cam_x % GRID_SIZE)
    start_y = -(cam_y % GRID_SIZE)
    
    for x in range(start_x, WINDOW_WIDTH, GRID_SIZE):
        pygame.draw.line(screen, (255,255,255,50), (x, 0), (x, WINDOW_HEIGHT))
    for y in range(start_y, WINDOW_HEIGHT, GRID_SIZE):
        pygame.draw.line(screen, (255,255,255,50), (0, y), (WINDOW_WIDTH, y))
        
    for sprite in sprites_group:
        screen.blit(sprite.image, camera.apply(sprite))

    # Editor HUD
    draw_hud(f"EDITOR MODE | Tool: {editor_tiles[selected_tool_idx]} | WASD: Pan | Click: Place | R-Click: Delete | E: Test | TAB: Switch Tool")
    
    # Draw Tool Preview
    preview = ASSETS.get(editor_tiles[selected_tool_idx], ASSETS["ground"])
    screen.blit(preview, (WINDOW_WIDTH - 60, 10))

def gameplay_loop():
    global current_state
    
    for event in pygame.event.get():
        if event.type == pygame.QUIT: sys.exit()
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE: current_state = GameState.MENU
            if event.key == pygame.K_e: current_state = GameState.EDITOR

    # Logic
    player.update(blocks_group)
    camera.update(player.rect)
    
    # Drawing
    draw_parallax_bg()
    
    # Draw visible sprites only
    for sprite in sprites_group:
        if camera.camera.colliderect(sprite.rect):
            screen.blit(sprite.image, camera.apply(sprite))
            
    draw_hud("GAMEPLAY | Arrows: Move | Space: Jump | E: Edit Mode | ESC: Menu")

# --- MAIN EXECUTION ---
reset_level()
running = True

while running:
    if current_state == GameState.MENU:
        menu_loop()
    elif current_state == GameState.EPISODE_SELECT:
        episode_select_loop()
    elif current_state == GameState.EDITOR:
        editor_loop()
    elif current_state == GameState.GAMEPLAY:
        gameplay_loop()
        
    pygame.display.flip()
    clock.tick(FPS)

pygame.quit()
