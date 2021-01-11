from . import unit
from . import utils
from .utils import PathFlags, SpellTypes


class SpellSecondaryEffect(object):
    def __init__(self):
        self.spelltype = 0
        self.params = ["power", "spelltype", "range", "precision", "damage", "aoe", "casttime", "nreff", "skipchance",
                       "fatiguecost", "maxbounces", "scalecost", "scalerate", "pathperresearch", "scalefatigueexponent",
                       "nextspell", "unitmod"]
        self.power = 0
        self.spelltype = 0
        self.range = 0
        self.precision = 0
        self.damage = 0
        self.aoe = 0
        self.casttime = 0
        self.nreff = 0
        self.skipchance = 0
        self.fatiguecost = 0
        self.fatiguecostpereffect = 0
        self.maxbounces = 0
        self.pathlevel = 0
        self.paths = 0

        self.scalecost = 0.0
        self.scalerate = 0.0
        self.pathperresearch = 0.0
        self.scalefatigueexponent = 0.0

        self.nobattlefield = False
        self.nextspell = ""
        self.anysummon = False

        self.reqs = []
        self.descrs = []
        self.descrconds = []
        self.multcommands = []
        self.setcommands = []
        self.magicpathvaluescaling = 0.0
        self.unitmod = ""

    def compatibility(self, eff, modifier, researchlevel):
        "Return True if this secondary is compatible with the given SpellEffect."
        # Skipchance is done by the main processing loop now
        # it makes determining if there are legal modifiers for a spell a LOT better

        # see if the event list allows this unitmod
        # if yes then we need to be allowed, ignoring all the other reqs
        if eff.eventset is not None:
            realeventset = utils.eventsets[eff.eventset]
            if self.unitmod in realeventset.allowedunitmods:
                return True


        # Check reqs to begin with
        for r in self.reqs:
            if not r.test(eff):
                return False
				
        if self.nextspell != "" and eff.noadditionalnextspells > 0:
            return False

        if self.anysummon:
            if eff.effect in [1, 10001, 10050, 10038, 21, 10021]:
                if eff.effect in [1, 10001, 10050, 10038, 21]:
                    pass
                elif eff.effect in [10021]:
                    # Block weapon mods on permanent summon commanders
                    if self.unitmod != "":
                        unitmod = utils.unitmods[self.unitmod]
                        if unitmod.weaponmod != "":
                            return False
            else:
                return False
        if eff.isnextspell and self.name != "Do Nothing":
            return False
        # do not give nextspells secondary effects as they don't respect the path requirements the way the main spell does
        # oh and it could chain to ridiculous levels like "add a set on fire effect" "add an entangle to that set on fire" etc etc etc

        okay = self.paths == 0
        for flag in PathFlags:
            if self.paths & flag and (eff.paths & flag):
                okay = True
                break
        if not okay:
            return False

        if self.nobattlefield:
            if 660 <= eff.aoe <= 670:
                return False

        for flag in SpellTypes:
            if self.spelltype & flag and not (eff.spelltype & flag):
                return False

        # Make sure that various things cannot be pushed out of range
        finalrange = self.range + modifier.range + (eff.range % 1000)
        if finalrange < 0:
            return False

        cast = (100 if eff.casttime is None else eff.casttime) + modifier.casttime
        finalcast = self.casttime + cast
        if finalcast < 5:
            return False

        finalpower = researchlevel + self.power + modifier.power
        # power extremes don't matter for holy spells
        # do nothing should also always be allowed
        if not eff.isnextspell and self.name != "Do Nothing":
            if finalpower < max(0, eff.power) and eff.paths != 256:
                return False
            if finalpower > eff.maxpower and eff.paths != 256:
                return False

        finalnreff = self.nreff + modifier.nreff + (eff.nreff % 1000)
        if finalnreff <= 0:
            return False

        finalaoe = self.aoe + modifier.aoe + (eff.aoe % 1000)
        if finalaoe < 0:
            return False

        finalbounces = self.maxbounces + eff.maxbounces + modifier.maxbounces
        if finalbounces < 0:
            return False

        finalpathlevel = self.pathlevel + eff.pathlevel + modifier.pathlevel
        # skip for holy
        if eff.paths != 256:
            if finalpathlevel <= 0 and eff.pathlevel > 0:
                return False

        if self.unitmod != "":
            u = unit.get(eff.damage)
            umod = utils.unitmods[self.unitmod]
            if not umod.compatibility(u):
                return False

        return True
