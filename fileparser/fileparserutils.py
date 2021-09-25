import re

def parseschool(alias):
    try:
        return int(alias)
    except ValueError:
        pass
    print(f"School alias {alias}")
    longform = {"none":-1, "unresearchable":-1, "conjuration":1, "conj":1, "alt":2, "alteration":2, "evo":4, "evocation":4,
                "construction":8, "constr":8, "const":8, "ench":16, "enchantment":16, "thaum":32, "thaumaturgy":32,
                "blood":64, "bloodmagic":64, "holy":128, "divine":128}
    tmp = alias.replace(" ", "").lower()
    components = tmp.split("+")
    ret = 0
    for component in components:
        if component in longform:
            ret += longform[component]
        else:
            try:
                ret += int(component)
            except:
                raise ValueError(f"Unrecognised researchschool alias {component} in string {alias}")
    print(f"School parse: {alias} -> {ret}")
    return ret

def parsepathalias(alias):
    try:
        return int(alias)
    except ValueError:
        pass
    tmp = alias.replace(" ", "").replace("+", "").lower()
    shortformchars = {"f":1, "a":2, "w":4, "e":8, "s":16, "d":32, "n":64, "b":128, "h":256}
    longform = {"none":-1, "fire":1, "air":2, "water":4, "earth":8, "astral":16, "death":32, "nature":64,
                           "blood":128, "holy":256}
    isshortform = True
    ret = 0
    for char in tmp:
        if char not in shortformchars:
            isshortform = False
            break
        ret += shortformchars[char]
    if isshortform:
        print(f"Shortform paths: {alias} -> {ret}")
        return ret
    tmp = alias.replace(" ", "").lower()
    components = tmp.split("+")
    ret = 0
    for component in components:
        if component in shortformchars:
            ret += shortformchars[component]
        else:
            if component in longform:
                ret += longform[component]
            else:
                try:
                    ret += int(component)
                except:
                    raise ValueError(f"Unrecognised path alias {component} in string {alias}")
    print(f"Longform paths: {alias} -> {ret}")
    return ret

def parsesimpleint(simple, line, curreff):
    if simple in ["schools"]:
        specialparser = parseschool
    elif simple in ["paths", "secondarypaths"]:
        specialparser = parsepathalias
    else:
        specialparser = None
    if specialparser is not None:
        m = re.match(f"#{simple}\\W+?(.*?)\\W*$", line)
        if m is None:
            #raise Exception(f"Failed special parser {specialparser.__name__} for line {line}")
            return False
        setattr(curreff, simple, specialparser(m.groups()[0]))
        return True

    m = re.match(f"#{simple}\\W+?([-0-9+^ ]*)\\W*$", line)
    if m is not None:
        arg = m.groups()[0].strip()
        try:
            pval = int(arg)
            setattr(curreff, simple, pval)
            return True
        except ValueError:
            print(f"{line} is not a simple int")
            arg = arg.replace(" ","")
            # Do powers first
            if "^" in arg:
                while "^" in arg:
                    m = re.search("([0-9]*)\\W*?\\^\\W*?([0-9]*)", arg)
                    if m is None:
                        raise ValueError(f"Error while parsing exponent in: {line}")
                    prev = int(m.groups()[0])
                    after = int(m.groups()[1])
                    val = prev ** after
                    arg = re.sub("([0-9]*)\\W*?\\^\\W*?([0-9]*)", str(val), arg, 1)
                print(f"After exponent replaces: {arg}")


            components = arg.split("+")
            real = 0
            for component in components:
                component = component.strip()
                real += int(component)
            print(f"Parser addition: {line} -> {real}")
            setattr(curreff, simple, real)
            return True
    return False
