import csv
import os
from copy import copy

from . import weapon

cache = {}
descriptioncache = {}


class Unit(object):
    def __init__(self):
        pass

    @staticmethod
    def from_id(id):
        with open("BaseU.csv", "r") as f:
            reader = csv.DictReader(f, delimiter="\t")
            for line in reader:
                if int(line["id"]) == id:
                    break
            return Unit.from_line(line)

    @staticmethod
    def from_line(line):
        global descriptioncache
        self = Unit()
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
        return self


def get(id):
    # The file lookup is slow
    # but also making deepcopy methods for objects is really annoying
    # so probably easiest to save the file line
    if id in cache:
        return Unit.from_line(copy(cache[id]))
    u = Unit.from_id(id)
    cache[id] = copy(u.line)
    return u
