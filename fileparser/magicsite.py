import os
import re

from Entities import MagicSite
from Entities.namecond import NameCond
from Exceptions.ParseError import ParseError

modifier_params_int = ["rarity", "loc", "gold", "res", "level", "decunrest", "supply",
                        "incscale", "decscale", "conjcost", "altcost", "evocost", "constcost", "enchcost", "thaucost",
                       "bloodcost", "scry", "scryrange", "firerange", "airrange", "waterrange", "earthrange",
                       "astralrange", "deathrange", "naturerange", "bloodrange", "elementrange", "sorceryrange",
                       "allrange", "heal", "curse", "disease", "horrormark", "holyfire", "holypower", "xp",
                       "adventureruin", "blesshp", "blessanimawe", "blessmr", "blessawe", "blessmor", "blessstr",
                       "blessdarkvis", "blessatt", "blessdef", "blessprec", "blessfireres", "blesscoldres",
                       "blessshockres", "blesspoisres", "blessairshield", "blessreinvig", "blessdtv", "recallgod",
                       "domwar", "usefixedunitid", "desiredmontagsize", "restrictunitstospellpaths",
                        "mincreaturepower", "maxcreaturepower", "secondaryeffectchance", "makedummymonster",
                       "effectnumberforunits", "com", "mon", "summon", "summonlvl2", "summonlvl3", "summonlvl4",
                       "wallcom", "wallunit", "wallmult", "makebattledummymonster"]
modifier_params_str = ["selectunitmod", "unitmodlist"]
modifier_params_float = []


def readMagicSiteFile(fp):
    "Read one file and return all the magic sites within."
    out = {}
    curreff = None
    with open(fp, "r") as f:
        for lineno, line in enumerate(f):
            line = line.strip()
            if line == "": continue
            if line.startswith("--"): continue

            if line.startswith("#newsite"):
                if curreff is not None:
                    raise ParseError(f"{fp} line {lineno}: Unexpected #newsite (still parsing previous effect)")
                m = re.match("#newsite\W+\"(.*)\"\W*$", line)
                if m is None:
                    raise ParseError(f"{fp} line {lineno}: Expected a site name, none was found")
                curreff = MagicSite.MagicSite()
                curreff.name = m.groups()[0]

            else:
                if curreff is None:
                    raise ParseError(f"{fp} line {lineno}: Expected a #newsite line")

                sorted = False

                # Params to simply copy
                for simple in modifier_params_int:
                    m = re.match(f"#{simple}\\W+?([-0-9]*)\\W*$", line)
                    if m is not None:
                        pval = int(m.groups()[0])
                        setattr(curreff, simple, pval)
                        sorted = True
                        break

                if sorted: continue

                for simple in modifier_params_str:
                    m = re.match(f"#{simple}" + "\\W+?\"(.*)\"\\W*", line)
                    if m is not None:
                        pval = m.groups()[0]
                        setattr(curreff, simple, pval)
                        sorted = True
                        continue

                if sorted: continue

                for simple in modifier_params_float:
                    m = re.match(f"#{simple}\W+?([-.0-9]*)\W*$", line)
                    if m is not None:
                        pval = float(m.groups()[0])
                        setattr(curreff, simple, pval)
                        sorted = True
                        continue

                if sorted: continue

                m = re.match(f'#allowedunitmod "(.*)"', line)
                if m is not None:
                    pval = m.groups()[0]
                    curreff.allowedunitmods.append(pval)
                    sorted = True
                    continue

                if line.startswith("#scaleparam"):
                    m = re.match('#scaleparam\\W+"(.*)"\\W+?([0-9-.]*)', line)
                    if m is None:
                        raise ParseError(f"{fp} line {lineno}: bad #scaleparam")
                    curreff.scaleparams[m.groups()[0]] = float(m.groups()[1])
                    continue

                if line.startswith("#name"):
                    m = re.match('#name\\W+([0-9]*)\\W+"(.*)"', line)
                    if m is None:
                        raise ParseError(f"{fp} line {lineno}: bad #name")
                    path = int(m.groups()[0])
                    if path not in curreff.names:
                        curreff.names[path] = []
                    curreff.names[path].append(m.groups()[1])
                    continue

                if line.startswith("#dummymonstername"):
                    m = re.match('#dummymonstername\\W+([0-9]*)\\W+"(.*)"', line)
                    if m is None:
                        raise ParseError(f"{fp} line {lineno}: bad #dummymonstername")
                    path = int(m.groups()[0])
                    if path not in curreff.dummymonsternames:
                        curreff.dummymonsternames[path] = []
                    curreff.dummymonsternames[path].append(m.groups()[1])
                    continue

                if line.startswith("#end"):
                    out[curreff.name] = curreff
                    curreff = None
                    continue

                raise ParseError(f"{fp} line {lineno}: Unrecognised content: {line}")
    return out


def readMagicSitesFromDir(dir):
    from Services.utils import magicsites
    out = magicsites
    for f in os.listdir(dir):
        if f.endswith(".txt"):
            c = readMagicSiteFile(os.path.join(dir, f))
            for key in c:
                if key in out:
                    raise ParseError(f"MagicSite named {key} already exists and was redefined in {f}")
                out[key] = c[key]

