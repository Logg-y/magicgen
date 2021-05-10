import csv
import os
from copy import copy

from Entities import weapon

cache = {}
descriptioncache = {}

csv_keys = []

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
                        setattr(self, k, -1)
                        csv_keys.append(k)
                    break
        else:
            for k in csv_keys:
                setattr(self,k, -1)
        self.weapons = []


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
        id = int(line["id"])
        self.origid = id
        self.id = id
        for k in line.keys():
            try:
                val = int(line[k])
            except:
                val = line[k]
            if val is None: val = -1
            if val == "": val = -1
            setattr(self, k, val)
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


def get(id):
    # The file lookup is slow
    # but also making deepcopy methods for objects is really annoying
    # so probably easiest to save the file line
    if id in cache:
        return UnitInBaseDataFinder.from_line(copy(cache[id]))
    u = UnitInBaseDataFinder.from_id(id)
    cache[id] = copy(u.line)
    return u
