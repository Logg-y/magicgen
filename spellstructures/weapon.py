import csv
from copy import copy

# unlike with units, there are two files to cache in the name of speed
cache = {}
cache2 = {}


class Weapon(object):
    def __init__(self):
        pass

    @staticmethod
    def from_id(id):
        with open("weapons.csv", "r") as f:
            reader = csv.DictReader(f, delimiter="\t")
            for line in reader:
                if int(line["id"]) == id:
                    break
            return Weapon.from_line(line)

    @staticmethod
    def from_line(line):
        self = Weapon()
        self.origid = int(line["id"])
        self.line = line
        self.name = line["name"]
        self.att = int(line["att"])
        self.def_ = int(line["def"])
        self.len = int(line["len"])
        self.nratt = int(line["nratt"])
        self.ammo = int(line["ammo"])
        self.secondaryeffectid = int(line["secondaryeffect"])
        self.secondaryeffect = None
        if self.secondaryeffectid > 0:
            self.secondaryeffect = get(self.secondaryeffectid)
        self.secondaryeffectalwaysid = int(line["secondaryeffectalways"])
        self.secondaryeffectalways = None
        if self.secondaryeffectalwaysid > 0:
            self.secondaryeffectalways = get(self.secondaryeffectalwaysid)

        if self.origid in cache2:
            line = copy(cache2[self.origid])
        else:
            with open("effects_weapons.csv", "r") as f:
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
        return self


def get(id):
    if id in cache:
        return Weapon.from_line(copy(cache[id]))
    u = Weapon.from_id(id)
    cache[id] = copy(u.line)
    return u
