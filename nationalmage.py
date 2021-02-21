from typing import (
    Dict,
    List,
)
from spellstructures import PathFlags, utils
import sys
import debugkeys

class MagePathRandom(object):
    def __init__(self, chance, link, paths):
        self.chance: int = chance  # chance for generating
        self.link: int = link  # amount of levels it gives
        self.paths: int = paths  # path mask

    def getpossiblepaths(self) -> List[int]:
        acc = []
        for i in range(0, 8):
            if self.paths & (2 **i):
                acc.append(2 ** i)
        return acc

    def getnumberofpossiblepaths(self) -> int:
        acc: int = 0
        for i in range(0, 8):
            if self.paths & (2 ** i):
                acc += 1
        return acc


    def canrandompath(self, path: PathFlags) -> bool:
        return path in self.getpossiblepaths()

    def __repr__(self):
        return f"MagePathRandom(Paths={self.paths}, link={self.link}, chance={self.chance})"

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
        self.pathweights: Dict[PathFlags, float] = {}
        for i in range(0, 8):
            self.pathweights[2 ** i] = 0
        self.pathweightsinitialised: bool = False

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

    def gettotalpossiblepathsmask(self) -> int:
        acc: int = self.pathmask
        for random in self.randoms:
            acc |= random.paths
        return acc

    def getrandomspossiblepathmask(self) -> int:
        acc: int = 0
        for random in self.randoms:
            acc |= random.paths
        return acc

    def getguaranteedlevelinpath(self, path: int) -> int:
        return self.pathlevels[path]

    def totext(self) -> str:
        return f"({self.name},{utils.pathstotext(self.pathmask)},{utils.pathstotext(self.getrandomspossiblepathmask())})"

    def getaveragelevelinpath(self, path: PathFlags) -> float:
        acc: float = float(self.pathlevels[path])
        for random in self.randoms:
            if random.canrandompath(path):
                acc += random.link * random.chance / random.getnumberofpossiblepaths() / 100
        return acc

    def gettotalpathsamount(self) -> float:
        acc: float = 0.0
        for i in self.pathlevels:
            acc += self.pathlevels[i]
        for random in self.randoms:
            acc += random.chance * random.link
        return acc

    def getweightfractionforpath(self, path: PathFlags) -> float:
        if not self.pathweightsinitialised:
            self._calculatepathweightproportions()
        return self.pathweights[path]

    def _calculatepathweightproportions(self):
        debugkeys.debuglog(f"Generating pathweights for mage {self.totext()}",
                           debugkeys.debugkeys.NATIONALSPELLGENERATIONWEIGHTING)
        self.pathweightsinitialised = True
        for i in range(0, 8):
            self.pathweights[2 ** i] = self.getaveragelevelinpath(2 ** i)
        debugkeys.debuglog(f"Average levels (default weight) in paths: " +
                           str([utils.pathstotext(i) + " " + str(self.pathweights[i]) for i in self.pathweights]),
                           debugkeys.debugkeys.NATIONALSPELLGENERATIONWEIGHTING)
        s = sum(self.pathweights.values())
        debugkeys.debuglog(f"Total weights sum {s}",
                           debugkeys.debugkeys.NATIONALSPELLGENERATIONWEIGHTING)
        # Avoid ZeroDivisionError for non mages
        if s == 0.0:
            debugkeys.debuglog(f"No weight, therefore skipping adjustment",
                               debugkeys.debugkeys.NATIONALSPELLGENERATIONWEIGHTING)
            return
        for pathflag, weight in self.pathweights.items():  # Normalize
            self.pathweights[pathflag] = float(weight) / s

        debugkeys.debuglog(f"Adjusted weights: " +
                           str([utils.pathstotext(i) + " " + str(self.pathweights[i]) for i in self.pathweights]),
                           debugkeys.debugkeys.NATIONALSPELLGENERATIONWEIGHTING)
        s = sum(self.pathweights.values())
        debugkeys.debuglog(f"Total weights sum {s}",
                           debugkeys.debugkeys.NATIONALSPELLGENERATIONWEIGHTING)

    def __repr__(self):
        if len(self.randoms) > 3:
            return(f"NationalMage({self.id}, paths={self.pathlevels}, randoms={self.randoms[:2]})")
        return(f"NationalMage({self.id}, paths={self.pathlevels}, randoms={self.randoms}")