import os
import re

import spellstructures

secondary_params_int = ["att", "def_", "len", "nratt", "ammo", "secondaryeffectid", "secondaryeffectalwaysid", "effect",
                        "damage", "spec", "range", "aoe"]
secondary_params_str = ["nameprefix"]
secondary_params_float = []


def readWeaponModFile(fp):
    "Read one file and return all the weapon modifiers within."
    out = {}
    # ineff = False
    curreff = None
    with open(fp, "r") as f:
        for lineno, line in enumerate(f):
            line = line.strip()
            if line == "": continue
            if line.startswith("--"): continue

            if line.startswith("#newweaponmod"):
                if curreff is not None:
                    raise ParseError(f"{fp} line {lineno}: Unexpected #newweaponmod (still parsing previous effect)")
                m = re.match("#newweaponmod\W+\"(.*)\"\W*$", line)
                if m is None:
                    raise ParseError(f"{fp} line {lineno}: Expected a weapon mod name, none was found")
                curreff = spellstructures.WeaponMod()
                curreff.name = m.groups()[0]

            else:
                if curreff is None:
                    raise ParseError(f"{fp} line {lineno}: Expected a #newweaponmod line")

                sorted = False

                # Params to simply copy
                for simple in secondary_params_int:
                    m = re.match(f"#{simple}\\W+?([-0-9]*)\\W*$", line)
                    if m is not None:
                        pval = int(m.groups()[0])
                        setattr(curreff, simple, pval)
                        sorted = True
                        break

                if sorted: continue

                for simple in secondary_params_str:
                    m = re.match(f"#{simple}" + "\\W+?\"(.*)\"\\W*", line)
                    if m is not None:
                        pval = m.groups()[0]
                        setattr(curreff, simple, pval)
                        sorted = True
                        continue

                if sorted: continue

                for simple in secondary_params_float:
                    m = re.match(f"#{simple}\W+?([-.0-9]*)\W*$", line)
                    if m is not None:
                        pval = float(m.groups()[0])
                        setattr(curreff, simple, pval)
                        sorted = True
                        continue

                if sorted: continue

                if line.startswith("#req"):
                    m = re.match('#req2\\W+([0-9]*)[ \t]([<>=!]+)\\W+(.+)[ \t]+([<>=!]+)\\W*([0-9]*)', line)
                    if m is not None:
                        cond = spellstructures.NameCond()
                        cond.val2 = m.groups()[0]
                        cond.op2 = m.groups()[1]
                        cond.param = m.groups()[2]
                        cond.op = m.groups()[3]
                        cond.val = m.groups()[4]
                        cond.text = ""
                        curreff.reqs.append(cond)
                        continue

                    m = re.match('#req\\W+(.+)[ \t]+([<>&=!]+)\\W*([0-9]*)', line)
                    if m is None:
                        raise ParseError(f"{fp} line {lineno}: bad #req")
                    cond = spellstructures.NameCond()
                    cond.param = m.groups()[0]
                    cond.op = m.groups()[1]
                    cond.val = m.groups()[2]
                    cond.text = ""
                    curreff.reqs.append(cond)
                    continue

                if line.startswith("#set"):
                    m = re.match('#set\\W+(.*?)\\W*?([-0-9.]+)$', line)
                    if m is not None:
                        param = m.groups()[0]
                        val = int(m.groups()[1])
                        curreff.setcommands.append([param, val])
                        continue
                    raise ParseError(f"{fp} line {lineno}: bad #set")

                if line.startswith("#extracommand"):
                    m = re.match('#extracommand\\W+(.*?)$', line)
                    if m is not None:
                        param = m.groups()[0]
                        curreff.extracommands.append(param)
                        continue
                    raise ParseError(f"{fp} line {lineno}: bad #extracommand")

                if line.startswith("#mult"):
                    m = re.match('#mult\\W+(.*?)\\W*?([-0-9.]+)$', line)
                    if m is not None:
                        param = m.groups()[0]
                        val = int(m.groups()[1])
                        curreff.multcommands.append([param, val])
                        continue
                    raise ParseError(f"{fp} line {lineno}: bad #mult")

                if line.startswith("#end"):
                    out[curreff.name] = curreff
                    curreff = None
                    continue

                raise ParseError(f"{fp} line {lineno}: Unrecognised content: {line}")
    return out


def readWeaponModsFromDir(dir):
    out = spellstructures.weaponmods
    for f in os.listdir(dir):
        if f.endswith(".txt"):
            c = readWeaponModFile(os.path.join(dir, f))
            for key in c:
                if key in out:
                    raise ParseError(f"WeaponMod named {key} already exists and was redefined in {f}")
                out[key] = c[key]
