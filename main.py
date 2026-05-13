import asyncio
import json
import random
from pathlib import Path

import pygame

pygame.init()

WIDTH, HEIGHT = 360, 640
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Pinga Ana Adventure")
clock = pygame.time.Clock()


def _first_square_frame(surf: pygame.Surface) -> pygame.Surface:
    """Tiras horizontais (ex. 600x100 com frames 100x100): usa só o 1.º frame quadrado."""
    w, h = surf.get_size()
    if w > h and h >= 16:
        return surf.subsurface((0, 0, h, h)).copy()
    return surf


def _crop_to_opaque_bounds(surf: pygame.Surface) -> pygame.Surface:
    """Remove margens transparentes para o escalonamento preencher o tamanho do sprite (rect = imagem visível)."""
    try:
        m = pygame.mask.from_surface(surf, 127)
    except (ValueError, pygame.error):
        return surf
    rects = m.get_bounding_rects()
    if not rects:
        return surf
    bb = pygame.Rect(rects[0])
    for r in rects[1:]:
        bb.union_ip(r)
    bb = bb.clip(surf.get_rect())
    if bb.width < 2 or bb.height < 2:
        return surf
    return surf.subsurface(bb).copy()


def load_game_config() -> dict:
    """Lê `game_config.json` junto a `main.py` ou, na raiz do projecto, `assets/game_config.json`."""
    base = Path(__file__).resolve().parent
    defaults: dict = {
        "player": {"hits_until_death": 1},
        "enemies": {"orc": {"hits_to_destroy": 2}},
    }
    paths: list[Path] = [base / "game_config.json"]
    if base.name != "assets" and (base / "assets").is_dir():
        paths.append(base / "assets" / "game_config.json")
    for path in paths:
        if not path.is_file():
            continue
        try:
            with open(path, encoding="utf-8") as f:
                patch = json.load(f)
            if isinstance(patch.get("player"), dict):
                defaults["player"].update(patch["player"])
            if isinstance(patch.get("enemies"), dict):
                for name, stats in patch["enemies"].items():
                    if isinstance(stats, dict):
                        defaults["enemies"].setdefault(name, {"hits_to_destroy": 1})
                        defaults["enemies"][name].update(stats)
            break
        except (OSError, json.JSONDecodeError):
            continue
    return defaults


def _load_scaled_png(filename: str, size: tuple[int, int]) -> pygame.Surface | None:
    """Local: main.py na raiz e PNGs em assets/. Web (pygbag): main.py e PNGs no mesmo assets/."""
    base = Path(__file__).resolve().parent
    for path in (base / filename, base / "assets" / filename):
        try:
            surf = pygame.image.load(str(path)).convert_alpha()
            surf = _first_square_frame(surf)
            surf = _crop_to_opaque_bounds(surf)
            return pygame.transform.smoothscale(surf, size)
        except (FileNotFoundError, OSError, pygame.error, ValueError):
            continue
    return None


BLACK = (20, 20, 25)
WHITE = (255, 255, 255)
GOLD = (255, 215, 0)
RED_OFF = (90, 45, 50)
GREEN_ON = (40, 85, 55)

# +25% face aos tamanhos base (48 / 32 / 12)
SIZE_SCALE = 1.25
PLAYER_SIZE = (int(round(48 * SIZE_SCALE)), int(round(48 * SIZE_SCALE)))
ENEMY_SIZE = (int(round(32 * SIZE_SCALE)), int(round(32 * SIZE_SCALE)))
BULLET_SIZE = (int(round(12 * SIZE_SCALE)), int(round(12 * SIZE_SCALE)))
PLAYER_FALLBACK = (int(round(32 * SIZE_SCALE)), int(round(32 * SIZE_SCALE)))
ENEMY_FALLBACK = (int(round(24 * SIZE_SCALE)), int(round(24 * SIZE_SCALE)))
BULLET_FALLBACK = (int(round(8 * SIZE_SCALE)), int(round(8 * SIZE_SCALE)))
SPAWN_PAD = int(round(20 * SIZE_SCALE))


class Player(pygame.sprite.Sprite):
    def __init__(self) -> None:
        super().__init__()
        self.image = _load_scaled_png("player.png", PLAYER_SIZE)
        if self.image is None:
            self.image = pygame.Surface(PLAYER_FALLBACK)
            self.image.fill(GOLD)

        self.rect = self.image.get_rect(center=(WIDTH // 2, HEIGHT // 2))
        self.pos = pygame.Vector2(self.rect.center)
        self.speed = 3

    def move(self, target_pos: tuple[float, float] | None) -> None:
        if not target_pos:
            return
        target_vec = pygame.Vector2(target_pos)
        direction = target_vec - self.pos
        if direction.length() > 5:
            direction = direction.normalize()
            self.pos += direction * self.speed
            self.rect.center = (int(self.pos.x), int(self.pos.y))


class Enemy(pygame.sprite.Sprite):
    def __init__(self, _player_pos: pygame.Vector2, *, hits_to_destroy: int = 1) -> None:
        super().__init__()
        self.image = _load_scaled_png("enemy.png", ENEMY_SIZE)
        if self.image is None:
            self.image = pygame.Surface(ENEMY_FALLBACK)
            self.image.fill((200, 0, 0))

        self.hits_to_destroy = max(1, int(hits_to_destroy))
        self.hits_left = self.hits_to_destroy

        side = random.choice(["t", "b", "l", "r"])
        if side == "t":
            self.pos = pygame.Vector2(random.randint(0, WIDTH), -SPAWN_PAD)
        elif side == "b":
            self.pos = pygame.Vector2(random.randint(0, WIDTH), HEIGHT + SPAWN_PAD)
        elif side == "l":
            self.pos = pygame.Vector2(-SPAWN_PAD, random.randint(0, HEIGHT))
        else:
            self.pos = pygame.Vector2(WIDTH + SPAWN_PAD, random.randint(0, HEIGHT))

        self.rect = self.image.get_rect(center=(int(self.pos.x), int(self.pos.y)))
        self.speed = 1.5

    def take_bullet_hit(self) -> bool:
        """Devolve True se o inimigo morreu (tiros esgotados)."""
        self.hits_left -= 1
        return self.hits_left <= 0

    def update(self, player_pos: pygame.Vector2) -> None:
        diff = pygame.Vector2(player_pos) - self.pos
        if diff.length_squared() < 1e-6:
            return
        direction = diff.normalize()
        self.pos += direction * self.speed
        self.rect.center = (int(self.pos.x), int(self.pos.y))


class Bullet(pygame.sprite.Sprite):
    def __init__(self, start_pos: pygame.Vector2, target_pos: pygame.Vector2) -> None:
        super().__init__()
        self.image = _load_scaled_png("note.png", BULLET_SIZE)
        if self.image is None:
            self.image = pygame.Surface(BULLET_FALLBACK)
            self.image.fill(WHITE)

        self.rect = self.image.get_rect(center=(int(start_pos.x), int(start_pos.y)))
        self.pos = pygame.Vector2(start_pos)
        diff = pygame.Vector2(target_pos) - self.pos
        if diff.length_squared() < 1e-6:
            diff = pygame.Vector2(1, 0)
        self.dir = diff.normalize()
        self.speed = 7

    def update(self) -> None:
        self.pos += self.dir * self.speed
        self.rect.center = (int(self.pos.x), int(self.pos.y))
        if not screen.get_rect().colliderect(self.rect):
            self.kill()


def _shoot_toggle_rect() -> pygame.Rect:
    return pygame.Rect(WIDTH - 136, 6, 126, 38)


async def main() -> None:
    cfg = load_game_config()
    orc_hits = int(cfg["enemies"].get("orc", {}).get("hits_to_destroy", 2))
    player_max_hp = max(1, int(cfg["player"].get("hits_until_death", 1)))

    player = Player()
    all_sprites = pygame.sprite.Group(player)
    enemies = pygame.sprite.Group()
    bullets = pygame.sprite.Group()

    target_move_pos: tuple[float, float] | None = None
    spawn_timer = 0
    shoot_timer = 0
    score = 0
    player_hp = player_max_hp
    game_over = False
    shooting_enabled = True
    font = pygame.font.SysFont(None, 32)
    font_btn = pygame.font.SysFont(None, 22)
    font_death = pygame.font.SysFont(None, 44)
    shoot_btn = _shoot_toggle_rect()

    def reset_run() -> None:
        nonlocal player, all_sprites, enemies, bullets, target_move_pos
        nonlocal spawn_timer, shoot_timer, score, player_hp, game_over
        player = Player()
        all_sprites = pygame.sprite.Group(player)
        enemies = pygame.sprite.Group()
        bullets = pygame.sprite.Group()
        target_move_pos = None
        spawn_timer = 0
        shoot_timer = 0
        score = 0
        player_hp = player_max_hp
        game_over = False

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            if game_over:
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    reset_run()
                elif event.type == pygame.FINGERDOWN:
                    reset_run()
                continue

            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if shoot_btn.collidepoint(event.pos):
                    shooting_enabled = not shooting_enabled
                else:
                    target_move_pos = event.pos

            if event.type == pygame.MOUSEMOTION and pygame.mouse.get_pressed()[0]:
                if not shoot_btn.collidepoint(event.pos):
                    target_move_pos = event.pos

            if event.type == pygame.FINGERDOWN:
                fx, fy = event.x * WIDTH, event.y * HEIGHT
                if shoot_btn.collidepoint(fx, fy):
                    shooting_enabled = not shooting_enabled
                else:
                    target_move_pos = (fx, fy)
            if event.type == pygame.FINGERMOTION:
                target_move_pos = (event.x * WIDTH, event.y * HEIGHT)

        if not game_over:
            player.move(target_move_pos)

            spawn_timer += 1
            if spawn_timer > 60:
                enemy = Enemy(player.pos, hits_to_destroy=orc_hits)
                enemies.add(enemy)
                all_sprites.add(enemy)
                spawn_timer = 0

            shoot_timer += 1
            if shooting_enabled and shoot_timer > 40 and enemies:
                closest = min(
                    enemies,
                    key=lambda e: pygame.Vector2(e.pos).distance_to(player.pos),
                )
                bullet = Bullet(player.pos, closest.pos)
                bullets.add(bullet)
                all_sprites.add(bullet)
                shoot_timer = 0

            enemies.update(player.pos)
            bullets.update()

            for bullet in list(bullets):
                struck = pygame.sprite.spritecollide(bullet, enemies, dokill=False)
                if not struck:
                    continue
                bullet.kill()
                enemy = struck[0]
                if enemy.take_bullet_hit():
                    enemy.kill()
                    score += 1

            if pygame.sprite.spritecollide(player, enemies, False):
                player_hp -= 1
                for e in enemies:
                    e.kill()
                for b in list(bullets):
                    b.kill()
                if player_hp <= 0:
                    game_over = True

        screen.fill(BLACK)
        all_sprites.draw(screen)

        score_txt = font.render(f"Pinga Score: {score}", True, WHITE)
        screen.blit(score_txt, (10, 10))

        hp_txt = font.render(f"Vida: {player_hp}/{player_max_hp}", True, WHITE)
        screen.blit(hp_txt, (10, 42))

        btn_bg = GREEN_ON if shooting_enabled else RED_OFF
        pygame.draw.rect(screen, btn_bg, shoot_btn, border_radius=8)
        pygame.draw.rect(screen, WHITE, shoot_btn, 2, border_radius=8)
        btn_label = "Tiro: ON" if shooting_enabled else "Tiro: OFF"
        btn_txt = font_btn.render(btn_label, True, WHITE)
        screen.blit(btn_txt, btn_txt.get_rect(center=shoot_btn.center))

        if game_over:
            msg = font_death.render("vc morreu", True, WHITE)
            screen.blit(msg, msg.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 36)))
            hint = font_btn.render("Clique ou toque para recomeçar", True, (190, 190, 200))
            screen.blit(hint, hint.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 24)))

        pygame.display.flip()

        await asyncio.sleep(0)
        clock.tick(60)


asyncio.run(main())
