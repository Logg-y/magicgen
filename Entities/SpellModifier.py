from Enums.SpellTypes import SpellTypes
from Services import utils
from Enums.DebugKeys import debugkeys
import math

class SpellModifier(object):
    def __init__(self):
        self.params = ["power", "spelltype", "range", "precision", "damage", "aoe", "casttime", "nreff", "skipchance",
                       "fatiguecost", "maxbounces", "scalecost", "scalerate", "pathperresearch", "scalefatigueexponent",
                       "effect", "aispellmod", "reqdamaging", "spec", "provrange"]
        self.aispellmod = 0
        self.power = 0
        self.spelltype = 0
        self.range = 0
        self.precision = 0
        self.damage = 0
        self.aoe = 0
        self.casttime = 0
        self.nreff = 0
        self.skipchance = 40
        self.fatiguecost = 0
        self.maxbounces = 0
        self.pathlevel = 0
        self.effect = 0
        self.givecloudsfx = 0
        self.reqdamaging = -1
        self.spec = 0
        self.provrange = 0

        self.scalecost = 0.0
        self.scalerate = 0.0
        self.pathperresearch = 0.0
        self.scalefatigueexponent = 0.0

        self.nobattlefield = False
        self.minfinalfatiguecost = None
        self.maxfinalfatiguecost = None

        self.reqs = []
        self.descrs = []
        self.descrconds = []
        self.setcommands = []
        self.multcommands = []
        self.details = ""

    def compatibility(self, eff, researchlevel, isnextspell):
        "Return True if this modifier is compatible with the given SpellEffect."
        # Check reqs to begin with
        for r in self.reqs:
            if not r.test(eff):
                return False

        if self.nobattlefield:
            if 660 <= eff.aoe <= 670:
                return False
                
        if self.reqdamaging != -1:
            if self.reqdamaging > 0:
                if not utils.isDamagingSpellEffect(eff):
                    return False
            if self.reqdamaging == 0:
                if utils.isDamagingSpellEffect(eff):
                    return False
                
        for flag in SpellTypes:
            if self.spelltype & flag and not (eff.spelltype & flag):
                return False

        # Make sure that various things cannot be pushed out of range
        finalrange = self.range + (eff.range % 1000)
        if finalrange < 0:
            return False

        cast = 100 if eff.casttime is None else eff.casttime
        finalcast = self.casttime + cast
        if finalcast < 5:
            return False

        # Do nothing can slip through this as a secondary effect can alter it later
        finalpower = researchlevel + self.power
        if finalpower < max(0, eff.power) and (self.name != "Do Nothing" and not isnextspell):
            return False
        if finalpower > eff.maxpower and (self.name != "Do Nothing" and not isnextspell):
            return False

        finalnreff = self.nreff + (eff.nreff % 1000)
        if finalnreff <= 0:
            scaled = self.nreff + eff.nreff
            # if exactly some multiple of 1000 it's fine as that is x per level
            if scaled < 1000: 
                return False

        finalaoe = self.aoe + (eff.aoe % 1000)
        if finalaoe < 0:
            scaled = self.aoe + eff.aoe
            # if exactly some multiple of 1000 it's fine as that is x per level
            if scaled < 1000:
                return False

        finalbounces = self.maxbounces + eff.maxbounces
        if finalbounces < 0:
            return False

        finalpathlevel = self.pathlevel + eff.pathlevel
        if finalpathlevel <= 0 and eff.pathlevel > 0:
            return False

        actualpowerlvl = (researchlevel - eff.power) + self.power

        if not eff.canGenerateAtPowerlvl(actualpowerlvl, self, None):
            print(f"Can't generate due to potential for identical spells to one at rl {researchlevel - 1}")
            return False

        if self.maxfinalfatiguecost is not None or self.minfinalfatiguecost is not None:
            finalfatigue = eff.calculateExpectedFinalFatigue(researchlevel, self, None)

            if self.maxfinalfatiguecost is not None and finalfatigue >= self.maxfinalfatiguecost:
                print(f"maxfinalfatiguecost of {finalfatigue} too high (vs {self.maxfinalfatiguecost})")
                return False
            if self.minfinalfatiguecost is not None and finalfatigue < self.minfinalfatiguecost:
                print(f"minfinalfatiguecost of {finalfatigue} too low (vs {self.maxfinalfatiguecost})")
                return False


        return True
    def apply(self, s):
        "Applies the modifier to the passed Spell object"
        # Forced modifier overrides
        for attrib, val in self.setcommands:
            print(f"mod: Set spell {attrib} to {val}")
            setattr(s, attrib, val)

        for attrib, val in self.multcommands:
            newval = int(getattr(s, attrib) * val)
            print(f"mod: Mult: spell {attrib} by {val} to {newval}")
            setattr(s, attrib, newval)

        # Apply modifier to the spell
        for param in self.params:
            if hasattr(s, param):
                paramval = getattr(self, param)
                if param == "aispellmod":
                    s.multiplyAISpellMod(1 + (paramval / 100))
                elif param == "spec" and paramval != 0:
                    # Add to nextspells too
                    next = s
                    attempts = 0
                    while 1:
                        attempts += 1
                        if next is None or next == "":
                            break
                        if next.spec & paramval == 0:
                            print(f"Add spec {paramval} to {next.name}")
                            next.spec += paramval
                        next = next.nextspell
                        if attempts > 10000:
                            raise Exception(f"Likely infinite nextspell recursion in {self.name}")
                else:
                    if getattr(s, param) is not None:
                        setattr(s, param, getattr(s, param) + paramval)
                        print(f"mod: Added {paramval} to {param}")
                    elif paramval != 0:
                        print(f"WARNING: trying to add {paramval} to parameter with value None {param}")