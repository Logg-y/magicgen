import os
import re

import spellstructures
from spellstructures.utils import ParseError

secondary_params_int = ["requiredcodes", "usefixedunitid", "desiredmontagsize", "restrictunitstospellpaths", "mincreaturepower", "maxcreaturepower", "secondaryeffectchance"]
secondary_params_str = ["selectunitmod"]
secondary_params_float = []


def readEventSet(fp):
    "Read one file and return its event set."
    out = None
    curreff = None
    parsingrawmodcode = False
    with open(fp, "r") as f:
        for lineno, line in enumerate(f):
            line = line.strip()
            if line == "" and not parsingrawmodcode: continue
            if line.startswith("--") and not parsingrawmodcode: continue

            if line.startswith("#neweventset"):
                if curreff is not None:
                    raise ParseError(f"{fp} line {lineno}: Unexpected #neweventset (only 1 per file!)")
                m = re.match("#neweventset\W+\"(.*)\"\W*$", line)
                if m is None:
                    raise ParseError(f"{fp} line {lineno}: Expected an eventset name, none was found")
                curreff = spellstructures.EventSet()
                curreff.name = m.groups()[0]

            else:
                if parsingrawmodcode:
                    curreff.rawdata += (line + "\n")
                    continue
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

                m = re.match(f'#allowedunitmod "(.*)"', line)
                if m is not None:
                    pval = m.groups()[0]
                    curreff.allowedunitmods.append(pval)
                    sorted = True
                    continue

                if line.startswith("#scaleparam"):
                    m = re.match('#scaleparam\\W+"(.*)"\\W+?([0-9-.]*)', line)
                    if m is None:
                        raise spellstructures.ParseError(f"{fp} line {lineno}: bad #scaleparam")
                    curreff.scaleparams[m.groups()[0]] = float(m.groups()[1])
                    continue

                if line.startswith("#end"):
                    out = curreff
                    parsingrawmodcode = True
                    continue

                raise ParseError(f"{fp} line {lineno}: Unrecognised content: {line}")
    return out


def readEventSetsFromDir(dir):
    out = spellstructures.eventsets
    for dirpath, dirnames, files in os.walk(dir):
        for f in files:
            print(f)
            if f.endswith(".txt"):
                c = readEventSet(os.path.join(dirpath, f))
                if c is None:
                    continue
                if c.name in out:
                    raise ParseError(f"EventSet named {c.name} already exists and was redefined in {f}")
                out[c.name] = c
