import random
import sys
from typing import (
    Dict,
    List,
)
from Enums.PathFlags import PathFlags

# This gets populated later by the file parser
spelleffects = {}
modifiers = {}
secondaries = {}
unitmods = {}
weaponmods = {}
eventsets = {}
# For storing which eventsets are in each module group
eventmodulegroups = {}

magicsites = {}
magicsitenames = []

newunits = {}

# For tracking how many permanent slot taking spells have been made
# too many means that mechanic abuse from filling all 6 slots is possible
# this is saved as primary path: number of offending spells generated
permanent_slot_spells_by_path: Dict[int, int] = {}

spellnames = []
spellnamesbyeffect = {}
spellqualifiers = ["Improved ", "Advanced ", "Masterful ", "Perfected ", "Flawless ", "Ultimate "]

# The IDs to start making STUFF at.
SPELL_ID = 1310
WEAPON_ID = 810
MONSTER_ID = 3550
ENCHANTMENT_ID = 500
EVENT_CODE = -100
MONTAG_ID = 1001
SITE_ID = 1510

MONTAG_SCALE = 1.0


UNITMOD_TO_SECONDARY_CACHE = {}

def unitmodToSecondary(unitmod, fallback=True):
    """Return the secondary effect that uses the unitmod. If fallback,
    returns Do Nothing if there isn't one, else raises an error."""
    if unitmod.name in UNITMOD_TO_SECONDARY_CACHE:
        secondary = UNITMOD_TO_SECONDARY_CACHE[unitmod.name]
        if secondary is None and fallback:
            secondary = secondaries["Do Nothing"]
        elif secondary is None:
            raise ValueError(f"Couldn't find secondary effect for unitmod {unitmod.name}")
        return secondary
    else:
        for name, secondary in secondaries.items():
            if secondary.unitmod == unitmod.name:
                UNITMOD_TO_SECONDARY_CACHE[unitmod.name] = secondary
                return(secondary)
                break

        UNITMOD_TO_SECONDARY_CACHE[unitmod.name] = None

        if secondary.unitmod != unitmod.name and fallback:
            print(f"Couldn't find secondary effect for unitmod {unitmod.name} - convert to Do Nothing")
            secondary = secondaries["Do Nothing"]
            return secondary
        raise ValueError(f"Couldn't find secondary effect for unitmod {unitmod.name}")

def _selectFlag(flagpool, allowed):
    "From flagpool, chooses one bitflag at random which is specified in allowed. Returns None if there were no flags to return"
    l = []
    for x in flagpool:
        if x.value > -1:
            if allowed & x:
                l.append(x)
    if len(l) == 0:
        return None
    return random.choice(l)


def breakdownflag(flag):
    n = 0
    out = []
    while 1:
        if 2 ** n > flag: return out
        if flag & 2 ** n: out.append(n)
        n += 1


def pathstotext(path: int) -> str:
    acc = ""
    if path & PathFlags.FIRE:
        acc += "F"
    if path & PathFlags.AIR:
        acc += "A"
    if path & PathFlags.WATER:
        acc += "W"
    if path & PathFlags.EARTH:
        acc += "E"
    if path & PathFlags.ASTRAL:
        acc += "S"
    if path & PathFlags.DEATH:
        acc += "D"
    if path & PathFlags.NATURE:
        acc += "N"
    if path & PathFlags.BLOOD:
        acc += "B"
    if acc == "":
        acc += "_"
    return acc


def _writetoconsole(line):
    """Because PyInstaller and PySimpleGUI don't play nice unless specifying STDIN as well, I had to make
    this be converted to exe with --window to avoid the console coming up.
    For some reason after doing that, sys.stderr has to be flushed after every line to allow the GUI process
    to pick it up"""
    sys.stderr.write(line)
    sys.stderr.flush()


def normalizemapkeys(mapin: Dict) -> map:
    acc = 0
    for i in mapin:
        acc += mapin[i]
    for i in mapin:
        mapin[i] = mapin[i] / acc
    return mapin
