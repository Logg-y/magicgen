from typing import (
    Dict,
    List,
)
from spellstructures import PathFlags, utils
import sys

class MagePathRandom(object):
    def __init__(self, chance, link, paths):
        self.chance: int = chance  # chance for generating
        self.link: int = link  # amount of levels it gives
        self.paths: int = paths  # path mask


class NationalMage(object):
    "Container for a single national mage and its path access"
    def __init__(self):
        self.pathmask: int = 0  # Bit mask whether path exists. Indexes as in PathIndices
        self.pathlevels: Dict[int, int] = {}  # Map path index -> level
        for i in range(0, 8):
            self.pathlevels[2 ** i] = 0
        self.randoms: List[MagePathRandom] = []
        self.name = ""
        self.id = 0

    def addrandom(self, random: MagePathRandom):
        self.randoms.append(random)

    def addsinglemagic(self, pathmask: int, level: int):
        self.pathmask |= (pathmask & 255)  # Filter out holy levels
        self.pathlevels[pathmask] = level

    def canhaveblood(self) -> bool:
        for random in self.randoms:
            if random.paths & PathFlags.BLOOD:
                return True
        return (self.pathmask & PathFlags.BLOOD) != 0

    def ismage(self) -> bool:
        return (self.pathmask != 0) | (len(self.randoms) != 0)

    def hasaccesstopath(self, path: int) -> bool:
        for random in self.randoms:
            if random.paths & path:
                return True
        return (self.pathmask & path) != 0

    def getpossiblepaths(self) -> int:
        acc: int = self.pathmask
        for random in self.randoms:
            acc |= random.paths
        return acc

    def getrandompathpossibles(self) -> int:
        acc: int = 0
        for random in self.randoms:
            acc |= random.paths
        return acc

    def getlevelinpath(self, path: int) -> int:
        return self.pathlevels[path]

    def totext(self) -> str:
        return f"({self.name},{utils.pathstotext(self.pathmask)},{utils.pathstotext(self.getrandompathpossibles())})"
