from Enums.PathFlags import PathFlags
from Enums.SpellTypes import SpellTypes
from Services.utils import unitmods, eventsets, spelleffects
from Services import utils, DebugLogger
from Enums.DebugKeys import debugkeys
from fileparser import unitinbasedatafinder
from Entities.spell import Spell
import copy
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
        DebugLogger.debuglog(f"Begin secondary compatibility for {self.name} and {eff.name} "
                             f"with mod {modifier.name} at RL {researchlevel}", debugkeys.SECONDARYEFFECTCOMPATIBILITY)

        # see if the event list allows this unitmod
        # if yes then we need to be allowed, ignoring all the other reqs
        if eff.eventset is not None:
            realeventset = eventsets[eff.eventset]
            if self.unitmod in realeventset.allowedunitmods:
                DebugLogger.debuglog(f"Secondary is valid: allowed unit mod for eventset",
                                     debugkeys.SECONDARYEFFECTCOMPATIBILITY)
                return True
            if realeventset.unitmodlist is not None:
                unitmodlist = utils.unitmodlists[realeventset.unitmodlist]
                if self.unitmod in unitmodlist:
                    DebugLogger.debuglog(f"Secondary is valid: this unitmod is in unitmodlist for eventset",
                                         debugkeys.SECONDARYEFFECTCOMPATIBILITY)
                    return True

        if self.nextspell != "" and eff.noadditionalnextspells > 0:
            DebugLogger.debuglog(f"Secondary is invalid: this effect does not allow nextspells",
                                 debugkeys.SECONDARYEFFECTCOMPATIBILITY)
            return False

        if self.requiredresearchlevel is not None and self.requiredresearchlevel != researchlevel:
            DebugLogger.debuglog(f"Secondary is invalid: required research level is {self.requiredresearchlevel}",
                                 debugkeys.SECONDARYEFFECTCOMPATIBILITY)
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
                            DebugLogger.debuglog(
                                f"Secondary is invalid: no weapon mods allowed on permanent summon commanders",
                                debugkeys.SECONDARYEFFECTCOMPATIBILITY)
                            return False
            else:
                DebugLogger.debuglog(f"Secondary is invalid: secondary requires summon, but this spell effect is not",
                                     debugkeys.SECONDARYEFFECTCOMPATIBILITY)
                return False
            # Calculate what final power this should be, accounting for magic value and chassis value mismatches
            # This is so squishy human mages don't get pushed up to really high research for simple modifications
            # that don't really affect their combat ability
            if eff.chassisvalue is not None:
                thispower = self.calcModifiedPowerForSpellEffect(eff)
                finalpower = researchlevel + thispower + modifier.power


        if eff.isnextspell and self.name != "Do Nothing":
            DebugLogger.debuglog(f"Secondary is invalid: this is a nextspell, and nextspells are only allowed Do Nothing",
                                 debugkeys.SECONDARYEFFECTCOMPATIBILITY)
            return False

        # do not give nextspells secondary effects as they don't respect the path requirements the way the main spell does
        # oh and it could chain to ridiculous levels like "add a set on fire effect" "add an entangle to that set on fire" etc etc etc

        okay = self.paths == 0
        for flag in utils.breakdownflagcomponents(self.paths):
            if (eff.paths & flag):
                okay = True
                break
        if not okay:
            DebugLogger.debuglog(f"Secondary is invalid: effect paths {eff.paths} do not contain required paths {self.paths}",
                                 debugkeys.SECONDARYEFFECTCOMPATIBILITY)
            return False

        if self.nobattlefield:
            if 660 <= eff.aoe <= 670:
                DebugLogger.debuglog(f"Secondary is invalid: not allowed on battlefield wide effects",
                                     debugkeys.SECONDARYEFFECTCOMPATIBILITY)
                return False

        for flag in utils.breakdownflagcomponents(self.spelltype):
            if not (eff.spelltype & flag):
                DebugLogger.debuglog(f"Secondary is invalid: effect's spelltype missing flag {flag}",
                                     debugkeys.SECONDARYEFFECTCOMPATIBILITY)
                return False

        # Check #reqs
        for r in self.reqs:
            if not r.test(eff):
                DebugLogger.debuglog(f"Secondary is invalid: failed req {str(r)}",
                                     debugkeys.SECONDARYEFFECTCOMPATIBILITY)
                return False

        # Make sure that various things cannot be pushed out of range
        finalrange = self.range + modifier.range + (eff.range % 1000)
        if finalrange < 0:
            DebugLogger.debuglog(f"Secondary is invalid: final range would be negative",
                                 debugkeys.SECONDARYEFFECTCOMPATIBILITY)
            return False

        cast = (100 if eff.casttime is None else eff.casttime) + modifier.casttime
        finalcast = self.casttime + cast
        if finalcast < 5:
            DebugLogger.debuglog(f"Secondary is invalid: final cast time would be {finalcast} (<5% cast time)",
                                 debugkeys.SECONDARYEFFECTCOMPATIBILITY)
            return False


        # power extremes don't matter for holy spells
        # do nothing should also always be allowed
        if not eff.isnextspell and self.name != "Do Nothing":
            if finalpower < max(0, eff.power) and eff.paths != 256:
                DebugLogger.debuglog(f"Secondary is invalid: final power level of {finalpower} below effect minimum of {eff.power}",
                                     debugkeys.SECONDARYEFFECTCOMPATIBILITY)
                return False
            if finalpower > eff.maxpower and eff.paths != 256:
                DebugLogger.debuglog(f"Secondary is invalid: final powerlevel {finalpower} above effect max of {eff.maxpower}",
                                     debugkeys.SECONDARYEFFECTCOMPATIBILITY)
                return False

        finalnreff = self.nreff + modifier.nreff + (eff.nreff % 1000)
        if finalnreff <= 0:
            DebugLogger.debuglog(f"Secondary is invalid: final number of effects {finalnreff} must be positive",
                                 debugkeys.SECONDARYEFFECTCOMPATIBILITY)
            return False

        finalaoe = self.aoe + modifier.aoe + (eff.aoe % 1000) + (eff.aoe // 1000)*eff.pathlevel
        if finalaoe < 0:
            DebugLogger.debuglog(f"Secondary is invalid: final aoe {finalaoe} must not be negative",
                                 debugkeys.SECONDARYEFFECTCOMPATIBILITY)
            return False

        finalbounces = self.maxbounces + eff.maxbounces + modifier.maxbounces
        if finalbounces < 0:
            DebugLogger.debuglog(f"Secondary is invalid: final maxbounces {finalbounces} must not be negative",
                                 debugkeys.SECONDARYEFFECTCOMPATIBILITY)
            return False

        finalpathlevel = self.pathlevel + eff.pathlevel + modifier.pathlevel
        # skip for holy
        if eff.paths != 256:
            if finalpathlevel <= 0 and eff.pathlevel > 0:
                DebugLogger.debuglog(f"Secondary is invalid: finalpathlevel {finalpathlevel} not positive",
                                     debugkeys.SECONDARYEFFECTCOMPATIBILITY)
                return False

        if self.unitmod != "":
            umod = unitmods[self.unitmod]
            if not umod.compatibilityWithSpellEffect(eff):
                DebugLogger.debuglog(f"Secondary is invalid: unitmod incompatible with effect",
                                     debugkeys.SECONDARYEFFECTCOMPATIBILITY)
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
                DebugLogger.debuglog(f"Secondary is invalid: failed scalingaoelimit",
                                     debugkeys.SECONDARYEFFECTCOMPATIBILITY)
                return False

        if self.reqdamagingeffect is not None:
            if self.reqdamagingeffect:
                if eff.effect % 1000 not in utils.DAMAGING_EFFECTS:
                    DebugLogger.debuglog(
                        f"Secondary is invalid: spell effect is not damaging",
                        debugkeys.SECONDARYEFFECTCOMPATIBILITY)
                    return False
            else:
                if eff.effect % 1000 in utils.DAMAGING_EFFECTS:
                    DebugLogger.debuglog(
                        f"Secondary is invalid: spell effect is damaging",
                        debugkeys.SECONDARYEFFECTCOMPATIBILITY)
                    return False

        if self.ondamage:
            curr = eff
            while 1:
                # look for existing on damage effects, having multiple in the same spell
                # does not work correctly
                if isinstance(curr, str):
                    curr = spelleffects[curr]
                if curr.spec & 0x1000000000000000:
                    DebugLogger.debuglog(
                        f"Secondary is invalid: this spell already has an ondamage effect",
                        debugkeys.SECONDARYEFFECTCOMPATIBILITY)
                    return False
                if curr.effect > 1000:
                    DebugLogger.debuglog(
                        f"Secondary is invalid: ondamage effect not compatible with lingering spell effect",
                        debugkeys.SECONDARYEFFECTCOMPATIBILITY)
                    return False
                if curr.nextspell is not None and curr.nextspell != "":
                    curr = curr.nextspell
                    continue
                # this does currently not work on chain lightning effects (134)
                if curr.effect % 1000 not in utils.DAMAGING_EFFECTS or curr.effect % 1000 == 134:
                    DebugLogger.debuglog(
                        f"Secondary is invalid: is ondamage secondary, spell effect chain lightning or nondamaging",
                        debugkeys.SECONDARYEFFECTCOMPATIBILITY)
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
                DebugLogger.debuglog(f"Secondary is invalid: finalaoe {finalaoe} below specified min of {self.minfinalaoe}",
                                     debugkeys.SECONDARYEFFECTCOMPATIBILITY)
                return False

        DebugLogger.debuglog(f"Secondary is valid!",
                             debugkeys.SECONDARYEFFECTCOMPATIBILITY)
        return True
    def apply(self, spelleffect, s, mod, **options):
        "Return True on success, False on failure"
        setparams = options.get("setparams", None)
        costedAGemBeforeSecondary = s.fatiguecost >= 100

        for attrib, val in self.setcommands:
            print(f"secondary: Set spell {attrib} to {val}")
            setattr(s, attrib, val)

        for attrib, val in self.multcommands:
            # Commanders should not get the full mult for these
            if attrib == "fatiguecost" and spelleffect.chassisvalue is not None:
                print(
                    f"magicvalpercent {spelleffect.magicvaluepercent}, magicpathvaluescaling {self.magicpathvaluescaling},"
                    f" chassisvaluepercent {spelleffect.chassisvaluepercent}")
                magiccostmod = spelleffect.magicvaluepercent * s.fatiguecost * self.magicpathvaluescaling * (val - 1.0)
                chassiscostmod = spelleffect.chassisvaluepercent * s.fatiguecost * (val - 1.0)
                newval = int(
                    s.fatiguecost * (spelleffect.magicvaluepercent + spelleffect.chassisvaluepercent) + magiccostmod + chassiscostmod)
                print(
                    f"secondary.magicpathvaluescaling = {self.magicpathvaluescaling}: "
                    f"base magic: {spelleffect.magicvalue}, magic mod: {magiccostmod}, base chassis: "
                    f"{spelleffect.chassisvalue}, chassis mod: {chassiscostmod}, final={newval}, "
                    f"effectfatigue={spelleffect.fatiguecost}, oldspellfatigue={s.fatiguecost}")
            else:
                newval = int(getattr(s, attrib) * val)
                print(f"secondary: Mult: spell {attrib} by {val} to {newval}")
            setattr(s, attrib, newval)

        unitmodApplied = False
        # Apply secondary to the spell
        for param in self.params:
            if param == "unitmod":
                paramv = getattr(self, param)
                if paramv is not None and paramv != "":
                    realunitmod = utils.unitmods[paramv]
                    actualpowerlvl = spelleffect.calcActualpowerlvl(mod, self)
                    unitmoddata = realunitmod.apply(spelleffect, s, actualpowerlvl=actualpowerlvl, secondaryeffect=self)
                    if unitmoddata is None:
                        print(f"Failed to generate {spelleffect.name}: unit mod failed to apply")
                        return False
                    s.modcmdsbefore += unitmoddata
                    unitmodApplied = True
                    continue

            if hasattr(s, param):
                print(f"secondary: processing +param {param}")
                # Nextspell is weird because additions do not play nice
                # I suppose I could define __add__ or whatever for Spell objects that allows you to just to do this with the same logic
                # but that would be VERY counterintuitive and hard to follow
                if param == "nextspell":
                    if self.nextspell != "":
                        # We'll be walking along the nextspell chains and adding the effect to the end of that
                        tmp = s
                        while 1:
                            if isinstance(tmp.nextspell, Spell):
                                tmp = tmp.nextspell
                            else:
                                optionscopy = copy.copy(options)
                                optionscopy["isnextspell"] = True
                                optionscopy["forcepath"] = s.path1
                                optionscopy["blockmodifier"] = True
                                tmp.nextspell = utils.spelleffects[self.nextspell].rollSpell(**optionscopy)
                                if tmp.nextspell is None:
                                    print("ERROR: failed to generate nextspell")
                                    return False
                                # Copy certain targeting spec values
                                # 8 - demons/undead only
                                # 16 - magic beings only
                                # 32768 - sacreds only
                                # 131072 - not mindless
                                # 524288 - not undead
                                # 268435456 - not demons
                                # 536870912 - not inanimate
                                spectocopy = tmp.spec & 0x300a8018
                                tmp.nextspell.spec |= spectocopy
                                print(f"Copied target type checking spec values: {spectocopy} to new nextspell")
                                print(f"set nextspell to {tmp.nextspell.name}")
                                break
                elif param == "aispellmod":
                    s.multiplyAISpellMod(1 + (getattr(self, param) / 100))
                else:
                    setattr(s, param, getattr(s, param) + getattr(self, param))

        # Things that costed a gem before the secondary applied should still cost gems after, scale params appropriately
        if costedAGemBeforeSecondary and s.fatiguecost < 100:
            print("Spell is now too cheap, before the secondary it cost a gem and now it doesn't")
            spelleffect.scaleSpellEffectsToFatigue(s, 100)

        prev = s
        next = s.nextspell
        realaoe = (s.path1level * s.aoe // 1000) + s.aoe % 1000
        # Find the penultimate nextspell
        if next != "" and next is not None:
            while 1:
                realaoe = max(realaoe, (s.path1level * next.aoe // 1000) + next.aoe % 1000)
                if next.nextspell != "" and next.nextspell is not None:
                    prev = next
                    next = next.nextspell
                else:
                    break

        if self.ondamage:
            prev.spec += 0x1000000000000000
            print(f"Added on damage spec to penultimate nextspell {prev.name}")

        # Don't add fatigue to holy spells
        if self.fatiguepersquare > 0 and spelleffect.paths != 256:
            realaoe = min(50, realaoe)
            additionalfatigue = realaoe * self.fatiguepersquare
            s.fatiguecost += additionalfatigue
            print(f"Added {additionalfatigue} fatigue for +{self.fatiguepersquare} per square ({realaoe} squares)")

        # If the above did not apply a unitmod and we are using a new unit, it needs to be forced
        # or nothing else will write the mod commands for the new unit
        if not unitmodApplied and spelleffect.newunit is not None:
            s.modcmdsbefore += utils.unitmods["Do Nothing"].apply(spelleffect, s)
        return True