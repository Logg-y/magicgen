import os
import re


from Entities.eventset import EventSet
from Entities.namecond import NameCond
from Exceptions.ParseError import ParseError
from Services.utils import eventsets, eventmodulegroups

secondary_params_int = ["requiredcodes", "usefixedunitid", "desiredmontagsize", "restrictunitstospellpaths",
                        "mincreaturepower", "maxcreaturepower", "secondaryeffectchance", "minpowerlevel",
                        "maxpowerlevel", "modulebasescale", "makedummymonster", "moduleskipchance",
                        "setspelldamage", "makebattledummymonster", "fixedcreaturepower"]
secondary_params_str = ["modulegroup", "moduledescr", "moduledetails", "magicsite", "unitmodlist"]
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
                curreff = EventSet()
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
                        raise ParseError(f"{fp} line {lineno}: bad #scaleparam")
                    curreff.scaleparams[m.groups()[0]] = float(m.groups()[1])
                    continue

                # the trailing space here is NEEDED
                # or this trips all the other #module* params and tries to RE them and fails
                if line.startswith("#module "):
                    m = re.match('#module\\W+"(.*?)"\\W+?"(.*?)"', line)
                    if m is None:
                        raise ParseError(f"{fp} line {lineno}: bad #module")
                    curreff.modules[m.groups()[0]] = m.groups()[1]
                    continue

                if line.startswith("#textrepl"):
                    m = re.match('#textrepl\\W+"(.*?)"\\W+?"(.*?)"', line)
                    if m is None:
                        raise ParseError(f"{fp} line {lineno}: bad #textrepl")
                    curreff.textrepls[m.groups()[0]] = m.groups()[1]
                    continue

                if line.startswith("#incompatible"):
                    m = re.match('#incompatible\\W+"(.*?)"', line)
                    if m is None:
                        raise ParseError(f"{fp} line {lineno}: bad #incompatible")
                    curreff.incompatibilities.append(m.groups()[0])
                    continue

                if line.startswith("#noun"):
                    m = re.match('#noun\\W+"(.*?)"', line)
                    if m is None:
                        raise ParseError(f"{fp} line {lineno}: bad #noun")
                    curreff.nouns.append(m.groups()[0])
                    continue

                if line.startswith("#verb"):
                    m = re.match('#verb\\W+"(.*?)"', line)
                    if m is None:
                        raise ParseError(f"{fp} line {lineno}: bad #noun")
                    curreff.verbs.append(m.groups()[0])
                    continue

                if line.startswith("#req"):
                    m = re.match('#req2\\W+([0-9]*)[ \t]([<>=!]+)\\W+(.+)[ \t]+([<>=!]+)\\W*?([0-9]+)', line)
                    if m is not None:
                        cond = NameCond()
                        cond.val2 = m.groups()[0]
                        cond.op2 = m.groups()[1]
                        cond.param = m.groups()[2]
                        cond.op = m.groups()[3]
                        cond.val = m.groups()[4]
                        cond.text = ""
                        curreff.reqs.append(cond)
                        continue

                    m = re.match('#req\\W+(.+)[ \t]+([<>&=!]+)\\W*?([0-9]+)', line)
                    if m is None:
                        raise ParseError(f"{fp} line {lineno}: bad #req")
                    cond = NameCond()
                    cond.param = m.groups()[0]
                    cond.op = m.groups()[1]
                    cond.val = m.groups()[2]
                    cond.text = ""
                    curreff.reqs.append(cond)
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

                if line.startswith("#effectnumberforunits"):
                    m = re.match('#effectnumberforunits\\W+(.*)', line)
                    if m is None:
                        raise ParseError(f"{fp} line {lineno}: bad #effectnumberforunits")
                    curreff.effectnumberforunits.append(int(m.groups()[0]))
                    continue

                if line.startswith("#selectunitmod"):
                    m = re.match('#selectunitmod\\W+"(.*)"', line)
                    if m is None:
                        raise ParseError(f"{fp} line {lineno}: bad #selectunitmod")
                    if curreff.selectunitmod is None:
                        curreff.selectunitmod = []
                    curreff.selectunitmod.append(m.groups()[0])
                    continue

                if line.startswith("#end"):
                    out = curreff
                    parsingrawmodcode = True
                    continue

                raise ParseError(f"{fp} line {lineno}: Unrecognised content: {line}")
    return out


def readEventSetsFromDir(dir):
    out = eventsets
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
                if c.modulegroup is not None:
                    if c.modulegroup not in eventmodulegroups:
                        eventmodulegroups[c.modulegroup] = []
                    eventmodulegroups[c.modulegroup].append(c)
