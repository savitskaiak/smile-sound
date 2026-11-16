import math
import os
import random
import sys

import pygame

pygame.init()

# 1. Окно
WIDTH, HEIGHT = 800, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Смайлик на pygame")
clock = pygame.time.Clock()
font = pygame.font.SysFont(None, 22)
big_font = pygame.font.SysFont(None, 44)
huge_font = pygame.font.SysFont(None, 80)

BASE = os.path.dirname(os.path.abspath(__file__))
IMG = os.path.join(BASE, "images")
SND = os.path.join(BASE, "sounds")

# ---------------------------------------------------------------- ЗВУК
# Если звуковой карты нет, игра всё равно работает - просто без звука.
try:
    pygame.mixer.init()
except pygame.error:
    pass
SOUND_OK = pygame.mixer.get_init() is not None

# Событие -> базовая громкость (потом умножается на общую громкость).
# Файл звука берётся из папки sounds по имени события: shoot.ogg, pop.ogg ...
BASE_VOL = {
    "music": 0.4,      # фоновая музыка
    "start": 0.7,      # начало игры
    "shoot": 0.6,      # выстрел
    "pop": 0.8,        # попали во врага
    "pickup": 0.8,     # коснулись друга
    "hurt": 0.8,       # враг ударил нас
    "levelup": 0.8,    # каждые 10 очков
    "gameover": 0.8,   # жизни кончились
    "win": 0.8,        # победа (30 очков)
}
sounds = {}
if SOUND_OK:
    for name in BASE_VOL:
        for ext in (".ogg", ".wav"):          # ищем файл: сначала ogg, потом wav
            try:
                sounds[name] = pygame.mixer.Sound(os.path.join(SND, name + ext))
                break
            except Exception:
                pass  # нет такого файла - пробуем следующий формат

volume = 0.5   # общая громкость от 0.0 до 1.0
muted = False


def apply_volume():
    v = 0 if muted else volume
    for name, s in sounds.items():
        s.set_volume(BASE_VOL[name] * v)


def play(name):
    if name in sounds:
        sounds[name].play()


apply_volume()


# ------------------------------------------------------------ КАРТИНКИ
SCALE = 0.75  # картинки в файлах 160x160, уменьшаем до 120x120


def load(name, factor=SCALE):
    """Картинка с прозрачным фоном (convert_alpha), плавно изменённая по размеру."""
    img = pygame.image.load(os.path.join(IMG, name)).convert_alpha()
    w, h = img.get_size()
    return pygame.transform.smoothscale(img, (int(w * factor), int(h * factor)))


def make_box(size, cx, cy):
    r = pygame.Rect(0, 0, size[0], size[1])
    r.center = (int(cx), int(cy))
    return r


# Персонаж собирается из частей: тело + лицо + две руки + тень.
COLORS = ["blue", "green", "pink", "purple", "red", "yellow"]
SHAPES = ["circle", "rhombus", "square", "squircle"]
FACES = "abcdefghijkl"
ANGRY = [4, 5, 6]    # лица e, f, g - злые (у врагов)
HAPPY = [0, 11]      # лица a, l - добрые (у друзей)
DEAD = 9             # лицо j - глаза-крестики (после удара)


def hand_name(color, kind):
    # у жёлтого цвета файл называется иначе: hand_yellow_open.png
    if color == "yellow":
        return f"hand_yellow_{kind}.png"
    return f"{color}_hand_{kind}.png"


bodies = {(c, s): load(f"{c}_body_{s}.png") for c in COLORS for s in SHAPES}
hands_open = {c: load(hand_name(c, "open")) for c in COLORS}
hands_closed = {c: load(hand_name(c, "closed")) for c in COLORS}
faces = [load(f"face_{f}.png") for f in FACES]
shadow = load("shadow.png")

BW, BH = bodies[("blue", "circle")].get_size()
HAND_W = max(h.get_width() for h in hands_open.values())
MARGIN_X = BW // 2 + HAND_W + 6      # чтобы руки не выходили за окно
PSIZE = (90, 90)                      # хитбокс игрока (чуть меньше тела - честнее)

# Снаряд - маленький круглый шарик цвета персонажа
BALL = 30
BULLET_BOX = (24, 24)
balls = {c: pygame.transform.smoothscale(bodies[(c, "circle")], (BALL, BALL)) for c in COLORS}

# Иконка жизни: маленький смайлик
ICON = 40


def make_icon(color):
    icon = pygame.Surface((ICON, ICON), pygame.SRCALPHA)
    icon.blit(pygame.transform.smoothscale(bodies[(color, "circle")], (ICON, ICON)), (0, 0))
    f = faces[0]
    f = pygame.transform.smoothscale(f, (f.get_width() * ICON // BW, f.get_height() * ICON // BW))
    icon.blit(f, f.get_rect(center=(ICON // 2, ICON // 2 + 1)))
    return icon


life_icons = {c: make_icon(c) for c in COLORS}

# Блоки - препятствия (через них нельзя пройти, шарики в них врезаются)
tile = load("tile_grey.png", 0.5)
TILE = tile.get_width()
blocks = [make_box((TILE, TILE), 170, 230), make_box((TILE, TILE), 630, 370),
          make_box((TILE, TILE), 400, 480)]


def hits_block(box):
    return any(box.colliderect(b) for b in blocks)


# ------------------------------------------ ВРАГИ И ДРУЗЬЯ (случайные)
ENEMY = 64
ENEMY_BOX = (50, 50)
FRIEND_BOX = (54, 54)


def make_sprite(kind):
    """Враг: случайное тело + злое лицо. Друг: жёлтый круг + весёлое лицо."""
    if kind == "enemy":
        color = random.choice([c for c in COLORS if c != "yellow"])
        body = bodies[(color, random.choice(SHAPES))]
        face = faces[random.choice(ANGRY)]
    else:
        body = bodies[("yellow", "circle")]
        face = faces[random.choice(HAPPY)]
    body = pygame.transform.smoothscale(body, (ENEMY, ENEMY))
    face = pygame.transform.smoothscale(face, (face.get_width() // 2, face.get_height() // 2))
    sprite = pygame.Surface((ENEMY, ENEMY), pygame.SRCALPHA)
    sprite.blit(body, (0, 0))
    sprite.blit(face, face.get_rect(center=(ENEMY // 2, ENEMY // 2 + 3)))
    return sprite


def new_direction(e):
    lo, hi = e["sp"]
    angle = random.uniform(0, 2 * math.pi)
    sp = random.uniform(lo, hi)
    e["vx"] = math.cos(angle) * sp
    e["vy"] = math.sin(angle) * sp
    e["timer"] = random.randint(40, 120)  # через сколько кадров снова сменить курс


def spawn(kind, avoid):
    """kind: 'enemy' - злой смайлик, 'friend' - добрый."""
    size = ENEMY_BOX if kind == "enemy" else FRIEND_BOX
    while True:
        ex = random.randint(60, WIDTH - 60)
        ey = random.randint(60, HEIGHT - 60)
        # не появляемся на игроке и не внутри блока
        if math.hypot(ex - avoid[0], ey - avoid[1]) > 200 and not hits_block(make_box(size, ex, ey)):
            break
    e = {
        "kind": kind, "x": ex, "y": ey, "vx": 0, "vy": 0, "timer": 0,
        "base": make_sprite(kind),
        "rot": random.uniform(0, 360),
        # враги вращаются, друзья - нет (чтобы лицо было видно)
        "spin": random.choice([-1, 1]) * random.uniform(1, 4) if kind == "enemy" else 0,
        "sp": (1.5, 3.5) if kind == "enemy" else (0.8, 1.8),
        "phase": random.uniform(0, 6.28),
    }
    new_direction(e)
    return e


def e_box(e):
    return make_box(ENEMY_BOX if e["kind"] == "enemy" else FRIEND_BOX, e["x"], e["y"])


def move_swimmer(e):
    """Хаотичное движение: смена курса, виляние, отскок от краёв и блоков."""
    e["timer"] -= 1
    if e["timer"] <= 0:
        new_direction(e)
    e["vy"] += random.uniform(-0.3, 0.3)
    e["vy"] = max(-3.5, min(3.5, e["vy"]))
    old = (e["x"], e["y"])
    e["x"] += e["vx"]
    e["y"] += e["vy"]
    e["rot"] += e["spin"]
    box = e_box(e)
    if box.left < 0:
        e["x"] -= box.left
        e["vx"] = abs(e["vx"])
    if box.right > WIDTH:
        e["x"] -= box.right - WIDTH
        e["vx"] = -abs(e["vx"])
    if box.top < 0:
        e["y"] -= box.top
        e["vy"] = abs(e["vy"])
    if box.bottom > HEIGHT:
        e["y"] -= box.bottom - HEIGHT
        e["vy"] = -abs(e["vy"])
    if hits_block(e_box(e)):
        e["x"], e["y"] = old          # врезались в блок - возвращаемся и летим назад
        e["vx"] = -e["vx"]
        e["vy"] = -e["vy"]


# ---------------------------------------------------- СОСТОЯНИЕ ИГРЫ
WIN_SCORE = 30
color_i, shape_i, face_i = 0, 0, 0
speed = 5
state = "playing"   # "playing", "gameover" или "win"


def reset_game():
    global x, y, shoot_dir, look, t, score, lives, invuln, next_bonus
    global shoot_cooldown, bullets, enemies, friends, state
    x, y = WIDTH / 2, HEIGHT / 2
    shoot_dir = 1          # куда стрелять: 1 вправо, -1 влево
    look = 0.0             # куда смотрит лицо: -1 влево ... +1 вправо
    t = 0.0
    score = 0
    lives = 3
    invuln = 0             # сколько кадров неуязвим после удара
    next_bonus = 10        # при каком счёте играет звук "levelup"
    shoot_cooldown = 0
    bullets = []
    enemies = [spawn("enemy", (x, y)) for _ in range(5)]
    friends = [spawn("friend", (x, y)) for _ in range(2)]
    state = "playing"
    if "music" in sounds:
        sounds["music"].stop()
        sounds["music"].play(loops=-1)   # музыка играет по кругу
    play("start")


reset_game()

running = True
while running:
    # ------------------------------------------------------ СОБЫТИЯ
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                running = False
            if event.key == pygame.K_c:       # C - цвет
                color_i = (color_i + 1) % len(COLORS)
            if event.key == pygame.K_z:       # Z - форма тела
                shape_i = (shape_i + 1) % len(SHAPES)
            if event.key == pygame.K_f:       # F - лицо
                face_i = (face_i + 1) % len(faces)
            if event.key == pygame.K_r:       # R - начать заново
                reset_game()
            # --- ГРОМКОСТЬ ---
            if event.key in (pygame.K_MINUS, pygame.K_KP_MINUS):
                volume = max(0.0, round(volume - 0.1, 1))
                muted = False
                apply_volume()
            if event.key in (pygame.K_EQUALS, pygame.K_PLUS, pygame.K_KP_PLUS):
                volume = min(1.0, round(volume + 0.1, 1))
                muted = False
                apply_volume()
            if event.key == pygame.K_m:       # M - выключить/включить звук
                muted = not muted
                apply_volume()

    keys = pygame.key.get_pressed()
    color = COLORS[color_i]
    moving = False

    # ------------------------------------------------------ ОБНОВЛЕНИЕ
    if state == "playing":
        dx = (keys[pygame.K_RIGHT] or keys[pygame.K_d]) - (keys[pygame.K_LEFT] or keys[pygame.K_a])
        dy = (keys[pygame.K_DOWN] or keys[pygame.K_s]) - (keys[pygame.K_UP] or keys[pygame.K_w])

        moving = bool(dx or dy)
        if moving:
            length = math.hypot(dx, dy)
            step_x = dx / length * speed
            step_y = dy / length * speed
            # двигаемся по осям отдельно, чтобы скользить вдоль блока, а не застревать
            x += step_x
            if hits_block(make_box(PSIZE, x, y)):
                x -= step_x
            y += step_y
            if hits_block(make_box(PSIZE, x, y)):
                y -= step_y
            t += 0.3
            if dx:
                shoot_dir = 1 if dx > 0 else -1
        else:
            t += 0.08
        look += (dx - look) * 0.2  # плавный поворот лица

        # --- ОГРАНИЧЕНИЕ ПО РАМКЕ ЭКРАНА ---
        # персонаж вместе с руками и подпрыгиванием не выходит за окно
        x = max(MARGIN_X, min(WIDTH - MARGIN_X, x))
        y = max(BH // 2 + 12, min(HEIGHT - BH // 2 - 14, y))
        pbox = make_box(PSIZE, x, y)

        # --- СТРЕЛЬБА ПО ПРОБЕЛУ ---
        if shoot_cooldown > 0:
            shoot_cooldown -= 1
        if keys[pygame.K_SPACE] and shoot_cooldown == 0:
            start_x = x + shoot_dir * (PSIZE[0] // 2 + 10)
            bullets.append({"x": start_x, "y": y + 8, "vx": 12 * shoot_dir, "color": color})
            shoot_cooldown = 15  # не чаще 4 выстрелов в секунду
            play("shoot")

        # --- ШАРИКИ: движение, столкновение с блоками ---
        for b in bullets:
            b["x"] += b["vx"]
        bullets = [
            b for b in bullets
            if -40 < b["x"] < WIDTH + 40
            and not hits_block(make_box(BULLET_BOX, b["x"], b["y"]))
        ]

        # --- ВРАГИ И ДРУЗЬЯ ДВИЖУТСЯ ХАОТИЧНО ---
        for e in enemies + friends:
            move_swimmer(e)

        # --- ПОПАДАНИЯ ШАРИКОВ ---
        alive_bullets = []
        for b in bullets:
            bbox = make_box(BULLET_BOX, b["x"], b["y"])
            hit = False
            for k, e in enumerate(enemies):
                if bbox.colliderect(e_box(e)):
                    score += 1
                    play("pop")
                    enemies[k] = spawn("enemy", (x, y))  # подбитый появляется заново
                    hit = True
                    break
            if not hit:
                for k, f in enumerate(friends):
                    if bbox.colliderect(e_box(f)):
                        score = max(0, score - 2)        # в друга стрелять нельзя!
                        play("hurt")
                        friends[k] = spawn("friend", (x, y))
                        hit = True
                        break
            if not hit:
                alive_bullets.append(b)
        bullets = alive_bullets

        # --- СТОЛКНОВЕНИЯ ИГРОКА ---
        if invuln > 0:
            invuln -= 1
        for k, e in enumerate(enemies):
            if invuln == 0 and pbox.colliderect(e_box(e)):
                lives -= 1
                invuln = 120                              # 2 секунды неуязвимости
                play("hurt")
                enemies[k] = spawn("enemy", (x, y))
                if lives <= 0:
                    state = "gameover"
                    if "music" in sounds:
                        sounds["music"].stop()
                    play("gameover")
                break
        for k, f in enumerate(friends):
            if state == "playing" and pbox.colliderect(e_box(f)):
                score += 5                                # подружились
                play("pickup")
                friends[k] = spawn("friend", (x, y))

        # --- ПОБЕДА И БОНУСЫ ---
        if state == "playing":
            if score >= WIN_SCORE:
                state = "win"
                if "music" in sounds:
                    sounds["music"].stop()
                play("win")
            elif score >= next_bonus:
                play("levelup")
                while next_bonus <= score:
                    next_bonus += 10

    # ------------------------------------------------------ РИСУЕМ
    screen.fill((228, 233, 240))

    for b in blocks:
        screen.blit(tile, b.topleft)

    for f in friends:                                     # друзья слегка подпрыгивают
        spr = f["base"]
        bounce = math.sin(t * 0.6 + f["phase"]) * 4
        screen.blit(spr, spr.get_rect(center=(f["x"], f["y"] + bounce)))
    for e in enemies:                                     # враги крутятся
        spr = pygame.transform.rotate(e["base"], e["rot"])
        screen.blit(spr, spr.get_rect(center=(e["x"], e["y"])))
    for b in bullets:
        ball = balls[b["color"]]
        screen.blit(ball, ball.get_rect(center=(b["x"], b["y"])))

    # игрок (мигает, пока неуязвим; после удара - глаза-крестики)
    if not (state == "playing" and invuln > 0 and (invuln // 6) % 2 == 0):
        shape = SHAPES[shape_i]
        body = bodies[(color, shape)]
        face = faces[DEAD] if (invuln > 0 or state == "gameover") else faces[face_i]
        hand = hands_closed[color] if moving else hands_open[color]
        hand_l = pygame.transform.flip(hand, True, False)  # левая рука - зеркало правой

        bob = abs(math.sin(t)) * (-10 if moving else -3)     # подпрыгивание
        sway = math.sin(t) * (10 if moving else 3)           # качание рук
        cx, cy = int(x), int(y + bob)

        ground_y = int(y) + BH // 2 - 4                      # тень остаётся на земле
        screen.blit(shadow, shadow.get_rect(center=(cx, ground_y)))
        screen.blit(body, body.get_rect(center=(cx, cy)))
        screen.blit(face, face.get_rect(center=(cx + look * 6, cy + 3)))
        hy = cy + 8
        screen.blit(hand, hand.get_rect(midright=(cx - BW // 2 + 4, hy + sway)).move(-4, 0))
        screen.blit(hand_l, hand_l.get_rect(midleft=(cx + BW // 2 - 4, hy - sway)).move(4, 0))

    # --- ИНТЕРФЕЙС ---
    dark = (60, 70, 90)
    screen.blit(font.render(
        "Стрелки/WASD - идти, Пробел - огонь, C - цвет, Z - форма, F - лицо, R - заново",
        True, dark), (10, 8))
    screen.blit(font.render(
        "-/+ громкость, M - без звука. Жёлтый друг: коснись +5, не стреляй! Цель: 30 очков",
        True, dark), (10, 28))
    for k in range(lives):                                # жизни
        screen.blit(life_icons[color], (10 + k * 46, 50))
    score_text = big_font.render(f"Счёт: {score}", True, dark)
    screen.blit(score_text, (WIDTH - score_text.get_width() - 15, 52))
    # полоска громкости
    vol_shown = 0 if muted else volume
    label = "Звук выкл" if muted else f"Громкость: {int(vol_shown * 100)}%"
    screen.blit(font.render(label, True, dark), (WIDTH - 150, 100))
    pygame.draw.rect(screen, dark, (WIDTH - 150, 120, 130, 10), 1)
    pygame.draw.rect(screen, dark, (WIDTH - 150, 120, int(130 * vol_shown), 10))

    if state != "playing":
        shade = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        shade.fill((0, 0, 0, 140))
        screen.blit(shade, (0, 0))
        title = "Игра окончена" if state == "gameover" else "Победа!"
        for text, fnt, yy in (
            (title, huge_font, 220),
            (f"Счёт: {score}", big_font, 300),
            ("R - играть заново", big_font, 350),
        ):
            img = fnt.render(text, True, (255, 255, 255))
            screen.blit(img, img.get_rect(center=(WIDTH // 2, yy)))

    pygame.display.flip()
    clock.tick(60)

pygame.quit()
sys.exit()
