import csv
from copy import copy

# unlike with units, there are two files to cache in the name of speed
from typing import Dict

cache = {}
cache2 = {}


class Weapon(object):
    def __init__(self, data: Dict[str, str]):
        self.line = data
        self.origid =  int(data["id"])
        self.name = data["name"]
        self.att = int(data["att"])
        self.def_ = int(data["def"])
        self.len = int(data["len"])
        self.nratt = int(data["nratt"])
        self.ammo = int(data["ammo"])
        self.secondaryeffectid = int(data["secondaryeffect"])
        self.secondaryeffect = None
        self.secondaryeffectid = int(data["secondaryeffect"])
        self.secondaryeffect = None
        if self.secondaryeffectid > 0:
            self.secondaryeffect = get(self.secondaryeffectid)
        self.secondaryeffectalwaysid = int(data["secondaryeffectalways"])
        self.secondaryeffectalways = None
        if self.secondaryeffectalwaysid > 0:
            self.secondaryeffectalways = get(self.secondaryeffectalwaysid)

        if self.origid in cache2:
            line = copy(cache2[self.origid])
        else:
            with open("data/effects_weapons.csv", "r") as f:
                reader = csv.DictReader(f, delimiter="\t")
                for line in reader:
                    if int(line["record_id"]) == self.origid:
                        break
                cache2[self.origid] = copy(line)

        self.effect = int(line["effect_number"])
        self.damage = line["ritual"]
        self.spec = int(line["modifiers_mask"])

        self.range = line["raw_argument"]
        # this next thing seems to have values corresponding with strenght based range
        # this can also be stuff like AoE for fear effects

        # and now it's all confusing, so take only what I need
        self.aoe = int(line["area_base"])

    @staticmethod
    def from_id(id):
        with open("data/weapons.csv", "r") as f:
            reader = csv.DictReader(f, delimiter="\t")
            for line in reader:
                if int(line["id"]) == id:
                    break
            return Weapon.from_line(line)

    @staticmethod
    def from_line(line):
        return Weapon(line)


def get(id):
    if id in cache:
        return Weapon.from_line(copy(cache[id]))
    u = Weapon.from_id(id)
    cache[id] = copy(u.line)
    return u
