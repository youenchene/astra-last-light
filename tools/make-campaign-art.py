#!/usr/bin/env python3
"""Author Astra's original campaign pixels offline; no input images or randomness.

Only the six owned campaign text sources are written. --check compares without
writing; --preview DIR uses the installed AGK PNG helper; --kit-check validates
exported sources through AGK without a manifest or build. All geometry is
native-resolution, hard-edged and palette-indexed.
"""

import argparse
import hashlib
import os
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / "game/art"
SYMBOLS = ".123456789ABCDEF"


class Canvas:
    """Small clipped integer rasterizer; coordinates include their endpoints."""

    def __init__(self, width, height, background=0):
        self.w, self.h = width, height
        self.p = [[background] * width for _ in range(height)]

    def dot(self, x, y, color):
        if 0 <= x < self.w and 0 <= y < self.h:
            self.p[y][x] = color

    def rect(self, x0, y0, x1, y1, color):
        for y in range(max(0, y0), min(self.h, y1 + 1)):
            for x in range(max(0, x0), min(self.w, x1 + 1)):
                self.p[y][x] = color

    def line(self, x0, y0, x1, y1, color):
        dx, dy = abs(x1 - x0), -abs(y1 - y0)
        sx, sy = (1 if x0 < x1 else -1), (1 if y0 < y1 else -1)
        error = dx + dy
        while True:
            self.dot(x0, y0, color)
            if (x0, y0) == (x1, y1):
                break
            twice = error * 2
            if twice >= dy:
                error += dy
                x0 += sx
            if twice <= dx:
                error += dx
                y0 += sy

    def poly(self, points, color):
        # Even/odd scan conversion, integer division, then close the boundary.
        for y in range(max(0, min(p[1] for p in points)),
                       min(self.h, max(p[1] for p in points) + 1)):
            crossings = []
            for (ax, ay), (bx, by) in zip(points, points[1:] + points[:1]):
                if (ay <= y < by) or (by <= y < ay):
                    crossings.append(ax + (y - ay) * (bx - ax) // (by - ay))
            crossings.sort()
            for left, right in zip(crossings[::2], crossings[1::2]):
                self.rect(left, y, right, y, color)
        for a, b in zip(points, points[1:] + points[:1]):
            self.line(a[0], a[1], b[0], b[1], color)

    def ellipse(self, cx, cy, rx, ry, color):
        for y in range(max(0, cy - ry), min(self.h, cy + ry + 1)):
            for x in range(max(0, cx - rx), min(self.w, cx + rx + 1)):
                if (x - cx) ** 2 * ry ** 2 + (y - cy) ** 2 * rx ** 2 <= rx ** 2 * ry ** 2:
                    self.dot(x, y, color)

    def paste(self, other, x, y):
        for yy, row in enumerate(other.p):
            for xx, color in enumerate(row):
                if color:
                    self.dot(x + xx, y + yy, color)


def plate(c, points, base=3, light=5):
    c.poly(points, 1)
    center_x = sum(x for x, _ in points) // len(points)
    center_y = sum(y for _, y in points) // len(points)
    inner = [(x + (1 if x < center_x else -1),
              y + (1 if y < center_y else -1)) for x, y in points]
    c.poly(inner, base)
    for a, b in zip(inner, inner[1:]):
        if b[0] >= a[0]:
            c.line(*a, *b, light)


def reactor(c, x, y, rx, ry, shade, glow):
    for a, b, col in [(rx + 2, ry + 2, 1), (rx + 1, ry + 1, 5),
                      (rx, ry, shade), (max(1, rx - 2), max(1, ry - 2), glow)]:
        c.ellipse(x, y, a, b, col)
    c.line(x - 1, y - max(1, ry - 2), x + 1, y + max(1, ry - 2), 7)


def salvage_boss():
    c = Canvas(64, 48)
    # Twin articulated grapple jaws leave a deep, readable open mouth at left.
    for points in [[(3, 4), (18, 2), (40, 10), (42, 19), (24, 15), (11, 11), (7, 18), (2, 17)],
                   [(2, 31), (8, 29), (12, 36), (27, 30), (45, 29), (40, 39), (17, 45), (3, 42)]]:
        plate(c, points, 3, 6)
    plate(c, [(27, 13), (48, 7), (60, 13), (62, 32), (49, 40), (26, 33), (19, 24)], 4, 5)
    plate(c, [(32, 15), (48, 12), (55, 18), (54, 30), (41, 35), (28, 29)], 3, 6)
    for y in (14, 31):
        c.rect(55, y, 60, y + 3, 12)
        c.rect(57, y, 61, y + 1, 14)
    c.rect(12, 20, 33, 28, 1)
    c.rect(12, 21, 30, 23, 5)
    c.rect(14, 25, 28, 27, 3)
    c.rect(11, 21, 14, 27, 13)
    c.rect(11, 23, 12, 25, 14)
    reactor(c, 42, 24, 6, 8, 12, 14)
    for x, y in [(17, 5), (24, 8), (30, 10), (17, 40), (24, 37), (30, 35)]:
        c.line(x, y, x + 2, y + 3, 1)
        c.dot(x + 3, y, 14)
    for y in range(18, 31, 3):
        c.line(51, y, 54, y - 1, 1)
    c.line(34, 11, 38, 4, 5)
    c.dot(38, 3, 15)
    c.line(34, 37, 38, 44, 3)
    for x, y in [(12, 6), (19, 8), (13, 38), (20, 36)]:
        c.line(x, y, x + 4, y + 1, 4)
        c.dot(x + 1, y - 1, 5)
    c.poly([(5, 7), (10, 6), (7, 12), (4, 14)], 2)
    c.line(6, 7, 9, 7, 5)
    c.poly([(5, 34), (8, 36), (10, 40), (5, 40)], 2)
    c.line(29, 16, 34, 14, 7)
    c.line(30, 32, 34, 33, 5)
    for x, y in [(46, 12), (50, 15), (50, 34), (58, 20), (58, 26)]:
        c.dot(x, y, 6)
    c.line(45, 35, 49, 33, 13)
    return c


def nebula_boss():
    c = Canvas(64, 48)
    # Swept manta fins, central eye, split needle tail; not a recolored carrier.
    plate(c, [(3, 22), (19, 14), (40, 2), (56, 2), (46, 12), (42, 19), (60, 15),
              (56, 24), (62, 34), (43, 29), (50, 41), (58, 46), (39, 43), (17, 31)], 8, 10)
    c.poly([(8, 23), (26, 17), (43, 6), (37, 19), (50, 23), (34, 30), (45, 40), (25, 31)], 9)
    c.poly([(10, 23), (29, 20), (40, 10), (33, 23), (40, 36), (25, 29)], 10)
    for points in [[(17, 20), (35, 12), (28, 20)], [(17, 28), (30, 29), (38, 37)]]:
        c.poly(points, 11)
    c.line(40, 5, 48, 4, 6)
    c.line(40, 42, 50, 44, 6)
    reactor(c, 29, 24, 9, 5, 9, 15)
    c.rect(29, 20, 30, 28, 1)
    c.dot(26, 22, 7)
    for x, y in [(42, 13), (45, 11), (47, 33), (43, 35), (52, 23)]:
        c.ellipse(x, y, 2, 1, 15)
        c.dot(x, y, 6)
    c.poly([(8, 20), (2, 16), (4, 22), (13, 24), (4, 26), (2, 32), (10, 28)], 5)
    c.line(43, 23, 58, 20, 10)
    c.line(44, 26, 59, 31, 10)
    for x, y in [(33, 14), (39, 10), (38, 35), (44, 40)]:
        c.line(x, y, x + 3, y - 1, 5)
    c.line(17, 24, 20, 24, 7)
    c.line(35, 21, 37, 22, 6)
    c.line(35, 27, 38, 26, 3)
    c.poly([(46, 6), (52, 4), (47, 9)], 3)
    c.poly([(47, 40), (52, 43), (44, 41)], 3)
    c.line(50, 18, 55, 17, 5)
    c.dot(48, 25, 11)
    return c


def foundry_boss():
    c = Canvas(64, 48)
    plate(c, [(13, 4), (49, 4), (59, 12), (59, 37), (48, 44), (13, 44), (6, 36), (6, 12)], 12, 14)
    plate(c, [(19, 8), (47, 8), (53, 15), (53, 33), (45, 39), (18, 39), (12, 32), (12, 15)], 13, 14)
    for y in (3, 35):
        plate(c, [(2, y), (31, y), (35, y + 4), (29, y + 10), (2, y + 10)], 3, 5)
        c.rect(2, y + 3, 24, y + 5, 5)
        c.rect(1, y + 3, 5, y + 8, 1)
        c.rect(2, y + 4, 3, y + 7, 14)
        for x in range(10, 29, 5):
            c.line(x, y + 6, x + 2, y + 8, 1)
    c.rect(15, 16, 42, 32, 1)
    c.rect(18, 18, 40, 30, 12)
    for x in range(20, 40, 5):
        c.rect(x, 19, x + 2, 29, 14)
        c.rect(x, 20, x + 1, 24, 7)
    c.rect(17, 24, 41, 25, 13)
    for y in (12, 31):
        c.line(42, y, 48, y + 4, 5)
        c.dot(43, y + 1, 7)
    for y in range(14, 35, 5):
        c.rect(54, y, 61, y + 2, 1)
        c.rect(57, y, 61, y, 14)
    c.rect(9, 17, 12, 31, 3)
    c.rect(7, 21, 10, 27, 15)
    # Recessed service bays, heat-scarred lower armor and upper rim lighting.
    c.poly([(17, 33), (39, 33), (45, 37), (20, 38)], 12)
    c.line(22, 34, 36, 34, 14)
    c.line(18, 14, 38, 14, 14)
    c.line(35, 10, 45, 10, 14)
    for x in range(35, 47, 4):
        c.rect(x, 11, x + 1, 12, 12)
    for y in (19, 27):
        c.rect(45, y, 50, y + 4, 12)
        c.line(46, y, 49, y, 14)
        c.rect(46, y + 2, 49, y + 3, 3)
    for x, y in [(16, 15), (40, 16), (40, 31), (15, 32), (50, 11), (51, 36)]:
        c.dot(x, y, 6)
    c.line(11, 14, 14, 12, 5)
    c.line(10, 32, 13, 35, 4)
    return c


def citadel_boss():
    c = Canvas(64, 48)
    # Cathedral crown: separate lance pinnacles around an open ion halo.
    for points in [[(4, 3), (28, 9), (42, 4), (57, 8), (59, 16), (29, 18), (15, 11)],
                   [(4, 44), (27, 37), (42, 43), (57, 39), (59, 31), (29, 29), (15, 36)]]:
        plate(c, points, 4, 6)
    c.ellipse(41, 24, 16, 16, 3)
    c.ellipse(41, 24, 14, 14, 6)
    c.ellipse(41, 24, 11, 11, 15)
    c.ellipse(41, 24, 9, 10, 0)
    plate(c, [(7, 23), (24, 18), (40, 19), (48, 24), (39, 29), (24, 30)], 5, 7)
    c.poly([(14, 24), (31, 21), (40, 24), (31, 27)], 15)
    c.line(18, 24, 37, 24, 7)
    for y in (4, 36):
        plate(c, [(22, y), (37, y + 3), (29, y + 7), (15, y + 6)], 3, 5)
        c.line(23, y + 2, 29, y + 3, 14)
    for x, y in [(42, 8), (55, 23), (41, 40)]:
        reactor(c, x, y, 2, 2, 9, 15)
    c.poly([(56, 20), (61, 17), (62, 23), (60, 29), (56, 28)], 5)
    c.line(59, 21, 59, 26, 7)
    c.line(34, 14, 40, 11, 7)
    c.line(47, 14, 51, 18, 7)
    c.line(48, 36, 52, 32, 4)
    c.line(34, 35, 39, 38, 4)
    for x, y in [(13, 8), (18, 10), (13, 39), (18, 37)]:
        c.line(x, y, x + 3, y, 15)
    c.line(29, 20, 35, 20, 6)
    c.line(30, 28, 36, 28, 3)
    c.dot(47, 24, 14)
    return c


def explosion(width, height, frame):
    c = Canvas(width, height)
    cx, cy = width // 2 - 1, height // 2 - 1
    # Integer directions and staged lobes give asymmetric motion without RNG.
    directions = [(10, 0), (7, 6), (1, 10), (-8, 7), (-10, -1),
                  (-6, -8), (3, -10), (9, -5)]
    radius = max(2, min(width, height) // 2 - 3)
    extent = [2, 4, 7, 10, 12, 14, 16, 18][frame]
    spread = radius * extent // 20
    if frame < 5:
        for i, (dx, dy) in enumerate(directions):
            x, y = cx + dx * spread // 12, cy + dy * spread // 12
            r = max(1, radius * [3, 5, 6, 5, 3][frame] // 10 + (i % 2))
            c.ellipse(x, y, r, max(1, r * 3 // 4), 12)
            c.ellipse(x - 1, y - 1, max(1, r - 1), max(1, r * 3 // 4 - 1), 13)
            c.ellipse(x - 1, y - 1, max(1, r - 2), max(1, r // 2), 14)
        r = max(1, radius * [2, 5, 6, 4, 2][frame] // 10)
        c.ellipse(cx, cy, r + 1, r, 14)
        c.ellipse(cx - 1, cy - 1, r, max(1, r - 1), 7 if frame < 3 else 11)
    else:
        for i, (dx, dy) in enumerate(directions):
            x, y = cx + dx * spread // 11, cy + dy * spread // 11
            r = max(1, radius * (8 - frame) // 13)
            c.ellipse(x, y, r + 1, r, 2 if frame == 7 else 12)
            c.dot(x, y, 13 if frame == 7 else 14)
            if frame == 5:
                c.line(x, y, x + dx // 5, y + dy // 5, 14)
    if 1 <= frame <= 4:
        # Lateral shock-wave emphasizes the large blast's wide aspect ratio.
        length = (width // 2 - 2) * (frame + 1) // 5
        c.line(cx - length, cy, cx - length // 2, cy, 6)
        c.line(cx + length // 2, cy, cx + length, cy, 6)
    return c


def stars(c, sector):
    for i in range(43):
        x, y = 72 + (i * 37 + sector * 11) % 86, 3 + (i * 23) % 85
        c.dot(x, y, 3 if i % 4 else 5)
    for x, y in [(90, 12), (147, 29), (120, 5)]:
        c.line(x - 2, y, x + 2, y, 3)
        c.line(x, y - 2, x, y + 2, 3)
        c.dot(x, y, 6)


def scenery(c, sector):
    stars(c, sector)
    if sector == 0:
        c.ellipse(125, 24, 24, 17, 2)
        c.ellipse(121, 21, 20, 14, 3)
        c.ellipse(116, 18, 15, 11, 4)
        c.line(91, 35, 154, 11, 5)
        c.line(94, 37, 155, 14, 3)
        for x, y in [(112, 12), (117, 15), (126, 24), (111, 27)]:
            c.line(x, y, x + 9, y + 1, 3)
            c.line(x + 2, y + 2, x + 7, y + 2, 4)
        for x, y in [(82, 55), (141, 63), (101, 34), (152, 78)]:
            plate(c, [(x, y), (x + 11, y - 4), (x + 7, y + 5), (x - 4, y + 8)], 2, 4)
            c.line(x, y + 2, x + 5, y, 13)
    elif sector == 1:
        for i in range(10):
            x, y = 80 + i * 8, 23 + (i * i * 3) % 38
            c.ellipse(x, y, 18, 9, 8)
            c.ellipse(x, y - 2, 13, 5, 9)
            c.line(x - 7, y - 3, x + 9, y - 4, 10)
        c.ellipse(134, 18, 12, 12, 15)
        c.ellipse(139, 15, 12, 12, 1)
        for x, y in [(90, 69), (149, 60), (104, 15)]:
            c.poly([(x, y - 8), (x + 4, y), (x, y + 9), (x - 3, y)], 9)
            c.line(x, y - 6, x, y + 5, 6)
    elif sector == 2:
        for x in range(80, 161, 18):
            c.rect(x, 4, x + 5, 74, 2)
            c.line(x, 8, x + 18, 29, 3)
            c.line(x, 30, x + 18, 10, 3)
            c.rect(x + 7, 13, x + 15, 31, 12)
            c.rect(x + 9, 17, x + 13, 28, 13)
            c.rect(x + 10, 20, x + 12, 26, 14)
        for y in (7, 34, 72):
            c.rect(78, y, 159, y + 2, 4)
            c.line(78, y + 3, 159, y + 3, 1)
    elif sector == 3:
        c.ellipse(128, 30, 30, 26, 8)
        c.ellipse(128, 30, 27, 23, 3)
        c.ellipse(128, 30, 24, 21, 1)
        for x, top in [(83, 26), (98, 13), (116, 3), (136, 14), (151, 24)]:
            c.poly([(x - 5, 69), (x - 3, top + 8), (x, top), (x + 3, top + 8), (x + 6, 69)], 3)
            c.line(x, top + 6, x, 65, 5)
            c.rect(x - 1, top + 17, x + 1, top + 24, 15)
    else:
        # Victory is a new composition: dawn over a living world, broken crown.
        c.ellipse(132, 97, 68, 47, 3)
        c.ellipse(131, 101, 66, 47, 15)
        c.ellipse(130, 105, 66, 47, 6)
        c.ellipse(130, 110, 65, 47, 5)
        for i in range(9):
            x, y = 86 + i * 9, 75 + (i * 7) % 18
            c.line(x, y, x + 12, y - 2, 6)
        for x, y in [(96, 20), (138, 30), (151, 11)]:
            plate(c, [(x, y), (x + 7, y - 4), (x + 3, y + 7)], 3, 5)
            c.line(x + 1, y + 8, x - 6, y + 17, 2)


def fighter(c, x, y, victory=False):
    # Authored for these panels; deliberately not imported/scaled hero art.
    c.poly([(x - 20, y + 1), (x - 9, y - 3), (x - 8, y + 5)], 9)
    c.poly([(x - 17, y + 1), (x - 8, y), (x - 8, y + 3)], 15)
    plate(c, [(x - 9, y - 2), (x - 12, y - 12), (x, y - 6), (x + 7, y - 2),
              (x + 23, y + 1), (x + 7, y + 5), (x - 12, y + 11), (x - 8, y + 4)], 4, 6)
    c.poly([(x - 6, y), (x + 7, y - 3), (x + 15, y), (x + 4, y + 2)], 15)
    c.line(x - 3, y - 1, x + 7, y - 2, 7)
    c.line(x - 8, y + 6, x + 6, y + 3, 3)
    c.rect(x - 9, y - 4, x - 6, y - 2, 14)
    if victory:
        c.line(x - 28, y + 3, x - 19, y + 2, 6)


def eye(c, x, y, narrowed=False, look=0):
    # Heavy upper lash, stepped almond whites, tall iris, catchlight and lid.
    c.poly([(x - 1, y), (x + 4, y - 2), (x + 11, y - 1), (x + 13, y + 2),
            (x + 9, y + 6), (x + 3, y + 6)], 8)
    c.poly([(x + 1, y + 1), (x + 5, y), (x + 10, y + 1),
            (x + 11, y + 3), (x + 8, y + 5), (x + 3, y + 4)], 6)
    c.rect(x + 5 + look, y + 1, x + 8 + look, y + 4, 15)
    c.rect(x + 6 + look, y + 1, x + 7 + look, y + 4, 1)
    c.dot(x + 5 + look, y + 1, 7)
    c.line(x, y, x + 5, y - 2, 1)
    c.line(x + 5, y - 2, x + 11, y - 1, 1)
    c.line(x + 2, y + 7, x + 8, y + 7, 13)
    if narrowed:
        c.line(x + 1, y + 1, x + 11, y + 1, 8)


def pilot_suit(c, sector):
    c.poly([(5, 95), (8, 83), (22, 77), (27, 69), (49, 68), (54, 77), (66, 82), (75, 95)], 1)
    c.poly([(8, 95), (12, 85), (25, 81), (29, 74), (47, 72), (54, 82), (64, 85), (70, 95)], 3)
    c.poly([(28, 67), (47, 64), (48, 77), (37, 83), (28, 77)], 13)
    c.poly([(31, 67), (44, 67), (44, 75), (37, 79), (32, 76)], 14)
    c.poly([(23, 77), (36, 85), (50, 77), (54, 82), (37, 91), (20, 83)], 5)
    c.line(24, 78, 36, 85, 6)
    c.line(36, 85, 49, 79, 6)
    c.poly([(11, 85), (21, 83), (26, 88), (22, 95), (8, 95)], 4)
    c.line(11, 86, 20, 85, 6)
    c.poly([(55, 85), (63, 88), (68, 95), (51, 95)], 4)
    c.rect(30, 91, 44, 94, 1)
    c.rect(32, 92, 37, 93, 15)
    for i in range(sector + 1):
        c.dot(40 + i, 92, 14)


def pilot_face(c, sector):
    # Same cyan-eyed, dark-violet-haired pilot in every panel; warm palette skin.
    c.poly([(17, 24), (30, 15), (46, 17), (57, 31), (56, 53), (48, 68),
            (38, 75), (29, 71), (20, 59), (15, 40)], 8)
    c.poly([(20, 28), (31, 21), (45, 22), (53, 33), (52, 55), (45, 66),
            (37, 72), (29, 67), (21, 54)], 13)
    c.poly([(25, 29), (36, 24), (46, 28), (50, 39), (47, 57), (42, 67),
            (36, 70), (29, 64), (23, 51)], 14)
    c.poly([(24, 46), (27, 38), (33, 36), (32, 52), (27, 57), (24, 54)], 11)
    c.poly([(42, 38), (48, 38), (49, 49), (44, 52)], 11)
    eye(c, 23, 43, narrowed=sector in (2, 3), look=1 if sector == 1 else 0)
    eye(c, 40, 42, narrowed=sector == 3)
    c.line(24, 38, 33, 39 if sector in (2, 3) else 36, 8)
    c.line(41, 37, 49, 35 if sector == 1 else 38, 8)
    c.line(38, 48, 36, 56, 13)
    c.line(36, 56, 39, 57, 13)
    c.dot(39, 55, 11)
    if sector == 4:
        c.poly([(31, 61), (43, 60), (39, 65), (35, 65)], 8)
        c.line(33, 62, 40, 61, 6)
        c.line(35, 67, 39, 67, 11)
    else:
        c.line(33, 62, 41, 61 if sector == 1 else 62, 12)
        c.line(35, 64, 39, 64, 11)
    # Consistent small cheek mark, visible through changing lighting/expression.
    c.line(47, 54, 45, 57, 13)
    if sector == 2:
        c.line(25, 56, 27, 58, 12)
        c.dot(24, 59, 12)


def pilot_hair(c, victory=False):
    c.poly([(12, 35), (13, 20), (22, 10), (37, 8), (52, 17), (58, 34), (53, 50),
            (49, 33), (43, 27), (43, 41), (34, 29), (29, 41), (25, 30), (18, 49)], 8)
    c.poly([(15, 31), (19, 19), (30, 13), (42, 13), (34, 20), (26, 24), (20, 39)], 9)
    c.poly([(29, 22), (37, 16), (48, 21), (51, 31), (42, 25), (40, 34)], 9)
    c.line(20, 23, 29, 17, 10)
    c.line(31, 16, 37, 14, 10)
    c.line(43, 20, 48, 25, 10)
    c.line(18, 32, 22, 25, 3)
    c.line(33, 25, 36, 30, 10)
    c.line(23, 22, 29, 19, 3)
    c.line(29, 18, 33, 17, 5)
    c.line(46, 25, 48, 29, 3)
    c.line(17, 33, 16, 39, 9)
    if victory:
        c.poly([(14, 31), (9, 48), (13, 67), (4, 78), (18, 72), (22, 56), (19, 43)], 8)
        c.line(13, 46, 16, 65, 9)
        c.line(16, 65, 10, 72, 10)
        c.poly([(52, 35), (56, 57), (66, 68), (61, 79), (52, 73), (50, 57)], 8)
        c.line(55, 59, 60, 68, 9)


def helmet(c, sector):
    # Open face flight helmet, side-mounted ear unit and transparent visor glints.
    c.poly([(6, 44), (5, 23), (13, 9), (28, 2), (46, 3), (58, 14), (64, 32),
            (60, 52), (54, 50), (55, 29), (48, 16), (32, 11), (20, 17), (13, 34), (13, 48)], 1)
    c.poly([(7, 28), (10, 17), (18, 9), (30, 5), (44, 6), (53, 14), (57, 24),
            (48, 15), (32, 10), (21, 15), (13, 28)], 5)
    c.line(16, 13, 29, 7, 6)
    c.line(30, 7, 42, 8, 7)
    c.poly([(10, 25), (16, 19), (13, 36), (8, 39)], 3)
    c.poly([(55, 18), (61, 31), (58, 44), (55, 39)], 4)
    c.line(58, 29, 59, 34, 6)
    c.ellipse(12, 47, 8, 11, 1)
    c.ellipse(12, 46, 6, 9, 4)
    c.ellipse(12, 46, 4, 6, 3)
    c.rect(10, 42, 13, 49, 15 if sector != 2 else 14)
    c.line(9, 40, 13, 39, 6)
    c.line(15, 54, 21, 60, 5)
    c.line(21, 60, 28, 60, 5)
    c.rect(26, 59, 30, 61, 1)
    c.dot(28, 59, 15)
    c.line(15, 33, 19, 27, 6)
    c.line(20, 26, 23, 24, 6)
    c.line(53, 47, 50, 56, 5)
    c.rect(32, 5, 38, 7, 13)
    c.rect(34, 5, 36, 6, 14)


def victory_hand(c):
    # Gloved two-finger salute, apart from the face: a distinct final gesture.
    c.poly([(60, 95), (56, 83), (57, 75), (55, 59), (57, 56), (60, 60),
            (63, 74), (65, 59), (68, 57), (70, 60), (69, 78), (74, 76),
            (77, 81), (73, 91), (75, 95)], 1)
    c.poly([(62, 95), (59, 82), (60, 75), (57, 60), (59, 62), (64, 79),
            (67, 61), (68, 61), (67, 81), (73, 79), (74, 83), (70, 91), (72, 95)], 5)
    c.line(58, 60, 61, 72, 6)
    c.line(67, 62, 66, 74, 7)
    c.line(61, 82, 68, 87, 3)
    c.line(62, 86, 66, 89, 3)
    c.rect(62, 92, 70, 94, 3)
    c.rect(64, 92, 68, 93, 15)


def manga_panel(sector, bosses):
    c = Canvas(160, 96, 1)
    scenery(c, sector)
    if sector < 4:
        c.paste(bosses[sector], 91, 32)
        fighter(c, 103, 83)
    else:
        fighter(c, 125, 47, victory=True)
        c.line(76, 48, 95, 47, 15)
        c.line(77, 51, 89, 50, 6)
    # Angled manga gutter separates intimate cockpit portrait from exterior.
    c.poly([(0, 0), (78, 0), (67, 96), (0, 96)], 2)
    c.poly([(1, 1), (74, 1), (63, 95), (1, 95)], 8 if sector == 1 else 1)
    for i in range(8):
        c.line(2, 14 + i * 10, 11, 7 + i * 10, 3)
    c.line(77, 0, 66, 95, 6)
    c.line(79, 0, 68, 95, 3)
    pilot_suit(c, sector)
    pilot_face(c, sector)
    pilot_hair(c, victory=sector == 4)
    if sector < 4:
        helmet(c, sector)
    else:
        victory_hand(c)
        c.poly([(18, 24), (23, 22), (25, 25), (20, 27)], 14)
        c.dot(21, 24, 7)
    # Sector pips rather than baked captions; parent owns localization/story text.
    for i in range(5):
        c.rect(83 + i * 6, 4, 86 + i * 6, 5, 14 if i <= sector else 3)
    return c


def palette():
    entries = [line.split() for line in (ART / "palette.txt").read_text().splitlines()
               if line.strip() and not line.startswith("#")]
    colors = {int(parts[0]): int(parts[1], 16) for parts in entries}
    if set(colors) != set(range(16)):
        raise ValueError("Campaign art requires the complete 16-entry world palette")
    return colors


def text_art(name, frames, colors, opaque=False):
    lines = [f"# Original local procedural campaign art: {name}; make-campaign-art.py", "colors"]
    lines += [f"  {SYMBOLS[i]} " + (f"0x{colors[i]:03X}" if i or opaque else "transparent")
              for i in range(16)]
    for frame in frames:
        lines.append("frame")
        lines += ["".join(SYMBOLS[i] for i in row) for row in frame.p]
    return "\n".join(lines) + "\n"


def make_assets():
    bosses = [salvage_boss(), nebula_boss(), foundry_boss(), citadel_boss()]
    flashes = []
    for boss in bosses:
        flash = Canvas(64, 48)
        flash.p = [[7 if col else 0 for col in row] for row in boss.p]
        flashes.append(flash)
    return {"campaign_boss": bosses, "campaign_flash": flashes,
            "campaign_fx16": [explosion(16, 16, f) for f in range(8)],
            "campaign_fx32": [explosion(32, 32, f) for f in range(8)],
            "campaign_fx64": [explosion(64, 48, f) for f in range(8)],
            "campaign_manga": [manga_panel(s, bosses) for s in range(5)]}


def validate(assets):
    contracts = [("boss", 64, 48, 4), ("flash", 64, 48, 4),
                 ("fx16", 16, 16, 8), ("fx32", 32, 32, 8),
                 ("fx64", 64, 48, 8), ("manga", 160, 96, 5)]
    for suffix, width, height, count in contracts:
        frames = assets[f"campaign_{suffix}"]
        assert len(frames) == count, suffix
        assert all((f.w, f.h) == (width, height) for f in frames), suffix
        assert all(0 <= p <= 15 for f in frames for row in f.p for p in row), suffix
        assert len({tuple(map(tuple, f.p)) for f in frames}) == count, suffix
        if suffix != "manga":
            assert all(any(p == 0 for row in f.p for p in row) for f in frames), suffix
        else:
            assert all(p != 0 for f in frames for row in f.p for p in row), suffix
    for boss, flash in zip(assets["campaign_boss"], assets["campaign_flash"]):
        assert all(b == (7 if a else 0) for ra, rb in zip(boss.p, flash.p)
                   for a, b in zip(ra, rb)), "Hit flash mask mismatch"


def load_kit():
    kit = Path(os.environ.get("AGK_KIT", str(Path.home() / "Code/amiga/amiga-game-kit")))
    sys.path.insert(0, str(kit / "harness"))


def check_kit(assets, colors):
    load_kit()
    from agk.art import Asset  # type: ignore[import-not-found]

    total = 0
    for name, frames in assets.items():
        opaque = name == "campaign_manga"
        cfg = {"source": f"{name}.txt", "kind": "bitmap" if opaque else "bob"}
        parsed = Asset(name, cfg, str(ART), colors, 4)
        expected = [[[colors[p] if p or opaque else None for p in row]
                     for row in frame.p] for frame in frames]
        if parsed.frames != expected or parsed.warnings:
            raise ValueError(f"AGK round-trip failed: {name}: {parsed.warnings}")
        size = len(parsed.planar()) * 2
        total += size
        print(f"AGK {name}: exact pixels/palette; {size} planar source bytes")
    print(f"AGK total: {total} planar source bytes (not live chip-memory usage)")


def previews(directory, assets, colors):
    load_kit()
    from agk.image import Image  # type: ignore[import-not-found]

    directory.mkdir(parents=True, exist_ok=True)
    for name, frames in assets.items():
        # Horizontal contact sheet, nearest-neighbor only; panel sheet has 2 rows.
        cols = 3 if name == "campaign_manga" else len(frames)
        scale = 3 if name == "campaign_manga" else 4
        fw, fh = frames[0].w, frames[0].h
        width, height = cols * (fw + 2), ((len(frames) + cols - 1) // cols) * (fh + 2)
        rgb = bytearray()
        for y in range(height * scale):
            for x in range(width * scale):
                xx, yy = x // scale, y // scale
                tile = (yy // (fh + 2)) * cols + xx // (fw + 2)
                px, py = xx % (fw + 2), yy % (fh + 2)
                color = 0x112
                if tile < len(frames) and px < fw and py < fh:
                    index = frames[tile].p[py][px]
                    color = colors[index] if index else (0x224 if (px // 4 + py // 4) % 2 else 0x112)
                rgb.extend(((color >> 8) * 17, ((color >> 4) & 15) * 17, (color & 15) * 17))
        Image(bytes(rgb), width * scale, height * scale).save_png(directory / f"{name}.png")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="verify reproducibility without rewriting assets")
    parser.add_argument("--preview", type=Path, help="optional contact sheets via AGK's local PNG API")
    parser.add_argument("--kit-check", action="store_true", help="round-trip exported text via AGK's parser")
    args = parser.parse_args()
    colors, assets = palette(), make_assets()
    validate(assets)
    for name, frames in assets.items():
        data = text_art(name, frames, colors, opaque=name == "campaign_manga").encode("ascii")
        path = ART / f"{name}.txt"
        if args.check:
            if not path.exists() or path.read_bytes() != data:
                raise SystemExit(f"Reproduction mismatch: {path}")
        else:
            path.write_bytes(data)
        print(f"{path.relative_to(ROOT)}: {frames[0].w}x{frames[0].h} x{len(frames)}; "
              f"{len(data)} bytes; sha256 {hashlib.sha256(data).hexdigest()}")
    if args.preview:
        previews(args.preview, assets, colors)
    if args.kit_check:
        check_kit(assets, colors)


if __name__ == "__main__":
    main()
