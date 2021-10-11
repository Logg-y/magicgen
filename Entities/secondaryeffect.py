from Enums.PathFlags import PathFlags
from Enums.SpellTypes import SpellTypes
from Services.utils import unitmods, eventsets, spelleffects
from Services import utils
from Enums.DebugKeys import debugkeys
from fileparser import unitinbasedatafinder
import math

class SpellSecondaryEffect(object):
    def __init__(self):
        self.spelltype = 0
        self.params = ["power", "spelltype", "range", "precision", "damage", "aoe", "casttime", "nreff", "skipchance",
                       "fatiguecost", "maxbounces", "scalecost", "scalerate", "pathperresearch", "scalefatigueexponent",
                       "nextspell", "unitmod", "spec", "aispellmod"]
        self.power = 0
        self.spelltype = 0
        self.range = 0
        self.precision = 0
        self.damage = 0
        self.aoe = 0
        self.spec = 0
        self.casttime = 0
        self.nreff = 0
        self.skipchance = 0
        self.fatiguecost = 0
        self.fatiguecostpereffect = 0
        self.maxbounces = 0
        self.pathlevel = 0
        self.paths = 0
        self.offensiveeffect = 0
        self.ondamage = 0
        self.aispellmod = 0
        self.requiredresearchlevel = None
        self.scalingaoelimit = None

        self.scalecost = 0.0
        self.scalerate = 0.0
        self.pathperresearch = 0.0
        self.scalefatigueexponent = 0.0

        self.fatiguepersquare = 0.0

        self.reqdamagingeffect = None
        self.minfinalaoe = None
        self.maxfinalfatiguecost = None
        self.minfinalfatiguecost = None

        self.nobattlefield = False
        self.nextspell = ""
        self.anysummon = False
        self.details = ""

        self.reqs = []
        self.descrs = []
        self.descrconds = []
        self.multcommands = []
        self.setcommands = []
        self.nameprefixes = []
        self.magicpathvaluescaling = 0.0
        self.unitmod = ""

        # Cache combos of (eff, modifier, researchlevel) and result
        self._cache = {}

    def compatibility(self, eff, modifier, researchlevel):
        "Return True if this secondary is compatible with the given SpellEffect."
        triplet = (eff, modifier, researchlevel)
        if triplet in self._cache:
            return self._cache[triplet]
        retval = self._compatibility(eff, modifier, researchlevel)
        self._cache[triplet] = retval
        return retval

    def calcModifiedPowerForSpellEffect(self, eff):
        if eff.chassisvalue is not None:
            eff.calcchassisvalues()
            finalpercentage = eff.chassisvaluepercent + (eff.magicvaluepercent * self.magicpathvaluescaling)
            thispower = round(finalpercentage * self.power, 0)
            return math.floor(thispower)
        return self.power
    def __repr__(self):
        return f"SecondaryEffect({self.name})"

    def _compatibility(self, eff, modifier, researchlevel):
        # Skipchance is done by the main processing loop now
        # it makes determining if there are legal modifiers for a spell a LOT better

        # see if the event list allows this unitmod
        # if yes then we need to be allowed, ignoring all the other reqs
        if eff.eventset is not None:
            realeventset = eventsets[eff.eventset]
            if self.unitmod in realeventset.allowedunitmods:
                return True
            if realeventset.unitmodlist is not None:
                unitmodlist = utils.unitmodlists[realeventset.unitmodlist]
                if self.unitmod in unitmodlist:
                    return True

        if self.nextspell != "" and eff.noadditionalnextspells > 0:
            return False

        if self.requiredresearchlevel is not None and self.requiredresearchlevel != researchlevel:
            return False

        finalpower = researchlevel + self.power + modifier.power

        if self.anysummon:
            if eff.effect in [1, 10001, 10050, 10038, 21, 10021]:
                if eff.effect in [1, 10001, 10050, 10038, 21]:
                    pass
                elif eff.effect in [10021]:
                    # Block weapon mods on permanent summon commanders
                    if self.unitmod != "":
                        unitmod = unitmods[self.unitmod]
                        if unitmod.weaponmod != "":
                            return False
            else:
                return False
            # Calculate what final power this should be, accounting for magic value and chassis value mismatches
            # This is so squishy human mages don't get pushed up to really high research for simple modifications
            # that don't really affect their combat ability
            if eff.chassisvalue is not None:
                thispower = self.calcModifiedPowerForSpellEffect(eff)
                finalpower = researchlevel + thispower + modifier.power


        if eff.isnextspell and self.name != "Do Nothing":
            return False

        # do not give nextspells secondary effects as they don't respect the path requirements the way the main spell does
        # oh and it could chain to ridiculous levels like "add a set on fire effect" "add an entangle to that set on fire" etc etc etc

        okay = self.paths == 0
        for flag in utils.breakdownflagcomponents(self.paths):
            if (eff.paths & flag):
                okay = True
                break
        if not okay:
            return False

        if self.nobattlefield:
            if 660 <= eff.aoe <= 670:
                return False

        for flag in utils.breakdownflagcomponents(self.spelltype):
            if not (eff.spelltype & flag):
                return False

        # Check #reqs
        for r in self.reqs:
            if not r.test(eff):
                return False

        # Make sure that various things cannot be pushed out of range
        finalrange = self.range + modifier.range + (eff.range % 1000)
        if finalrange < 0:
            return False

        cast = (100 if eff.casttime is None else eff.casttime) + modifier.casttime
        finalcast = self.casttime + cast
        if finalcast < 5:
            return False


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

        finalaoe = self.aoe + modifier.aoe + (eff.aoe % 1000) + (eff.aoe // 1000)*eff.pathlevel
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
            umod = unitmods[self.unitmod]
            if not umod.compatibilityWithSpellEffect(eff):
                return False

        extraresearch = researchlevel - finalpower
        actualpowerlvl = (researchlevel - eff.power) + self.power + modifier.power

        scaleamt = eff.scalerate * ((actualpowerlvl * (actualpowerlvl + 1)) / 2)
        if eff.spelltype & SpellTypes.POWER_SCALES_AOE:
            finalaoe += scaleamt

        # aoe limit so that mass rust doesn't get decay/burning etc
        # don't apply to holy spells as (at research 0) they need to be allowed this
        if self.scalingaoelimit is None and self.offensiveeffect != 0 and eff.paths != 256:
            scalingaoelimit = 3
        else:
            scalingaoelimit = self.scalingaoelimit
        if scalingaoelimit is not None:
            if finalaoe > 600:
                finalaoe = 50
            maxbaseaoe = scalingaoelimit * ((researchlevel * (researchlevel + 1)) / 2)
            # this is quadratic, negative power differentials (from slower casting etc) should be considered 0
            finalpower = max(0, finalpower)
            print(f"scalingaoelimit: {scalingaoelimit} at rl{researchlevel} has maxbaseaoe {maxbaseaoe}, "
                  f"spell has {finalaoe}, scaleamt was {scaleamt}")
            if finalaoe > maxbaseaoe:
                return False

        if self.reqdamagingeffect is not None:
            if self.reqdamagingeffect:
                if eff.effect % 1000 not in utils.DAMAGING_EFFECTS:
                    return False
            else:
                if eff.effect % 1000 in utils.DAMAGING_EFFECTS:
                    return False

        if self.ondamage:
            curr = eff
            while 1:
                # look for existing on damage effects, having multiple in the same spell
                # does not work correctly
                if isinstance(curr, str):
                    curr = spelleffects[curr]
                if curr.spec & 0x1000000000000000:
                    return False
                if curr.effect > 1000:
                    return False
                if curr.nextspell is not None and curr.nextspell != "":
                    curr = curr.nextspell
                    continue
                # this does currently not work on chain lightning effects (134)
                if curr.effect % 1000 not in utils.DAMAGING_EFFECTS or curr.effect % 1000 == 134:
                    return False
                break

        # Modifiers cannot check this including the secondary as well, this is
        # because modifiers come first: secondaries need to also check the modifier value
        maxfinalfatiguecost = self.maxfinalfatiguecost
        if modifier.maxfinalfatiguecost is not None:
            if self.maxfinalfatiguecost is None:
                maxfinalfatiguecost = modifier.maxfinalfatiguecost
            else:
                maxfinalfatiguecost = min(modifier.maxfinalfatiguecost, self.maxfinalfatiguecost)

        minfinalfatiguecost = self.minfinalfatiguecost
        if modifier.minfinalfatiguecost is not None:
            if self.minfinalfatiguecost is None:
                minfinalfatiguecost = modifier.minfinalfatiguecost
            else:
                minfinalfatiguecost = max(modifier.minfinalfatiguecost, self.minfinalfatiguecost)

        if maxfinalfatiguecost is not None or minfinalfatiguecost is not None:
            finalfatigue = eff.calculateExpectedFinalFatigue(researchlevel, modifier, self)

            if maxfinalfatiguecost is not None and finalfatigue >= maxfinalfatiguecost:
                print(f"maxfinalfatiguecost of {finalfatigue} too high (vs {maxfinalfatiguecost})")
                return False
            if minfinalfatiguecost is not None and finalfatigue < minfinalfatiguecost:
                print(f"minfinalfatiguecost of {finalfatigue} too low (vs {maxfinalfatiguecost})")
                return False




        if self.minfinalaoe is not None:
            if eff.spelltype & SpellTypes.POWER_SCALES_AOE:
                finalaoe = eff.aoe % 1000 + (eff.aoe // 1000 * eff.pathlevel)
                finalaoe += round(eff.scalerate * ((actualpowerlvl*(actualpowerlvl+1))/2), 0)
            else:
                finalaoe = eff.aoe
            if finalaoe < self.minfinalaoe:
                return False

        return True
