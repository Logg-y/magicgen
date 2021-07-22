import os
import re

from Entities.namecond import NameCond
from Entities.unitmodlist import UnitModList
from Exceptions.ParseError import ParseError
from Services.utils import unitmodlists

secondary_params_int = []
secondary_params_str = []
secondary_params_float = []


def readUnitModListFile(fp):
    "Read one file and return all the spell modifiers within."
    out = {}
    curreff = None
    with open(fp, "r") as f:
        for lineno, line in enumerate(f):
            line = line.strip()
            if line == "": continue
            if line.startswith("--"): continue

            if line.startswith("#newunitmodlist"):
                if curreff is not None:
                    raise ParseError(f"{fp} line {lineno}: Unexpected #newunitmodlist (still parsing previous effect)")
                m = re.match("#newunitmodlist\W+\"(.*)\"\W*$", line)
                if m is None:
                    raise ParseError(f"{fp} line {lineno}: Expected an effect name, none was found")
                curreff = UnitModList()
                curreff.name = m.groups()[0]

            else:
                if curreff is None:
                    raise ParseError(f"{fp} line {lineno}: Expected a #newunitmodlist line")

                m = re.match(f'#allowedunitmod "(.*)"', line)
                if m is not None:
                    pval = m.groups()[0]
                    curreff.allowedunitmods.append(pval)
                    continue

                if line.startswith("#end"):
                    out[curreff.name] = curreff
                    curreff = None
                    continue

                raise ParseError(f"{fp} line {lineno}: Unrecognised content: {line}")
    return out


def readUnitModListsFromDir(dir):
    out = unitmodlists
    for f in os.listdir(dir):
        if f.endswith(".txt"):
            c = readUnitModListFile(os.path.join(dir, f))
            for key in c:
                if key in out:
                    raise ParseError(f"UnitModList named {key} already exists and was redefined in {f}")
                out[key] = c[key]
