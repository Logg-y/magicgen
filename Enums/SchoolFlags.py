import enum


class SchoolFlags(enum.IntFlag):
    UNRESEARCHABLE = -1
    CONJURATION = 1
    ALTERATION = 2
    EVOCATION = 4
    CONSTRUCTION = 8
    ENCHANTMENT = 16
    THAUMATURGY = 32
    BLOOD = 64
    DIVINE = 128