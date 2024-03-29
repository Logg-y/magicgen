import os
import re

from Entities import newweapon
from Exceptions.ParseError import ParseError
from Services import fileparserutils

modifier_params_int = ["baseweapon"]
modifier_params_str = []
modifier_params_float = []


def readNewWeaponFile(fp):
    "Read one file and return all the new units within."
    out = {}
    curreff = None
    with open(fp, "r") as f:
        for lineno, line in enumerate(f):
            line = line.strip()
            if line == "": continue
            if line.startswith("--"): continue

            if line.startswith("#newweapon"):
                if curreff is not None:
                    raise ParseError(f"{fp} line {lineno}: Unexpected #newweapon (still parsing previous effect)")
                m = re.match("#newweapon\W+\"(.*)\"\W*$", line)
                if m is None:
                    raise ParseError(f"{fp} line {lineno}: Expected a weapon name, none was found")
                curreff = newweapon.NewWeapon()
                curreff.name = m.groups()[0]

            else:
                if curreff is None:
                    raise ParseError(f"{fp} line {lineno}: Expected a #newweapon line")

                sorted = False

                # Params to simply copy
                for simple in modifier_params_int:
                    if fileparserutils.parsesimpleint(simple, line, curreff):
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


                if line.startswith("#raw"):
                    m = re.match('#raw\\W+"(.*)"$', line)
                    if m is None:
                        raise ParseError(f"{fp} line {lineno}: bad #raw")
                    curreff.rawcmds.append(m.groups()[0].strip())
                    continue

                if line.startswith("#setstr"):
                    m = re.match('#setstr\\W+(.*?)\\W*?"(.+)"', line)
                    if m is not None:
                        param = m.groups()[0]
                        val = m.groups()[1]
                        curreff.setcmds.append([param, val])
                        continue
                    raise ParseError(f"{fp} line {lineno}: bad #setstr")

                if line.startswith("#set"):
                    m = re.match('#set\\W+(.*?)\\W*?([-0-9]+)', line)
                    if m is not None:
                        param = m.groups()[0]
                        val = int(m.groups()[1])
                        curreff.setcmds.append([param, val])
                        continue
                    raise ParseError(f"{fp} line {lineno}: bad #set")

                if line.startswith("#end"):
                    out[curreff.name] = curreff
                    curreff = None
                    continue

                raise ParseError(f"{fp} line {lineno}: Unrecognised content: {line}")
    return out


def readNewWeaponsFromDir(dir):
    from Services.utils import newweapons
    out = newweapons
    for f in os.listdir(dir):
        if f.endswith(".txt"):
            c = readNewWeaponFile(os.path.join(dir, f))
            for key in c:
                if key in out:
                    raise ParseError(f"NewWeapon named {key} already exists and was redefined in {f}")
                out[key] = c[key]
