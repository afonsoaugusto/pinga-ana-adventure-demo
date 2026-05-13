import array
import asyncio
import io
import json
import math
import random
import struct
import sys
from pathlib import Path

import pygame


def _compute_runs_in_browser_wasm() -> bool:
    """pygbag/pyodide: emscripten/wasi, módulo js, pyodide em sys.modules, ou wasm em machine()."""
    if sys.platform in ("emscripten", "wasi"):
        return True
    try:
        __import__("js")
        return True
    except ImportError:
        pass
    for mod in sys.modules:
        if mod.startswith("pyodide"):
            return True
    try:
        import platform as _plt

        return "wasm" in _plt.machine().lower()
    except Exception:
        return False


pygame.init()

_RUNS_IN_BROWSER_WASM = _compute_runs_in_browser_wasm()

if _RUNS_IN_BROWSER_WASM:
    try:
        pygame.mixer.quit()
    except pygame.error:
        pass


def _mono16_pcm_to_wav(samples: array.array, sample_rate: int) -> bytes:
    """PCM mono 16-bit LE → ficheiro WAV em bytes.

    Não usar o stdlib `wave`: no pygbag o PEP 723 tenta `pip install wave` e instala
    um pacote PyPI incompatível, quebrando o arranque no browser.
    """
    pcm = samples.tobytes()
    n = len(pcm)
    header = struct.pack(
        "<4sI4s4sIHHIIHH4sI",
        b"RIFF",
        36 + n,
        b"WAVE",
        b"fmt ",
        16,
        1,
        1,
        sample_rate,
        sample_rate * 2,
        2,
        16,
        b"data",
        n,
    )
    return header + pcm


def _synth_hit_enemy(sr: int = 22050) -> bytes:
    """Impacto curto: ruído + grave em decaimento (acerto no inimigo)."""
    dur = 0.075
    n = max(1, int(sr * dur))
    out = array.array("h")
    for i in range(n):
        t = i / sr
        env = math.exp(-18.0 * i / n)
        f = 280.0 * math.exp(-9.0 * t)
        thump = 0.5 * math.sin(2 * math.pi * f * t)
        noise = (random.random() * 2.0 - 1.0) * 0.38
        s = (thump + noise) * env
        out.append(int(max(-1.0, min(1.0, s)) * 30000))
    return _mono16_pcm_to_wav(out, sr)


def _synth_hurt_player(sr: int = 22050) -> bytes:
    """Tom mais baixo que desce (levou dano)."""
    dur = 0.2
    n = max(1, int(sr * dur))
    out = array.array("h")
    for i in range(n):
        t = i / sr
        f = 175.0 - 105.0 * (i / n)
        env = math.sin(math.pi * i / n) ** 1.4
        s = 0.72 * math.sin(2 * math.pi * f * t) * env
        out.append(int(max(-1.0, min(1.0, s)) * 30500))
    return _mono16_pcm_to_wav(out, sr)


def _synth_bg_loop(sr: int = 22050) -> bytes:
    """Loop ambiente suave (acordes graves + tremolo)."""
    dur = 2.56
    n = max(1, int(sr * dur))
    freqs = (98.0, 130.81, 164.81, 196.0)
    out = array.array("h")
    edge = max(1, int(sr * 0.05))
    for i in range(n):
        t = i / sr
        trem = 0.82 + 0.18 * math.sin(2 * math.pi * 0.42 * t)
        s = 0.0
        for k, f in enumerate(freqs):
            s += (0.2 / len(freqs)) * math.sin(2 * math.pi * f * t + 0.35 * k)
        s *= trem
        fade = 1.0
        if i < edge:
            fade = i / edge
        elif i > n - edge:
            fade = (n - 1 - i) / max(1, edge - 1)
        s *= fade
        out.append(int(max(-1.0, min(1.0, s * 0.5)) * 26000))
    return _mono16_pcm_to_wav(out, sr)


def load_procedural_sounds() -> tuple[pygame.mixer.Sound | None, pygame.mixer.Sound | None, pygame.mixer.Sound | None]:
    """Sons gerados em memória (sem ficheiros externos). Devolve (hit_inimigo, dano_jogador, musica_fundo)."""
    if _RUNS_IN_BROWSER_WASM:
        return None, None, None
    try:
        if pygame.mixer.get_init() is None:
            pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=1024)
        pygame.mixer.set_num_channels(16)
        hit = pygame.mixer.Sound(io.BytesIO(_synth_hit_enemy()))
        hurt = pygame.mixer.Sound(io.BytesIO(_synth_hurt_player()))
        bg = pygame.mixer.Sound(io.BytesIO(_synth_bg_loop()))
        hit.set_volume(0.52)
        hurt.set_volume(0.62)
        bg.set_volume(0.2)
        return hit, hurt, bg
    except (pygame.error, OSError, ValueError):
        return None, None, None

WIDTH, HEIGHT = 360, 640
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Pinga Ana Adventure")
clock = pygame.time.Clock()


def _present_display() -> None:
    """No browser o canvas SDL costuma actualizar-se melhor com update() que com flip()."""
    if _RUNS_IN_BROWSER_WASM:
        pygame.display.update()
    else:
        pygame.display.flip()


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


DEFAULT_CHARACTERS: list[dict] = [
    {
        "id": "arthas",
        "sprite": "player_arthas.png",
        "name": "Arthas",
        "title": "O Pirata",
        "forca": 1,
        "resistencia": 1,
        "velocidade": 1,
        "velocidade_tiro": 1,
    },
    {
        "id": "penetrus",
        "sprite": "player_penetrus.png",
        "name": "Penetrus",
        "title": "Mago",
        "forca": 2,
        "resistencia": 1,
        "velocidade": 1,
        "velocidade_tiro": 2,
    },
    {
        "id": "uni_orc",
        "sprite": "player_uni_orc.png",
        "name": "Uni-Orc",
        "title": "Orc Unicórnio",
        "forca": 1,
        "resistencia": 2,
        "velocidade": 1,
        "velocidade_tiro": 1,
    },
    {
        "id": "red_oni",
        "sprite": "player_red_oni.png",
        "name": "Red Oni",
        "title": "Demônio japonês",
        "forca": 2,
        "resistencia": 1,
        "velocidade": 2,
        "velocidade_tiro": 1,
    },
    {
        "id": "sr_baldius",
        "sprite": "player_sr_baldius.png",
        "name": "Sr. Baldius",
        "title": "Soldado Templário",
        "forca": 2,
        "resistencia": 2,
        "velocidade": 1,
        "velocidade_tiro": 1,
    },
]


def _normalize_character(raw: dict) -> dict | None:
    if not isinstance(raw, dict):
        return None
    cid = raw.get("id")
    name = raw.get("name")
    if not isinstance(cid, str) or not cid.strip():
        return None
    if not isinstance(name, str) or not name.strip():
        return None
    title = raw.get("title", "")
    if not isinstance(title, str):
        title = str(title)

    def _num(key: str, default: float = 1.0) -> float:
        v = raw.get(key, default)
        try:
            n = float(v)
        except (TypeError, ValueError):
            return default
        return max(0.1, n)

    cid_key = cid.strip()
    sprite_raw = raw.get("sprite")
    if isinstance(sprite_raw, str) and sprite_raw.strip():
        sprite = sprite_raw.strip()
    else:
        sprite = f"player_{cid_key}.png"

    return {
        "id": cid_key,
        "sprite": sprite,
        "name": name.strip(),
        "title": title.strip(),
        "forca": _num("forca", 1.0),
        "resistencia": int(max(1, round(_num("resistencia", 1.0)))),
        "velocidade": _num("velocidade", 1.0),
        "velocidade_tiro": _num("velocidade_tiro", 1.0),
    }


def load_characters_from_config(patch: dict) -> list[dict]:
    raw_list = patch.get("characters")
    if not isinstance(raw_list, list) or not raw_list:
        return [dict(c) for c in DEFAULT_CHARACTERS]
    out: list[dict] = []
    for item in raw_list:
        norm = _normalize_character(item) if isinstance(item, dict) else None
        if norm:
            out.append(norm)
    return out if out else [dict(c) for c in DEFAULT_CHARACTERS]


DEFAULT_ENEMIES_MERGE: dict[str, dict] = {
    "orc": {
        "sprite": "enemy.png",
        "resistencia": 2,
        "velocidade": 1.0,
        "comeca_apos_pontos": 0,
    },
    "soldado": {
        "sprite": "Characters(100x100)/Soldier/Soldier/Soldier-Idle.png",
        "resistencia": 2,
        "velocidade": 0.58,
        "comeca_apos_pontos": 10,
    },
}


def _normalize_enemy_entry(stats: dict, eid: str) -> dict:
    resistencia = stats.get("resistencia", stats.get("hits_to_destroy", 1))
    try:
        resistencia_i = max(1, int(resistencia))
    except (TypeError, ValueError):
        resistencia_i = 1
    sprite = stats.get("sprite", "enemy.png")
    if not isinstance(sprite, str) or not sprite.strip():
        sprite = "enemy.png"
    sprite = sprite.strip()
    try:
        vel = float(stats.get("velocidade", 1.0))
    except (TypeError, ValueError):
        vel = 1.0
    vel = max(0.12, min(4.0, vel))
    ap = stats.get("comeca_apos_pontos", stats.get("comeca_apos_pontuacao", 0))
    try:
        desde = max(0, int(ap))
    except (TypeError, ValueError):
        desde = 0
    return {
        "id": str(eid),
        "sprite": sprite,
        "resistencia": resistencia_i,
        "velocidade": vel,
        "comeca_apos_pontos": desde,
    }


def _merge_enemies_config(base: dict[str, dict], patch: dict | None) -> dict[str, dict]:
    merged = {k: dict(v) for k, v in base.items()}
    if not isinstance(patch, dict):
        return {k: _normalize_enemy_entry(v, k) for k, v in merged.items()}
    for name, stats in patch.items():
        if not isinstance(stats, dict):
            continue
        prev = merged.get(name, {})
        combined = {**prev, **stats}
        merged[name] = _normalize_enemy_entry(combined, str(name))
    return merged if merged else {
        k: _normalize_enemy_entry(v, k) for k, v in DEFAULT_ENEMIES_MERGE.items()
    }


def load_game_config() -> dict:
    """Lê `game_config.json` junto a `main.py` ou, na raiz do projecto, `assets/game_config.json`."""
    base = Path(__file__).resolve().parent
    defaults: dict = {
        "player": {"hits_until_death": 1},
        "enemies": {
            k: _normalize_enemy_entry(v, k) for k, v in DEFAULT_ENEMIES_MERGE.items()
        },
        "characters": [dict(c) for c in DEFAULT_CHARACTERS],
        "spawn": {
            "intervalo_inicial_frames": 60,
            "intervalo_minimo_frames": 12,
            "velocidade_progressao": 1.0,
        },
        "escala_sprites": 1.15,
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
            defaults["enemies"] = _merge_enemies_config(defaults["enemies"], patch.get("enemies"))
            if isinstance(patch.get("spawn"), dict):
                defaults["spawn"].update(patch["spawn"])
            if "escala_sprites" in patch:
                try:
                    defaults["escala_sprites"] = float(patch["escala_sprites"])
                except (TypeError, ValueError):
                    pass
            defaults["characters"] = load_characters_from_config(patch)
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
            if _RUNS_IN_BROWSER_WASM:
                return pygame.transform.scale(surf, size)
            return pygame.transform.smoothscale(surf, size)
        except (FileNotFoundError, OSError, pygame.error, ValueError):
            continue
    return None


def _load_character_portrait(character: dict, size: tuple[int, int]) -> pygame.Surface:
    """Sprite do personagem (menu e jogo); fallback para player.png."""
    cid = str(character.get("id", ""))
    sprite_name = character.get("sprite") or f"player_{cid}.png"
    surf = _load_scaled_png(str(sprite_name), size)
    if surf is None:
        surf = _load_scaled_png("player.png", size)
    if surf is None:
        fb = pygame.Surface(size)
        fb.fill((255, 215, 0))
        return fb
    return surf


BLACK = (20, 20, 25)
WHITE = (255, 255, 255)
GOLD = (255, 215, 0)
RED_OFF = (90, 45, 50)
GREEN_ON = (40, 85, 55)

PLAYER_SIZE = (55, 55)
ENEMY_SIZE = (37, 37)
BULLET_SIZE = (14, 14)
PLAYER_FALLBACK = (37, 37)
ENEMY_FALLBACK = (28, 28)
BULLET_FALLBACK = (10, 10)
SPAWN_PAD = 23

BASE_PLAYER_MOVE_SPEED = 3.0
BASE_BULLET_SPEED = 7.0
BASE_ENEMY_MOVE_SPEED = 1.5


def apply_escala_sprites_from_config(cfg: dict) -> None:
    """Define tamanhos de sprite a partir de `escala_sprites` no config (ex.: 1.15)."""
    global PLAYER_SIZE, ENEMY_SIZE, BULLET_SIZE, PLAYER_FALLBACK, ENEMY_FALLBACK, BULLET_FALLBACK, SPAWN_PAD
    scale = float(cfg.get("escala_sprites", 1.15))
    scale = max(0.5, min(2.5, scale))
    PLAYER_SIZE = (int(round(48 * scale)), int(round(48 * scale)))
    ENEMY_SIZE = (int(round(32 * scale)), int(round(32 * scale)))
    BULLET_SIZE = (int(round(12 * scale)), int(round(12 * scale)))
    PLAYER_FALLBACK = (int(round(32 * scale)), int(round(32 * scale)))
    ENEMY_FALLBACK = (int(round(24 * scale)), int(round(24 * scale)))
    BULLET_FALLBACK = (int(round(8 * scale)), int(round(8 * scale)))
    SPAWN_PAD = int(round(20 * scale))


def pick_enemy_type_id(score: int, enemies_norm: dict[str, dict]) -> str:
    """Escolhe tipo de inimigo conforme pontuação e `comeca_apos_pontos` de cada um."""
    eligible = [eid for eid, e in enemies_norm.items() if score >= int(e.get("comeca_apos_pontos", 0))]
    if not eligible:
        return next(iter(enemies_norm.keys()))
    return random.choice(eligible)


class Player(pygame.sprite.Sprite):
    def __init__(self, character: dict) -> None:
        super().__init__()
        self.character = character
        self.image = _load_character_portrait(character, PLAYER_SIZE)

        self.rect = self.image.get_rect(center=(WIDTH // 2, HEIGHT // 2))
        self.pos = pygame.Vector2(self.rect.center)
        vel = float(character.get("velocidade", 1.0))
        self.speed = BASE_PLAYER_MOVE_SPEED * vel

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
    def __init__(
        self,
        _player_pos: pygame.Vector2,
        *,
        enemy_profile: dict,
        cam_offset: pygame.Vector2 | None = None,
    ) -> None:
        super().__init__()
        sprite_file = str(enemy_profile.get("sprite", "enemy.png"))
        self.image = _load_scaled_png(sprite_file, ENEMY_SIZE)
        if self.image is None:
            self.image = _load_scaled_png("enemy.png", ENEMY_SIZE)
        if self.image is None:
            self.image = pygame.Surface(ENEMY_FALLBACK)
            self.image.fill((200, 0, 0))

        self.hits_to_destroy = max(1, int(enemy_profile.get("resistencia", 1)))
        self.hits_left = self.hits_to_destroy

        # Spawnar fora do viewport actual da câmara, em coordenadas de mundo.
        cx = cam_offset.x if cam_offset is not None else 0.0
        cy = cam_offset.y if cam_offset is not None else 0.0
        left, top = cx, cy
        right, bottom = cx + WIDTH, cy + HEIGHT

        side = random.choice(["t", "b", "l", "r"])
        if side == "t":
            self.pos = pygame.Vector2(random.uniform(left, right), top - SPAWN_PAD)
        elif side == "b":
            self.pos = pygame.Vector2(random.uniform(left, right), bottom + SPAWN_PAD)
        elif side == "l":
            self.pos = pygame.Vector2(left - SPAWN_PAD, random.uniform(top, bottom))
        else:
            self.pos = pygame.Vector2(right + SPAWN_PAD, random.uniform(top, bottom))

        self.rect = self.image.get_rect(center=(int(self.pos.x), int(self.pos.y)))
        vel = float(enemy_profile.get("velocidade", 1.0))
        self.speed = BASE_ENEMY_MOVE_SPEED * vel

    def take_bullet_hit(self, damage: float) -> bool:
        """Devolve True se o inimigo morreu (tiros esgotados)."""
        self.hits_left -= max(1, int(round(damage)))
        return self.hits_left <= 0

    def update(self, player_pos: pygame.Vector2) -> None:
        diff = pygame.Vector2(player_pos) - self.pos
        if diff.length_squared() < 1e-6:
            return
        direction = diff.normalize()
        self.pos += direction * self.speed
        self.rect.center = (int(self.pos.x), int(self.pos.y))


class Bullet(pygame.sprite.Sprite):
    def __init__(
        self,
        start_pos: pygame.Vector2,
        target_pos: pygame.Vector2,
        *,
        bullet_speed_mult: float = 1.0,
        damage: float = 1.0,
    ) -> None:
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
        self.speed = BASE_BULLET_SPEED * float(bullet_speed_mult)
        self.damage = float(damage)
        # Sem limite de tela: a bala morre depois de percorrer uma distância máxima.
        self.distance_left = float(max(WIDTH, HEIGHT)) * 1.2

    def update(self) -> None:
        step = self.dir * self.speed
        self.pos += step
        self.rect.center = (int(self.pos.x), int(self.pos.y))
        self.distance_left -= self.speed
        if self.distance_left <= 0:
            self.kill()


_SCROLL_TILE_MAIN: pygame.Surface | None = None
_SCROLL_TILE_FAR: pygame.Surface | None = None
_SCROLL_BG_USE_GRID_FALLBACK = False

_WORLD_GRID_FALLBACK = 64
_WORLD_GRID_COLOR = (34, 38, 48)
_WORLD_GRID_ACCENT = (48, 54, 70)


def _draw_world_background_grid(surface: pygame.Surface, cam_offset: pygame.Vector2) -> None:
    """Fundo a grelha (fallback se texturas RGB falharem no browser)."""
    surface.fill(BLACK)
    gs = _WORLD_GRID_FALLBACK
    start_x = -int(cam_offset.x) % gs
    start_y = -int(cam_offset.y) % gs
    for x in range(start_x - gs, WIDTH + gs, gs):
        col = _WORLD_GRID_ACCENT if ((x + int(cam_offset.x)) // gs) % 4 == 0 else _WORLD_GRID_COLOR
        pygame.draw.line(surface, col, (x, 0), (x, HEIGHT))
    for y in range(start_y - gs, HEIGHT + gs, gs):
        col = _WORLD_GRID_ACCENT if ((y + int(cam_offset.y)) // gs) % 4 == 0 else _WORLD_GRID_COLOR
        pygame.draw.line(surface, col, (0, y), (WIDTH, y))


def _surface_from_rgb_buffer(size: int, rgb: bytearray) -> pygame.Surface:
    """Uma cópia para textura — evita `set_at` por pixel (muito lento em pygbag/mobile)."""
    surf = pygame.image.frombytes(bytes(rgb), (size, size), "RGB")
    return surf.convert()


def _make_scroll_tile_far(size: int) -> pygame.Surface:
    """Textura repetível (céu / nébula distante) com período size em x e y."""
    buf = bytearray(size * size * 3)
    i = 0
    for y in range(size):
        for x in range(size):
            nx = 2 * math.pi * x / size
            ny = 2 * math.pi * y / size
            v = (
                0.34 * math.sin(nx * 1.4) * math.cos(ny * 1.1)
                + 0.28 * math.sin(nx * 2.8 + ny * 2.0)
                + 0.22 * math.sin(nx * 2.1 - ny * 2.9)
            )
            r = 9 + int(12 * v)
            g = 11 + int(14 * v)
            b = 24 + int(22 * v)
            sp = math.sin(x * 1.731 + y * 2.437)
            if sp > 0.91:
                r = min(255, r + 48)
                g = min(255, g + 52)
                b = min(255, b + 62)
            buf[i] = max(0, r)
            buf[i + 1] = max(0, g)
            buf[i + 2] = min(255, b)
            i += 3
    return _surface_from_rgb_buffer(size, buf)


def _make_scroll_tile_main(size: int) -> pygame.Surface:
    """Chão / arena repetível com variação tipo pedra e grelha subtil alinhada ao tile."""
    buf = bytearray(size * size * 3)
    i = 0
    for y in range(size):
        for x in range(size):
            nx = 2 * math.pi * x / size
            ny = 2 * math.pi * y / size
            stone = (
                0.3 * math.sin(nx * 2) * math.cos(ny * 2)
                + 0.22 * math.sin(nx * 4 + ny * 3)
                + 0.2 * math.sin(nx * 6) * math.sin(ny * 2)
                + 0.16 * math.sin((nx + ny) * 5)
            )
            r = 24 + int(26 * stone)
            g = 28 + int(28 * stone)
            b = 42 + int(40 * stone)
            buf[i] = max(0, min(255, r))
            buf[i + 1] = max(0, min(255, g))
            buf[i + 2] = max(0, min(255, b))
            i += 3
    surf = _surface_from_rgb_buffer(size, buf)
    gs = 44
    if size % gs == 0:
        line_c = (18, 22, 34)
        for x in range(0, size + 1, gs):
            pygame.draw.line(surf, line_c, (x, 0), (x, size), 1)
        for y in range(0, size + 1, gs):
            pygame.draw.line(surf, line_c, (0, y), (size, y), 1)
    return surf


def _scroll_background_tiles() -> tuple[pygame.Surface | None, pygame.Surface | None]:
    global _SCROLL_TILE_MAIN, _SCROLL_TILE_FAR, _SCROLL_BG_USE_GRID_FALLBACK
    if _SCROLL_BG_USE_GRID_FALLBACK:
        return None, None
    if _SCROLL_TILE_MAIN is None:
        try:
            _SCROLL_TILE_MAIN = _make_scroll_tile_main(176)
            _SCROLL_TILE_FAR = _make_scroll_tile_far(192)
        except (pygame.error, ValueError, TypeError, MemoryError, RuntimeError):
            _SCROLL_BG_USE_GRID_FALLBACK = True
            _SCROLL_TILE_MAIN = None
            _SCROLL_TILE_FAR = None
    return _SCROLL_TILE_MAIN, _SCROLL_TILE_FAR


def _blit_tiled_scroll(
    surface: pygame.Surface,
    tile: pygame.Surface,
    cam_offset: pygame.Vector2,
    parallax: float,
) -> None:
    """Repete `tile` no ecrã; deslocamento derivado de `cam_offset` com factor de parallax."""
    tw, th = tile.get_size()
    ox = float(cam_offset.x) * parallax
    oy = float(cam_offset.y) * parallax
    start_x = (-int(ox)) % tw
    start_y = (-int(oy)) % th
    for x in range(start_x - tw, WIDTH + tw, tw):
        for y in range(start_y - th, HEIGHT + th, th):
            surface.blit(tile, (x, y))


def _draw_world_background_wasm(surface: pygame.Surface, cam_offset: pygame.Vector2) -> None:
    """Fundo com scroll e poucos draw.rect (evita dezenas de draw.line por frame no canvas WASM)."""
    surface.fill(BLACK)
    bw = 40
    start_x = (-int(cam_offset.x)) % (bw * 2)
    for x in range(start_x - bw * 2, WIDTH + bw * 2, bw):
        i = (x + int(cam_offset.x)) // bw
        c = (32, 36, 48) if i % 2 == 0 else (22, 26, 36)
        pygame.draw.rect(surface, c, (x, 0, bw, HEIGHT))
    band_h = 10
    start_y = (-int(cam_offset.y)) % (band_h * 2)
    for y in range(start_y - band_h * 2, HEIGHT + band_h * 2, band_h):
        j = (y + int(cam_offset.y)) // band_h
        if j % 2 == 1:
            pygame.draw.rect(surface, (18, 22, 30), (0, y, WIDTH, band_h))


def draw_world_background(surface: pygame.Surface, cam_offset: pygame.Vector2) -> None:
    """Fundo infinito com scroll. No browser: rectas leves + update(); no desktop: tiles RGB."""
    if _RUNS_IN_BROWSER_WASM:
        _draw_world_background_wasm(surface, cam_offset)
        return
    main_tile, far_tile = _scroll_background_tiles()
    if main_tile is None or far_tile is None:
        _draw_world_background_grid(surface, cam_offset)
        return
    try:
        _blit_tiled_scroll(surface, far_tile, cam_offset, 0.24)
        _blit_tiled_scroll(surface, main_tile, cam_offset, 1.0)
    except (pygame.error, TypeError, ValueError):
        global _SCROLL_BG_USE_GRID_FALLBACK, _SCROLL_TILE_MAIN, _SCROLL_TILE_FAR
        _SCROLL_BG_USE_GRID_FALLBACK = True
        _SCROLL_TILE_MAIN = None
        _SCROLL_TILE_FAR = None
        _draw_world_background_grid(surface, cam_offset)


def draw_sprites_with_camera(
    surface: pygame.Surface,
    sprites: pygame.sprite.Group,
    cam_offset: pygame.Vector2,
) -> None:
    """Desenha sprites convertendo as suas posições de mundo para coordenadas de ecrã."""
    ox, oy = int(cam_offset.x), int(cam_offset.y)
    for sprite in sprites:
        surface.blit(sprite.image, (sprite.rect.x - ox, sprite.rect.y - oy))


def _shoot_toggle_rect() -> pygame.Rect:
    return pygame.Rect(WIDTH - 136, 6, 126, 38)


def _character_select_layout(chars: list[dict]) -> list[tuple[pygame.Rect, dict]]:
    top = 48
    gap = 6
    margin_x = 10
    w = WIDTH - 2 * margin_x
    n = max(1, len(chars))
    avail = HEIGHT - top - 14
    slot_h = max(52, (avail - (n - 1) * gap) // n)
    out: list[tuple[pygame.Rect, dict]] = []
    y = top
    for c in chars:
        out.append((pygame.Rect(margin_x, y, w, slot_h), c))
        y += slot_h + gap
    return out


async def main() -> None:
    snd_hit, snd_hurt, snd_bg = load_procedural_sounds()
    cfg = load_game_config()
    apply_escala_sprites_from_config(cfg)
    enemies_cfg: dict[str, dict] = cfg["enemies"]
    characters: list[dict] = cfg["characters"]
    spawn_cfg = cfg["spawn"] if isinstance(cfg.get("spawn"), dict) else {}
    spawn_initial = max(8, int(spawn_cfg.get("intervalo_inicial_frames", 60)))
    spawn_min = int(spawn_cfg.get("intervalo_minimo_frames", 12))
    spawn_min = max(4, min(spawn_min, spawn_initial - 1))
    spawn_vel_prog = float(spawn_cfg.get("velocidade_progressao", 1.0))
    spawn_vel_prog = max(0.25, min(4.0, spawn_vel_prog))
    SPAWN_INTERVAL_SHRINK_BASE = 0.988

    game_phase = "select"
    selected_character: dict | None = None
    player_max_hp = 1

    player: Player | None = None
    all_sprites = pygame.sprite.Group()
    enemies = pygame.sprite.Group()
    bullets = pygame.sprite.Group()

    target_move_pos: tuple[float, float] | None = None
    spawn_timer = 0
    spawn_interval_frames = spawn_initial
    shoot_timer = 0
    score = 0
    player_hp = 1
    game_over = False
    shooting_enabled = True
    font = pygame.font.SysFont(None, 32)
    font_btn = pygame.font.SysFont(None, 22)
    font_death = pygame.font.SysFont(None, 44)
    font_sel_title = pygame.font.SysFont(None, 30)
    font_sel_name = pygame.font.SysFont(None, 24)
    font_sel_sub = pygame.font.SysFont(None, 20)
    font_sel_stats = pygame.font.SysFont(None, 17)
    shoot_btn = _shoot_toggle_rect()

    _sel_layout_preview = _character_select_layout(characters)
    _thumb_side = (
        max(40, min(58, _sel_layout_preview[0][0].height - 10))
        if _sel_layout_preview
        else 56
    )
    select_portraits: dict[str, pygame.Surface] = {
        str(ch["id"]): _load_character_portrait(ch, (_thumb_side, _thumb_side)) for ch in characters
    }

    # Texturas de fundo (só desktop); no browser a grelha é gerada em draw_world_background.
    await asyncio.sleep(0)
    if not _RUNS_IN_BROWSER_WASM:
        _scroll_background_tiles()

    CARD_BG = (38, 42, 52)
    CARD_LINE = (72, 78, 92)
    CARD_HOVER = (52, 62, 82)

    def begin_play(character: dict) -> None:
        nonlocal game_phase, selected_character, player_max_hp, player, all_sprites
        nonlocal enemies, bullets, target_move_pos, spawn_timer, spawn_interval_frames, shoot_timer
        nonlocal score, player_hp, game_over, shooting_enabled
        selected_character = character
        player_max_hp = max(1, int(character.get("resistencia", 1)))
        player = Player(character)
        all_sprites = pygame.sprite.Group(player)
        enemies = pygame.sprite.Group()
        bullets = pygame.sprite.Group()
        target_move_pos = None
        spawn_timer = 0
        spawn_interval_frames = spawn_initial
        shoot_timer = 0
        score = 0
        player_hp = player_max_hp
        game_over = False
        shooting_enabled = True
        game_phase = "playing"
        if snd_bg is not None and snd_bg.get_num_channels() == 0:
            try:
                snd_bg.play(loops=-1)
            except pygame.error:
                pass

    def reset_run() -> None:
        nonlocal player, all_sprites, enemies, bullets, target_move_pos
        nonlocal spawn_timer, spawn_interval_frames, shoot_timer, score, player_hp, game_over
        if selected_character is None:
            return
        player = Player(selected_character)
        all_sprites = pygame.sprite.Group(player)
        enemies = pygame.sprite.Group()
        bullets = pygame.sprite.Group()
        target_move_pos = None
        spawn_timer = 0
        spawn_interval_frames = spawn_initial
        shoot_timer = 0
        score = 0
        player_hp = player_max_hp
        game_over = False

    def _pick_character_screen_pos(pos: tuple[float, float]) -> dict | None:
        for rect, ch in _character_select_layout(characters):
            if rect.collidepoint(pos):
                return ch
        return None

    cam_offset = pygame.Vector2(0, 0)

    def screen_to_world(p: tuple[float, float]) -> tuple[float, float]:
        return (p[0] + cam_offset.x, p[1] + cam_offset.y)

    running = True
    while running:
        # A câmara é recalculada a cada frame: o jogador fica sempre no centro do ecrã.
        if player is not None:
            cam_offset.x = player.pos.x - WIDTH / 2
            cam_offset.y = player.pos.y - HEIGHT / 2

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                continue

            if game_phase == "select":
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    ch = _pick_character_screen_pos(event.pos)
                    if ch is not None:
                        begin_play(ch)
                elif event.type == pygame.FINGERDOWN:
                    fx, fy = event.x * WIDTH, event.y * HEIGHT
                    ch = _pick_character_screen_pos((fx, fy))
                    if ch is not None:
                        begin_play(ch)
                continue

            assert player is not None

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
                    target_move_pos = screen_to_world(event.pos)

            if event.type == pygame.MOUSEMOTION and pygame.mouse.get_pressed()[0]:
                if not shoot_btn.collidepoint(event.pos):
                    target_move_pos = screen_to_world(event.pos)

            if event.type == pygame.FINGERDOWN:
                fx, fy = event.x * WIDTH, event.y * HEIGHT
                if shoot_btn.collidepoint(fx, fy):
                    shooting_enabled = not shooting_enabled
                else:
                    target_move_pos = screen_to_world((fx, fy))
            if event.type == pygame.FINGERMOTION:
                target_move_pos = screen_to_world((event.x * WIDTH, event.y * HEIGHT))

        if game_phase == "playing" and not game_over and player is not None:
            player.move(target_move_pos)
            # Re-sincroniza a câmara após o movimento deste frame para spawnar
            # inimigos relativos ao viewport actual.
            cam_offset.x = player.pos.x - WIDTH / 2
            cam_offset.y = player.pos.y - HEIGHT / 2

            spawn_timer += 1
            if spawn_timer > spawn_interval_frames:
                eid = pick_enemy_type_id(score, enemies_cfg)
                profile = enemies_cfg[eid]
                enemy = Enemy(player.pos, enemy_profile=profile, cam_offset=cam_offset)
                enemies.add(enemy)
                all_sprites.add(enemy)
                spawn_timer = 0
                spawn_interval_frames = max(
                    spawn_min,
                    int(spawn_interval_frames * (SPAWN_INTERVAL_SHRINK_BASE**spawn_vel_prog)),
                )

            shoot_timer += 1
            if shooting_enabled and shoot_timer > 40 and enemies:
                closest = min(
                    enemies,
                    key=lambda e: pygame.Vector2(e.pos).distance_to(player.pos),
                )
                ch = selected_character or {}
                bullet = Bullet(
                    player.pos,
                    closest.pos,
                    bullet_speed_mult=float(ch.get("velocidade_tiro", 1.0)),
                    damage=float(ch.get("forca", 1.0)),
                )
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
                if snd_hit is not None:
                    try:
                        snd_hit.play()
                    except pygame.error:
                        pass
                enemy = struck[0]
                if enemy.take_bullet_hit(bullet.damage):
                    enemy.kill()
                    score += 1

            if pygame.sprite.spritecollide(player, enemies, False):
                player_hp -= 1
                if snd_hurt is not None:
                    try:
                        snd_hurt.play()
                    except pygame.error:
                        pass
                for e in enemies:
                    e.kill()
                for b in list(bullets):
                    b.kill()
                if player_hp <= 0:
                    game_over = True

        if game_phase == "select":
            screen.fill(BLACK)
            title = font_sel_title.render("Escolha o personagem", True, WHITE)
            screen.blit(title, title.get_rect(midtop=(WIDTH // 2, 8)))
            hint_sel = font_sel_stats.render("Toque num cartão para jogar", True, (170, 175, 190))
            screen.blit(hint_sel, hint_sel.get_rect(midtop=(WIDTH // 2, 36)))
            mx, my = pygame.mouse.get_pos()
            for rect, ch in _character_select_layout(characters):
                hover = rect.collidepoint(mx, my)
                bg = CARD_HOVER if hover else CARD_BG
                pygame.draw.rect(screen, bg, rect, border_radius=10)
                pygame.draw.rect(screen, CARD_LINE, rect, 1, border_radius=10)
                portrait = select_portraits.get(str(ch["id"]))
                pad = 8
                text_x = rect.x + pad
                if portrait is not None:
                    px = rect.x + pad
                    py = rect.y + (rect.height - portrait.get_height()) // 2
                    screen.blit(portrait, (px, py))
                    text_x = px + portrait.get_width() + 8
                name_s = font_sel_name.render(ch["name"], True, WHITE)
                screen.blit(name_s, (text_x, rect.y + 8))
                sub = font_sel_sub.render(ch.get("title", ""), True, (190, 195, 210))
                screen.blit(sub, (text_x, rect.y + 30))
                f, r, v, vt = (
                    ch.get("forca", 1),
                    ch.get("resistencia", 1),
                    ch.get("velocidade", 1),
                    ch.get("velocidade_tiro", 1),
                )
                stats = font_sel_stats.render(
                    f"Força {f}  ·  Res {r}  ·  Vel {v}  ·  Tiro {vt}",
                    True,
                    (200, 205, 220),
                )
                screen.blit(stats, (text_x, rect.bottom - 26))
        else:
            draw_world_background(screen, cam_offset)
            draw_sprites_with_camera(screen, all_sprites, cam_offset)

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

        if _RUNS_IN_BROWSER_WASM:
            clock.tick(0)
        else:
            clock.tick(60)
        _present_display()
        await asyncio.sleep(0)


asyncio.run(main())
