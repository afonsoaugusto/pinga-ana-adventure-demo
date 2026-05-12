import asyncio
import random

import pygame

pygame.init()

WIDTH, HEIGHT = 360, 640
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Pinga Ana Adventure")
clock = pygame.time.Clock()

BLACK = (20, 20, 25)
WHITE = (255, 255, 255)
GOLD = (255, 215, 0)


class Player(pygame.sprite.Sprite):
    def __init__(self) -> None:
        super().__init__()
        try:
            self.image = pygame.image.load("assets/player.png").convert_alpha()
            self.image = pygame.transform.scale(self.image, (48, 48))
        except Exception:
            self.image = pygame.Surface((32, 32))
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
    def __init__(self, _player_pos: pygame.Vector2) -> None:
        super().__init__()
        try:
            self.image = pygame.image.load("assets/enemy.png").convert_alpha()
            self.image = pygame.transform.scale(self.image, (32, 32))
        except Exception:
            self.image = pygame.Surface((24, 24))
            self.image.fill((200, 0, 0))

        side = random.choice(["t", "b", "l", "r"])
        if side == "t":
            self.pos = pygame.Vector2(random.randint(0, WIDTH), -20)
        elif side == "b":
            self.pos = pygame.Vector2(random.randint(0, WIDTH), HEIGHT + 20)
        elif side == "l":
            self.pos = pygame.Vector2(-20, random.randint(0, HEIGHT))
        else:
            self.pos = pygame.Vector2(WIDTH + 20, random.randint(0, HEIGHT))

        self.rect = self.image.get_rect(center=(int(self.pos.x), int(self.pos.y)))
        self.speed = 1.5

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
        try:
            self.image = pygame.image.load("assets/note.png").convert_alpha()
            self.image = pygame.transform.scale(self.image, (12, 12))
        except Exception:
            self.image = pygame.Surface((8, 8))
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


async def main() -> None:
    player = Player()
    all_sprites = pygame.sprite.Group(player)
    enemies = pygame.sprite.Group()
    bullets = pygame.sprite.Group()

    target_move_pos: tuple[float, float] | None = None
    spawn_timer = 0
    shoot_timer = 0
    score = 0
    font = pygame.font.SysFont(None, 32)

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            if event.type in (pygame.MOUSEBUTTONDOWN, pygame.MOUSEMOTION):
                if pygame.mouse.get_pressed()[0]:
                    target_move_pos = event.pos
            if event.type == pygame.FINGERDOWN:
                target_move_pos = (event.x * WIDTH, event.y * HEIGHT)
            if event.type == pygame.FINGERMOTION:
                target_move_pos = (event.x * WIDTH, event.y * HEIGHT)

        player.move(target_move_pos)

        spawn_timer += 1
        if spawn_timer > 60:
            enemy = Enemy(player.pos)
            enemies.add(enemy)
            all_sprites.add(enemy)
            spawn_timer = 0

        shoot_timer += 1
        if shoot_timer > 40 and enemies:
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

        hits = pygame.sprite.groupcollide(enemies, bullets, True, True)
        if hits:
            score += len(hits)

        if pygame.sprite.spritecollide(player, enemies, False):
            score = 0
            for e in enemies:
                e.kill()

        screen.fill(BLACK)
        all_sprites.draw(screen)

        score_txt = font.render(f"Pinga Score: {score}", True, WHITE)
        screen.blit(score_txt, (10, 10))

        pygame.display.flip()

        await asyncio.sleep(0)
        clock.tick(60)


asyncio.run(main())
