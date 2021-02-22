import enum


class PathFlags(enum.IntFlag):
    NONE = -1
    FIRE = 1
    AIR = 2
    WATER = 4
    EARTH = 8
    ASTRAL = 16
    DEATH = 32
    NATURE = 64
    BLOOD = 128
    HOLY = 256