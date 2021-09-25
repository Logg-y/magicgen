import csv
import os
from copy import copy, deepcopy

from Entities import weapon

cache = {}
descriptioncache = {}

csv_keys = []

def getMontagSummonAIScore(montagID):
    if montagID == -2:
        return 72 # longdead
    elif montagID == -3:
        return 77 # average of armed and unarmed soulless
    elif montagID == -4:
        return 82 # ghoul, ignoring pischasa for now
    elif montagID == -5:
        return 100 # random animal: a guess as it will vary hugely no matter what is done to aispellmod
    elif montagID == -6:
        return 208 # lesser horror
    elif montagID == -7:
        return 346 # greater horror
    elif montagID == -8:
        return 1200 # doom horror
    elif montagID == -9:
        return 55 # swarm bugs
    elif montagID == -10:
        return 200 # good crossbreed, a guess
    elif montagID == -11:
        return 80 # bad crossbreed, a guess
    elif montagID == -12:
        return 90 # 3% good crossbreed, 97% bad crossbreed
    elif montagID == -13:
        return 95 # adventurers
    elif montagID == -14:
        return 120 # random dungeon creature, a guess
    elif montagID == -15:
        return 77 # more soulless
    raise ValueError(f"No summon AI score defined for montag {montagID}")

_badkeys = ["siegebonus", "castledef", "patrolbonus"]

class UnitInBaseDataFinder(object):
    def __init__(self):
        self.additionalmodcmds = ""
        self.origid = None
        self.id = None
        self.descr = ""
        # make sure keys are initialised - brand new units otherwise have nothing set
        if len(csv_keys) == 0:
            with open("data/BaseU.csv", "r") as f:
                reader = csv.DictReader(f, delimiter="\t")
                for line in reader:
                    for k in line.keys():
                        if k not in _badkeys:
                            setattr(self, k, -1)
                            csv_keys.append(k)
                    break
        else:
            for k in csv_keys:
                setattr(self,k, -1)
        self.weapons = []

    def __repr__(self):
        return (f"Unit({self.id}, {getattr(self, 'name', '???')})")

    def calcSummonAIScore(self):
        "Return the Illwinter base summon AI score for in an in battle summon of this unit."
        score = 2 * (getattr(self, "att", 0) + getattr(self, "def", 0) + getattr(self, "str", 0) + getattr(self, "hp", 0))
        if getattr(self, "fireshield", 0) > 0 or getattr(self, "trample", 0) > 0:
            score += (getattr(self, "hp") * 4)
        if getattr(self, "ethereal", 0) > 0:
            score += (getattr(self, "hp") * 4)

        secondshape = int(getattr(self, "secondshape", -1))
        if secondshape > 0:
            unit = get(int(secondshape))
            score += unit.calcSummonAIScore()
        return score




    @staticmethod
    def from_id(id):
        with open("data/BaseU.csv", "r") as f:
            reader = csv.DictReader(f, delimiter="\t")
            for line in reader:
                if int(line["id"]) == id:
                    return UnitInBaseDataFinder.from_line(line)
        raise ValueError(f"Unit {id} not found")

    @staticmethod
    def from_line(line):
        global descriptioncache
        self = UnitInBaseDataFinder()
        self.line = line
        self.params = ["id", "origid", "weapons", "descr", "uniqueid"]
        id = int(line["id"])
        self.origid = id
        self.id = id
        for k in line.keys():
            try:
                val = int(line[k])
            except:
                val = line[k]
            if (val is None or val == "") and k in _badkeys:
                continue
            if val is None: val = -1
            if val == "": val = -1
            setattr(self, k, val)
            self.params.append(k)
        self.weapons = []
        for x in range(1, 8):
            if getattr(self, f"wpn{x}") > 0:
                self.weapons.append(weapon.get(getattr(self, f"wpn{x}")))

        self.descr = ""
        if self.id in descriptioncache:
            self.descr = copy(descriptioncache[self.id])
        else:
            fp = os.path.join("./unitdescr", f"{str(self.origid).zfill(4)}.txt")
            if os.path.isfile(fp):
                with open(fp, "r") as f:
                    self.descr = f.read()
            descriptioncache[self.id] = copy(self.descr)
        self.uniqueid = f"vanilla-{self.id}"

        return self
    def __deepcopy__(self, memo):
        out = UnitInBaseDataFinder()
        for param in self.params:
            setattr(out, param, deepcopy(getattr(self, param, memo)))
        return out


def get(id):
    # The file lookup is slow
    # I did just save the file lines, but this was still being slow so deepcopy it is
    if id in cache:
        return deepcopy(cache[id])
    u = UnitInBaseDataFinder.from_id(id)
    cache[id] = u
    return deepcopy(u)
