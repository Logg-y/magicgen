from Enums.SpellTypes import SpellTypes

DAMAGING_SPELL_EFFECTS = [2, 103, 74, 73, 3, 109]

class SpellModifier(object):
    def __init__(self):
        self.params = ["power", "spelltype", "range", "precision", "damage", "aoe", "casttime", "nreff", "skipchance",
                       "fatiguecost", "maxbounces", "scalecost", "scalerate", "pathperresearch", "scalefatigueexponent",
                       "effect", "aicastmod", "reqdamaging"]
        self.aicastmod = 0
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

        self.scalecost = 0.0
        self.scalerate = 0.0
        self.pathperresearch = 0.0
        self.scalefatigueexponent = 0.0

        self.nobattlefield = False

        self.reqs = []
        self.descrs = []
        self.descrconds = []
        self.setcommands = []
        self.multcommands = []

    def compatibility(self, eff, researchlevel, isnextspell):
        "Return True if this modifier is compatible with the given SpellEffect."
        # This is done by the main processing loop now
        # it makes determining if there are legal modifiers for a spell a LOT better

        # Check reqs to begin with
        for r in self.reqs:
            if not r.test(eff):
                return False

        if self.nobattlefield:
            if 660 <= eff.aoe <= 670:
                return False
                
        if self.reqdamaging != -1:
            if self.reqdamaging > 0:
                if eff.effect not in DAMAGING_SPELL_EFFECTS:
                    return False
            if self.reqdamaging == 0:
                if eff.effect in DAMAGING_SPELL_EFFECTS: 
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

        return True
