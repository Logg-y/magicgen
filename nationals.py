import copy
import csv
import re

from typing import (
    Dict,
    List, Union,
)

from nationalsite import Site

from spellstructures import utils
from nation import Nation
from nationalmage import NationalMage, MagePathRandom

nations: Dict[int, Nation] = {}  # map nation id to nation

spellids = []
weaponids = []
monsterids: List[int] = []
eventcodes = []
montagids = []


def readVanilla():
    nationalunits = {}
    with open("fort_leader_types_by_nation.csv", "r") as datacsv:
        reader = csv.DictReader(datacsv, delimiter="\t")
        for line in reader:
            nationid = int(line["nation_number"])
            unit = int(line["monster_number"])
            if nationid not in nationalunits:
                nationalunits[nationid] = []
            nationalunits[nationid].append(unit)

    # Get their info
    unitdata = {}
    with open("BaseU.csv", "r") as datacsv:
        reader = csv.DictReader(datacsv, delimiter="\t")
        for line in reader:
            unitdata[int(line["id"])] = copy.copy(line)

    for nationid, units in nationalunits.items():
        if nationid not in nations:
            nations[nationid] = Nation(nationid)
        for unitid in units:
            if unitid in unitdata:
                dataline = unitdata[unitid]
                mage: NationalMage = NationalMage()
                for index, key in enumerate(["F", "A", "W", "E", "S", "D", "N", "B"]):
                    if dataline[key] != "":
                        mage.addsinglemagic(2 ** index, int(dataline[key]))

                for n in range(1, 7):
                    if dataline[f"mask{n}"] == "":
                        break
                    mask = int(dataline[f"mask{n}"]) >> 7
                    chance = int(dataline[f"rand{n}"])
                    instances = int(dataline[f"nbr{n}"])
                    link = int(dataline[f"link{n}"])
                    for i in range(instances):
                        mage.addrandom(MagePathRandom(chance=chance, link=link, paths=mask))

                mage.name = dataline[f"name"]

                if mage.ismage():
                    nations[nationid].addmage(mage)


def readMods(modstring):
    global monsterids, weaponids, spellids, eventcodes, montagids
    mods = modstring.strip().split(",")
    monsterids = [3499]
    weaponids = [799]
    spellids = [1299]
    eventcodes = [-299]
    montagids = [1000]
    for mod in mods:
        mod = mod.strip()
        if mod == "":
            continue
        with open(mod, "r", encoding="u8") as f:
            currentsite: Union[Site, None] = None
            sites: Dict[int, Site] = {}
            sitenames: Dict[str, int] = {}
            # TODO Sites that are defined after nations with them as startsite

            currentnation: Union[Nation, None] = None
            currentunit: Union[NationalMage,None] = None

            units: Dict[int, NationalMage] = {}

            for line in f:
                if "--" in line:
                    line = line[0:line.find("--")].strip()
                line = line.strip()
                if line == "": continue

                m = re.match("#newmonster (\\d+)", line)
                if m is None:
                    m = re.match("#selectmonster (\\d+)", line)
                if m is not None:
                    unitid = int(m.groups()[0])
                    print(f"Parsed newmonster {unitid}")
                    if unitid not in units:
                        units[unitid] = NationalMage()
                        units[unitid].id = unitid
                        monsterids.append(unitid)
                    currentunit = units[unitid]
                elif line.startswith("#newmonster"):
                    newid = max(monsterids) + 1
                    units[newid] = NationalMage()
                    monsterids.append(newid)
                    currentunit = units[newid]
                    currentunit.id = newid

                m = re.match("#montag (\\d+)", line)
                if m is not None:
                    newid = int(m.groups()[0])
                    montagids.append(newid)
                    print(f"Parsed montag {newid}")

                m = re.match("#code (.+)", line)
                if m is None:
                    m = re.match("#code2 (.+)", line)
                if m is None:
                    m = re.match("#codedelay (.+)", line)
                if m is None:
                    m = re.match("#codedelay2 (.+)", line)
                if m is not None:
                    newid = int(m.groups()[0])
                    eventcodes.append(newid)
                    print(f"Parsed event code {newid}")

                m = re.match("#newspell (\\d+)", line)
                if m is None:
                    m = re.match("#selectspell (\\d+)", line)
                if m is not None:
                    newid = int(m.groups()[0])
                    spellids.append(newid)
                    print(f"Parsed spell {newid}")
                elif line.startswith("#newspell"):
                    newid = max(spellids) + 1
                    print(f"Parsed spell with implied id {newid}")
                    spellids.append(newid)

                m = re.match("#newweapon (\\d+)", line)
                if m is None:
                    m = re.match("#selectweapon (\\d+)", line)
                if m is not None:
                    newid = int(m.groups()[0])
                    weaponids.append(newid)
                elif line.startswith("#newweapon"):
                    newid = max(weaponids) + 1
                    weaponids.append(newid)

                m = re.match("#selectnation (\\d+)", line)
                if m is not None:
                    nationid = int(m.groups()[0])
                    print(f"Parsed selectnation {nationid}")
                    if nationid not in nations:
                        nations[nationid] = Nation(nationid)
                    currentnation = nations[nationid]

                m = re.match("#newnation", line)
                if m is not None:
                    newid = -1
                    while newid in nations:
                        newid -= 1
                    print(f"Parsed newnation, assigned id {newid}")
                    if newid not in nations:
                        nations[newid] = Nation(newid)
                    currentnation = nations[newid]

                m = re.match("#newsite (\\d*)", line)
                if m is not None:
                    siteid = int(m.groups()[0])
                    print(f"Parsed newsite {siteid}")
                    currentsite = Site(siteid)
                    sites[siteid] = currentsite

                m = re.match("#name [\"](.+)[\"]", line)
                if m is not None:
                    name = m.groups()[0]
                    if currentsite is not None:
                        print(f"Attach site name {name} to {currentsite}")
                        currentsite.name = name
                        sitenames[name] = currentsite.id
                    elif currentnation is not None:
                        print(f"Attach nation name {name} to {currentnation}")
                        currentnation.name = name

                m = re.match("#era (.+)", line)
                if m is not None:
                    currentnation.era = int(m.groups()[0])

                m = re.match("#homecom (\\d+)", line)
                if m is not None:
                    unitid = int(m.groups()[0])
                    currentsite.mages.append(units[unitid])
                    print(f"Assign Commander {unitid} to site {currentsite}")

                m = re.match("#startsite [\"](.+)[\"]", line)
                if m is not None:
                    name = m.groups()[0]
                    currentnation.sites.append(sites[sitenames[name]])
                    print(f"Assign startsite {name} as belonging to {currentnation}")

                m = re.match("#addreccom (\\d+)", line)
                if m is not None:
                    unitid = int(m.groups()[0])
                    print(f"{unitid} is a recruitable commander of {currentnation}")
                    currentnation.addmage(units[unitid])

                if line.strip() == "#disableoldnations":
                    print(f"found disableoldnations")
                    for x in range(0, 120):
                        if x in nations:
                            del nations[x]

                if line.strip() == "#end":
                    print(f"Found #end")
                    currentnation = None
                    currentsite = None
                    currentunit = None

                m = re.match("#magicskill (\\d+) (\\d+)", line)
                if m is not None:
                    # In normal dominions modding, path flags are 0-7, just for this I converted them into their
                    # 2^n bitmask form
                    path = 2**int(int(m.groups()[0]))
                    level = int(m.groups()[1])
                    print(f"Give guaranteed path {path} of strength {level} to current commander")
                    currentunit.addsinglemagic(path, level)

                m = re.match("#custommagic (\\d+) (\\d+)", line)
                if m is not None:
                    mask = int(m.groups()[0]) >> 7
                    chancemask = int(m.groups()[1])
                    if chancemask > 100:
                        chance = 100
                        link = int(chancemask / 100)
                    else:
                        link = 1
                        chance = chancemask
                    random = MagePathRandom(paths=mask, chance=chance, link=link)
                    print(f"Give random path {mask} to current commander")
                    currentunit.addrandom(random)
