"""Проверка звуков: запустите (py sound_test.py), вводите номер клипа 1-9
или название события (shoot, pop, pickup, hurt, levelup, gameover, start, win, music).
q - выход."""
import os

import pygame

pygame.mixer.init()
base = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sounds")
print("Клипы: 1-9 (папка sounds/all_clips). События: shoot, pop, pickup, hurt, levelup, gameover, start, win, music")
while True:
    cmd = input("Что играть? (номер / название / q): ").strip().lower()
    if cmd == "q":
        break
    path = os.path.join(base, "all_clips", f"clip_{cmd}.ogg") if cmd.isdigit() else os.path.join(base, cmd + ".ogg")
    if not os.path.exists(path):
        print("Такого звука нет")
        continue
    pygame.mixer.stop()
    pygame.mixer.Sound(path).play()
