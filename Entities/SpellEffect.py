import math
import random

from Entities.spell import Spell
from Entities import spell
from Enums.PathFlags import PathFlags
from Enums.SchoolFlags import SchoolFlags
from Enums.SpellTypes import SpellTypes
from Services import utils, naming


# Prevent generation of more than this many effects in a single path that add to permanent slot usage
PERMANENT_SPELL_EFFECT_LIMIT_BY_PATH = 2

class SpellEffect(object):
    def __init__(self, fp):
        self.fp = fp
        self.name = None
        self.effect = -1
        self.damage = -1
        self.spec = 0
        self.schools = None
        self.spelltype = -1
        self.aoe = 0
        self.power = 1
        self.extraspell = ""
        self.nextspell = ""
        self.skipchance = 0
        self.scalerate = 0
        self.range = 0
        self.nreff = 1
        self.precision = 0
        self.pathlevel = 0
        self.fatiguecost = 0
        self.flightspr = -1
        self.explspr = None
        self.sound = None
        self.scalecost = 1.0
        self.paths = 0
        self.secondarypaths = 0
        self.descriptions = {}
        self.names = {}
        self.nameconds = {}
        self.descrconds = {}
        self.details = ""
        self.maxpower = 9
        self.maxbounces = 0
        self.chassisvalue = None
        self.copyspell = None
        self.pathperresearch = 0.66
        self.scalefatigueexponent = 1.6
        self.casttime = None
        self.provrange = None
        self.secondarypathchance = 10
        self.scalefatiguemult = 0.0
        self.nogeodst = None
        self.onlygeodst = None
        self.skipflightspr = 0
        self.skipexplspr = 0
        self.ainocast = 0
        self.nolandtrace = 0
        self.onlyfriendlydst = 0
        self.onlygeosrc = 0
        self.unique = 0
        self.generated = 0
        self.alwaysgenerate = 0
        self.donotsetextraspellpath = 0
        self.aicastmod = 0
        self.pathskipchances = {}
        self.banishment = 0
        self.smite = 0
        self.eventset = None
        self.noadditionalnextspells = 0
        self.basescale = 0
        self.secondaryeffectskipchance = 0
        self.permanentslotusage = 0

    def __repr__(self):
        return f"SpellEffect({self.name})"

    def rollSpell(self, researchlevel, forceschool=None, forcepath=None, isnextspell=False, forcesecondaryeff=None,
                  blockmodifier=False, blocksecondary=False, allowblood=True, allowskipchance=True, setparams=None,
                  forcedmodifier=None, forcepathlevel=None, **options):
        """Return a Spell on success, or None if it couldn't be done.

		researchlevel: the research level this spell should be for
		forceschool: the generated spell will be forced into a research school
		forcepath: the primary path will be forced into the given value
		forcepathlevel: the pathlevel to force
		isnextspell: internal, used to know if it's generating a nextspell
		forcesecondaryeff: always give the spell a secondary effect from one of the passed path flags
		blockmodifier: if True, only "Do Nothing" is allowed as a modifier (for holy spells)
		blocksecondary: if True, only "Do Nothing" is allowed as a secondary effect
		allowblood: if True, can assign blood paths and to the blood school
		allowskipchance: if False, skipchances of any value less than 100 (IE: 100% skip) will be ignored. Blood combat spell skipping bypasses this
		setparams: a dict of params to set on the created Spell object

		secondarychance: int of % chance to roll a secondary effect
		summonsecondarychance: int of % chance to roll a secondary effect on a summoning spell
		"""
        if setparams is None:
            isnational = False
        else:
            isnational = "restricted" in setparams

        if isnational and self.permanentslotusage:
            print(f"Fail {self.name} as this is a national generation and the effect wants to fill permanent slots")
            return None

        if isnextspell:
            print(f"Starting nextspell: {self.name}")

        if random.random() * 100 < self.skipchance and not isnextspell and (allowskipchance or self.skipchance >= 100):
            print(f"Failed to generate {self.name} at {researchlevel}: random skipchance")
            return None

        # bypasses allowskipchance
        if self.effect < 10000 and forcepath == 128 and not isnextspell:
            # Gimme less combat blood spells
            if random.random() < 0.85:
                print(f"Failed as 85% to have less blood combat spells")
                return None
            # Even less likely if they have other primary paths
            if self.paths != 128 and random.random() < 0.95:
                print(f"Failed as 95% to fail other path combat spells")
                return None

        if self.unique and self.generated > 0:
            print(f"Failed to generate {self.name} at {researchlevel}: effect is unique and already exists")
            return None

        if isinstance(self.nextspell, str) and len(self.nextspell) > 0:
            self.nextspell = utils.spelleffects[self.nextspell]

        # Don't make lots of generations from the same effect
        if allowskipchance and not isnextspell and self.generated > 0:
            tot = 0
            for x in range(0, self.generated):
                tot += (x + 1) * 8
            tot = min(98, tot)
            if random.random() * 100 < tot:
                print(f"Skipped based on {self.generated} previous generations")
                return None

        if forceschool and not (self.schools & forceschool):
            print(
                f"Failed to generate {self.name} at {researchlevel}: school is forced to {forceschool} which is incompatible")
            return None

        # path -1 means nextspells, and they can't be cast normally
        # so don't generate them if we aren't a next spell or have a forced path for some other reason
        if self.paths == -1 and not forcepath:
            print(f"Failed to generate {self.name} at {researchlevel}: spell has no paths")
            return None

        if self.schools == -1 and not isnextspell:
            # nextspells go in the unresearchable school!
            print(f"{self.name} is unresearchable and not next spell, fail this generation")
            return None

        self.isnextspell = isnextspell

        # Setting this on self allows modifiers to check against it
        self.researchlevel = researchlevel
        # Convenience for modifiers: set values equal to our nonscaling attributes
        for x in ["aoe", "damage", "range"]:
            setattr(self, f"nonscaling{x}", getattr(self, x) % 1000)

        s = Spell()

        # Roll a modifier.
        mod = None
        if blockmodifier:
            mod = utils.modifiers["Do Nothing"]
        elif forcedmodifier is not None:
            mod = forcedmodifier
        else:
            modlist = list(utils.modifiers.keys())
            random.shuffle(modlist)
            mod = None
            while mod is None:
                m = utils.modifiers[modlist.pop(0)]
                if m.compatibility(self, researchlevel, isnextspell):
                    if random.random() * 100 < m.skipchance:
                        modlist.append(m.name)
                    else:
                        print(f"Using mod {m.name} for {self.name}")
                        mod = m
                        break
                if len(modlist) == 0:
                    print(f"No valid modifiers for {self.name} at research {researchlevel}")
                    raise Exception(f"No valid modifiers for {self.name} at research {researchlevel}")

                    raise ValueError(f"No valid modifiers for {self.name}")
        secondarylist = list(utils.secondaries.keys())
        random.shuffle(secondarylist)
        secondary = None

        # use summonsecondarychance if this is a summoning spell
        if self.effect in [1, 10001, 10050, 10038, 21, 10021]:
            options["secondarychance"] = options.get("summonsecondarychance", 50)

        if blocksecondary:
            secondary = utils.secondaries["Do Nothing"]
        elif forcesecondaryeff is None and random.random() * 100 >= options.get("secondarychance", 20):
            print(f"Failed secondary effect chance of {options.get('secondarychance', 20)}")
            secondary = utils.secondaries["Do Nothing"]
        elif forcesecondaryeff is None and random.random() * 100 <= self.secondaryeffectskipchance:
            print(f"Secondary effect skipchance of {self.secondaryeffectskipchance}")
            secondary = utils.secondaries["Do Nothing"]
        else:
            while secondary is None:
                toconsider = utils.secondaries[secondarylist.pop(0)]
                if toconsider.compatibility(self, mod, researchlevel):
                    if forcesecondaryeff is None:
                        if random.random() * 100 < toconsider.skipchance:
                            secondarylist.append(toconsider.name)
                        else:
                            secondary = toconsider
                            break
                    else:
                        # Make sure its path matches what was asked for
                        if toconsider.paths & forcesecondaryeff:
                            # ignore skipchance for this
                            print(f"Using secondary {toconsider.name}")
                            secondary = toconsider
                            break
                        else:
                            print("Bad paths for forced secondary")
                if len(secondarylist) == 0:
                    print(f"Failed to generate {self.name} at {researchlevel}: no valid secondaries")
                    return None

        print(f"using secondary {secondary.name} for {self.name} with mod {mod.name}")

        # Holy spells need to escape this
        # Also, Nextspells without a scale rate should still be allowed
        if researchlevel + mod.power + secondary.power < self.power and self.paths != 256 and not (
                isnextspell and self.scalerate == 0):
            print(f"Failed to generate {self.name} at {researchlevel}: final power level too low")
            return None

        if researchlevel + mod.power + secondary.power > self.maxpower and self.paths != 256 and not (
                isnextspell and self.scalerate == 0):
            print(f"Failed to generate {self.name} at {researchlevel}: final power level too high")
            return None

        s.name = self.name + " " + str(random.randint(-9999, 9999))
        s.effect = self.effect
        s.damage = self.damage
        s.range = self.range
        s.nreff = self.nreff
        s.precision = self.precision
        s.aoe = self.aoe
        s.spec = self.spec
        s.details = self.details
        s.researchlevel = researchlevel
        s.flightspr = self.flightspr
        s.explspr = self.explspr
        s.sound = self.sound
        s.maxbounces = self.maxbounces
        s.provrange = self.provrange
        s.nogeodst = self.nogeodst
        s.onlygeodst = self.onlygeodst
        s.ainocast = self.ainocast
        s.onlyfriendlydst = self.onlyfriendlydst
        s.nolandtrace = self.nolandtrace
        s.onlygeosrc = self.onlygeosrc
        s.aicastmod = self.aicastmod
        s.parenteffect = self
        if s.details is None:
            s.details = ""
        if self.isnextspell:
            s.isnextspell = True

        if setparams is not None:
            for key, val in setparams.items():
                setattr(s, key, val)

        self.magicvalue = 0.0
        if self.chassisvalue is not None:
            self.magicvalue = self.fatiguecost - self.chassisvalue
            self.magicvaluepercent = self.magicvalue / self.fatiguecost
            self.chassisvaluepercent = self.chassisvalue / self.fatiguecost
            if self.magicvalue < 0.0:
                raise ValueError(
                    f"Can't have a negative (fatiguecost-chassisvalue) of {self.magicvalue} for {self.name}")

        if self.copyspell is not None:
            s.copyspell = self.copyspell
        if self.casttime is not None:
            s.casttime = self.casttime

        if self.paths == 0:
            self.paths = 255  # NOT HOLY unless otherwise stated
        if self.schools is None:
            self.schools = 127  # NOT HOLY

        if self.schools > -1:
            s.school = utils._selectFlag(SchoolFlags, self.schools)
            if forceschool is not None:
                s.school = forceschool
        else:
            s.school = -1

        # Guard against infinites if blood is the only legal option and we aren't allowed it
        if self.paths == 128 and not allowblood and not isnextspell:
            print(f"Failed to generate {self.name} at {researchlevel}: blood guard against infinite loop")
            return None

        possibleillwinterpaths = utils.breakdownflag(511 & self.paths)
        random.shuffle(possibleillwinterpaths)
        print(f"Possible path with illwinter ids are {possibleillwinterpaths}")

        if forcepath is None:
            while 1:
                if len(possibleillwinterpaths) == 0:
                    print(f"Failed to generate: no valid paths")
                    return None
                s.path1 = 2**possibleillwinterpaths.pop(0)
                if s.path1 == 128 and not allowblood:
                    continue
                if random.random() * 100 <= self.pathskipchances.get(s.path1, 0) and len(possibleillwinterpaths) > 0:
                    possibleillwinterpaths.append(s.path1)
                    continue
                # Effects taking permanent slots need to be limited in number to avoid mechanic abuse
                if self.permanentslotusage \
                        and utils.permanent_slot_spells_by_path.get(s.path1, 0) >= PERMANENT_SPELL_EFFECT_LIMIT_BY_PATH:
                    print(f"Path {s.path1} not allowed due to permanent slot taking spell limit")
                    continue
                print(f"Accepting path {s.path1}")
                break

        if forcepath is not None:
            if allowskipchance and random.random() * 100 <= self.pathskipchances.get(forcepath, 0):
                print(f"Forced path was {forcepath}, failed this pathskipchance")
                return None
            if self.permanentslotusage \
                    and utils.permanent_slot_spells_by_path.get(forcepath, 0) >= PERMANENT_SPELL_EFFECT_LIMIT_BY_PATH:
                print(f"Attempted to forcepath into a path that has too many permanent spell effects")
                return None
            print(f"Forced path to {forcepath}")
            s.path1 = forcepath

        s.path1level = self.pathlevel + mod.pathlevel + secondary.pathlevel
        if forcepathlevel is not None:
            print(f"Calced path level was {s.path1level}, using override {forcepathlevel} instead")
            s.path1level = forcepathlevel
        # modifier fatigue cost is added later
        s.fatiguecost = self.fatiguecost

        scaleamt = 1

        # See if the secondary effect we took has a path requirement that we fail to meet
        # (decide on offpath here if there will be one!)
        if secondary.paths > 0:
            if not (secondary.paths & s.path1):
                s.path2 = utils._selectFlag(PathFlags, secondary.paths)
                print(f"Forced to take offpath {s.path2} due to secondary effect")

        # Chance to roll a secondary path (if the secondary effect we picked doesn't demand one)
        if random.random() * 100 < self.secondarypathchance and s.path2 < 0 and forcesecondaryeff is None:
            if self.secondarypaths > 0 and s.path1level >= 2 and self.secondarypaths != s.path1:
                p = self.secondarypaths
                if p & s.path1:
                    p -= s.path1
                if p > 0:
                    while 1:
                        s.path2 = utils._selectFlag(PathFlags, p)
                        if s.path2 != s.path1:
                            if random.random() * 100 > self.pathskipchances.get(s.path2, 0):
                                break

        # only do this if there is something to scale
        if self.spelltype & SpellTypes.POWER_SCALES_AOE or self.spelltype & SpellTypes.POWER_SCALES_DAMAGE or \
                self.spelltype & SpellTypes.POWER_SCALES_NREFF or self.spelltype & SpellTypes.POWER_SCALES_MAXBOUNCES \
                or self.spelltype & SpellTypes.POWER_SCALES_EFFECTNO or self.eventset is not None:
            actualpowerlvl = (researchlevel - self.power) + mod.power + secondary.power

            scaleamt = 0
            for x in range(0, actualpowerlvl):
                scaleamt += (x + 1) * (mod.scalerate + self.scalerate + secondary.scalerate)
            scaleamt = math.ceil(scaleamt)

            # scale the thing
            if self.spelltype & SpellTypes.POWER_SCALES_AOE:
                s.aoe += scaleamt

                # Do I make it battlefield wide?
                if self.spelltype & SpellTypes.BUFF and self.spelltype & SpellTypes.ALLOW_BATTLEFIELD and not mod.nobattlefield and not secondary.nobattlefield:
                    tmp = s.aoe % 1000
                    if tmp > 25:
                        s.aoe = 666
                        # make it friendly only
                        if not self.spec & 4194304:
                            s.spec |= 4194304
                elif self.spelltype & SpellTypes.BUFF:
                    pass

                elif self.spelltype & SpellTypes.EVOCATION:
                    tmp = s.aoe % 1000
                    if self.spelltype & SpellTypes.ALLOW_BATTLEFIELD and not mod.nobattlefield and not secondary.nobattlefield:
                        tmp = s.aoe % 1000
                        if tmp >= 120:
                            s.aoe = 666
                        elif tmp >= 100:
                            s.aoe = 663
                        elif tmp >= 80:
                            s.aoe = 665

            if self.spelltype & SpellTypes.POWER_SCALES_DAMAGE:
                print(f"scale damage by {scaleamt}")
                s.damage += scaleamt
            if self.spelltype & SpellTypes.POWER_SCALES_NREFF:
                print(f"scale nreff by {scaleamt}")
                s.nreff += scaleamt
            if self.spelltype & SpellTypes.POWER_SCALES_MAXBOUNCES:
                print(f"scale maxbounces by {scaleamt}")
                s.maxbounces += scaleamt
            if self.spelltype & SpellTypes.POWER_SCALES_EFFECTNO:
                print(f"scale effect number by {scaleamt}")
                s.effect += scaleamt

            # Event set wants the scaleamt before it is messed with
            if self.eventset is not None:
                realeventset = utils.eventsets[self.eventset]
                eventsetcmds = realeventset.formatdata(self, s, scaleamt, secondary, actualpowerlvl)
                if eventsetcmds is None:
                    return None
                s.modcmdsbefore = eventsetcmds + "\n\n" + s.modcmdsbefore

            scaleamt2 = scaleamt * self.scalecost
            print(f"scaleamt now {scaleamt2} after being multiplied by scalecost {self.scalecost}")
            if scaleamt2 > 0:
                scaleamt2 += 1  # otherwise the case where scaleamt = 1 yields no fatigue increase!

            print(
                f"Scaling path calc is {mod.pathperresearch + self.pathperresearch + secondary.pathperresearch} * {actualpowerlvl}")
            print(
                f"Scaling path level modification is {math.floor((mod.pathperresearch + self.pathperresearch + secondary.pathperresearch) * actualpowerlvl)}")
            s.path1level += math.floor(
                (mod.pathperresearch + self.pathperresearch + secondary.pathperresearch) * actualpowerlvl)

            s.path1level += options.get("pathlevelmodflat", 0)
            s.path1level *= options.get("pathlevelmodmult", 1.0)
            s.path1level = max(1, s.path1level)
            s.path1level = math.floor(s.path1level)

            s.fatiguecost += 10 * actualpowerlvl
            print(f"Power level: Added {10 * actualpowerlvl} to fatigue cost, it is now {s.fatiguecost}")

            s.fatiguecost += scaleamt2 * self.scalefatiguemult
            print(f"Fatiguemult: Added {scaleamt2 * self.scalefatiguemult} to fatigue cost, it is now {s.fatiguecost}")

            scaleexponent = (mod.scalefatigueexponent + self.scalefatigueexponent + secondary.scalefatigueexponent)
            if scaleamt2 != 0.0 and scaleexponent > 0.0:
                s.fatiguecost += (scaleamt2 ** scaleexponent)
                print(
                    f"Exponent: Added {scaleamt2 ** scaleexponent} (exponent is {scaleexponent}) to fatigue cost, it is now {s.fatiguecost}")

        if self.nextspell != "":
            s.nextspell = self.nextspell.rollSpell(researchlevel + mod.power + secondary.power, forceschool=forceschool,
                                                   forcepath=s.path1, blockmodifier=True, isnextspell=True,
                                                   setparams=setparams, allowskipchance=False)
        if self.extraspell != "":
            extraspell = utils.spelleffects[self.extraspell]
            if self.donotsetextraspellpath == 0:
                s.modcmdsbefore += extraspell.rollSpell(researchlevel, forceschool=s.school, forcepath=s.path1,
                                                        isnextspell=True, blockmodifier=False, setparams=setparams,
                                                        forcedmodifier=mod, forcepathlevel=s.path1level,
                                                        allowskipchance=False, **options).output()
            else:
                s.modcmdsbefore += extraspell.rollSpell(researchlevel, forceschool=s.school, isnextspell=True,
                                                        blockmodifier=False, setparams=setparams, forcedmodifier=mod,
                                                        forcepathlevel=s.path1level, allowskipchance=False,
                                                        **options).output()

            # Remove decimal stuff
        s.nreff = math.floor(s.nreff)
        s.damage = math.floor(s.damage)
        s.maxbounces = math.floor(s.maxbounces)
        s.effect = math.floor(s.effect)

        # scaling fatiguecost per effect
        flatnumeffects = s.nreff % 1000
        scalenumeffects = s.nreff // 1000
        realnumeffects = (scalenumeffects * s.path1level) + flatnumeffects
        s.fatiguecost += (realnumeffects * secondary.fatiguecostpereffect)

        # don't make spells uncastable at the minimum level
        if not self.spelltype & SpellTypes.RITUAL:
            if s.fatiguecost > 100 * s.path1level:
                reductionfactor = (100 * s.path1level) / s.fatiguecost
                if realnumeffects > 1:
                    desirednumeffects = max(1, math.floor(realnumeffects * reductionfactor))
                    numeffectstolose = realnumeffects - desirednumeffects
                    # Take from scaling first
                    while 1:
                        # can't reduce scaling if it would drop below the number to lose
                        if numeffectstolose < s.path1level:
                            break
                        # don't reduce scaling below 1 if it existed
                        if (s.nreff // 1000) <= 1:
                            break
                        if numeffectstolose == 0:
                            break
                        s.nreff -= 1000
                        numeffectstolose -= s.path1level

                    while 1:
                        # Don't reduce the flat number of effects below 0
                        if (s.nreff % 1000) == 0:
                            break
                        if numeffectstolose == 0:
                            break
                        s.nreff -= 1
                        numeffectstolose -= 1

                    s.comments.append(f"Reduce number of effects from {realnumeffects} to fit cost "
                                      f"reduction scale of {reductionfactor}")

                s.comments.append(f"Reduced fatigue cost from {s.fatiguecost} to make it actually castable")
                s.fatiguecost = min(s.fatiguecost, 100 * s.path1level)

        plural = True if (s.aoe > 0 or s.nreff > 1) else False
        if self.spelltype & SpellTypes.EVOCATION:
            plural = True if (s.aoe > 1 or s.nreff > 1) else False

        # If we have an offpath, do offpath things
        if s.path2 > 0:
            # to be able to have an offpath the path requirement needs to be shifted to 2
            if s.path1level <= 1:
                s.path1level = max(2, s.path1level)
                # this is about all that can be done to compensate
                if 200 > s.fatiguecost >= 100:  # don't go from 1 gem to 0 gems
                    s.fatiguecost /= 2

        # Divert levels into secondary path, if applicable
        if s.path2 >= 0:
            # How many levels to divert?
            maxdivert = math.floor(s.path1level / 2)
            divert = random.randint(1, maxdivert)
            s.path2level = divert
            s.path1level -= divert
            if not self.spelltype & SpellTypes.RITUAL:
                s.fatiguecost = min(s.fatiguecost, 100 * s.path1level)

        # buffs with aoe 0 should be self only, which means setting range to 0
        if self.spelltype & SpellTypes.BUFF and s.aoe == 0:
            s.range = 0
        # Assign cast time
        if s.casttime is None:
            s.casttime = spell.casttimes.get(int(s.fatiguecost / 100), 100)

        # Reasons to try generating again:
        # if our path level has been reduced below 1 by mods
        if s.path1level < 1 and self.pathlevel > 0:
            print(f"Failed to generate, pathlevel has fallen to {s.path1level}")
            # researchlevel, forceschool=None, forcepath=None, isnextspell=False, forcesecondaryeff=None, blockmodifier=False, blocksecondary=False, allowblood=True, allowskipchance=True, setparams=None
            return self.rollSpell(researchlevel, forceschool=forceschool, forcepath=forcepath, isnextspell=isnextspell,
                                  forcesecondaryeff=forcesecondaryeff, blocksecondary=blocksecondary,
                                  allowblood=allowblood, allowskipchance=allowskipchance, setparams=setparams,
                                  forcepathlevel=forcepathlevel, forcedmodifier=forcedmodifier, **options)

        # Forced modifier overrides
        for attrib, val in mod.setcommands:
            print(f"mod: Set spell {attrib} to {val}")
            setattr(s, attrib, val)

        for attrib, val in mod.multcommands:
            newval = int(getattr(s, attrib) * val)
            print(f"mod: Mult: spell {attrib} by {val} to {newval}")
            setattr(s, attrib, newval)

        # Apply modifier to the spell
        for param in mod.params:
            if hasattr(s, param):
                setattr(s, param, getattr(s, param) + getattr(mod, param))
                print(f"mod: Added {getattr(mod, param)} to {param}")

        for attrib, val in secondary.setcommands:
            print(f"secondary: Set spell {attrib} to {val}")
            setattr(s, attrib, val)

        for attrib, val in secondary.multcommands:
            # Commanders should not get the full mult for these
            if attrib == "fatiguecost" and self.chassisvalue is not None:
                print(
                    f"magicvalpercent {self.magicvaluepercent}, magicpathvaluescaling {secondary.magicpathvaluescaling}, chassisvaluepercent {self.chassisvaluepercent}")
                magiccostmod = self.magicvaluepercent * s.fatiguecost * secondary.magicpathvaluescaling * (val - 1.0)
                chassiscostmod = self.chassisvaluepercent * s.fatiguecost * (val - 1.0)
                newval = int(
                    s.fatiguecost * (self.magicvaluepercent + self.chassisvaluepercent) + magiccostmod + chassiscostmod)
                print(
                    f"secondary.magicpathvaluescaling = {secondary.magicpathvaluescaling}: base magic: {self.magicvalue}, magic mod: {magiccostmod}, base chassis: {self.chassisvalue}, chassis mod: {chassiscostmod}, final={newval}, effectfatigue={self.fatiguecost}, oldspellfatigue={s.fatiguecost}")
            else:
                newval = int(getattr(s, attrib) * val)
                print(f"secondary: Mult: spell {attrib} by {val} to {newval}")
            setattr(s, attrib, newval)

        # Apply secondary to the spell
        for param in secondary.params:
            if param == "unitmod":
                paramv = getattr(secondary, param)
                if paramv is not None and paramv != "":
                    realunitmod = utils.unitmods[paramv]
                    s.modcmdsbefore += realunitmod.apply(self, s)
                    continue

            if hasattr(s, param):
                print(f"secondary: processing +param {param}")
                # Nextspell is weird because additions do not play nice
                # I suppose I could define __add__ or whatever for Spell objects that allows you to just to do this with the same logic
                # but that would be VERY counterintuitive and hard to follow
                if param == "nextspell":
                    if secondary.nextspell != "":
                        # We'll be walking along the nextspell chains and adding the effect to the end of that
                        tmp = s
                        while 1:
                            if isinstance(tmp.nextspell, Spell):
                                tmp = tmp.nextspell
                            else:
                                tmp.nextspell = utils.spelleffects[secondary.nextspell].rollSpell(researchlevel,
                                                                                                  forcepath=s.path1,
                                                                                                  isnextspell=True,
                                                                                                  blockmodifier=True,
                                                                                                  setparams=setparams,
                                                                                                  **options)
                                if tmp.nextspell is None:
                                    print("ERROR: failed to generate nextspell")
                                    return None
                                print(f"set nextspell to {tmp.nextspell.name}")
                                break
                else:
                    setattr(s, param, getattr(s, param) + getattr(secondary, param))

        # make fatigue nice round numbers
        if s.fatiguecost > 100:
            s.fatiguecost = int(100 * (s.fatiguecost // 100.0))
        else:
            s.fatiguecost = int(5 * (s.fatiguecost // 5.0))

        # Blood goes in blood magic.
        # And takes slaves.
        if s.path1 == PathFlags.BLOOD and s.school != -1:
            if not (self.spelltype & SpellTypes.ALLOW_NO_SLAVE_COST):
                pass
            s.school = SchoolFlags.BLOOD
            if s.fatiguecost > 100:
                s.sound = 32  # this is the blood spell sound that they ALL get

            # assume that blood rituals with non-blood primary path possibilities have numbers balanced for
            # gems and not slaves so multiply by 2
            if s.effect > 10000:
                if self.paths != 128:
                    s.fatiguecost *= 2

        s.fatiguecost += options.get("fatiguemodflat", 0)
        s.fatiguecost *= options.get("fatiguemodmult", 1.0)
        s.fatiguecost = math.floor(s.fatiguecost)
        s.fatiguecost = max(0, s.fatiguecost)

        # Fatigue cost should not exceed 999 for non rituals
        if not (self.spelltype & SpellTypes.RITUAL):
            s.fatiguecost = min(999, s.fatiguecost)

        descrs = []
        for x in self.descrconds.get(s.path1, []):
            if x.test(s):
                # blood description changes if it doesn't require a slave to cast
                if s.fatiguecost < 100:
                    descrs.append(x.text.replace("$BLOOD_INTRO$", "$BLOOD_INTRO2$"))
                else:
                    descrs.append(x.text)

        if len(descrs) == 0:
            fallbackdescr = self.descriptions.get(s.path1, "This spell and path combination have no description!")
            if s.fatiguecost < 100:
                fallbackdescr = fallbackdescr.replace("$BLOOD_INTRO$", "$BLOOD_INTRO2$")
            descrs.append(fallbackdescr)

        # write a description
        descrchoice = random.choice(descrs)
        # Fix unit names for stuff created from events
        if self.eventset is not None:
            realeventset = utils.eventsets[self.eventset]
            if realeventset.lastunitname is not None:
                descrchoice = descrchoice.replace("CREATURE", realeventset.lastunitname)

        s.descr = naming.parsestring(descrchoice, plural=plural, aoe=s.aoe, spelltype=self.spelltype, spell=s)

        s.descr = s.descr.strip() + " "
        moddescrs = secondary.descrs[:]
        for cond in secondary.descrconds:
            if cond.test(s):
                moddescrs.append(cond.text)

        if len(moddescrs) > 0:
            s.descr += naming.parsestring(random.choice(moddescrs), plural=plural, aoe=s.aoe, spelltype=self.spelltype,
                                          spell=s)

        s.descr = s.descr.strip() + " "
        moddescrs = mod.descrs[:]
        for cond in mod.descrconds:
            if cond.test(s):
                moddescrs.append(cond.text)

        if len(moddescrs) > 0:
            s.descr += random.choice(moddescrs)

        if s.effect == 10038:
            s.details += " This spell summons EFFECTIVENREFF creatures, with an additional NREFFSCALING per additional caster level. The creatures will attack anything in the target province, including friendlies, and will then disappear."

            s.details = s.details.strip()

        s.details += " " + secondary.details

        s.descr = s.descr.strip()
        s.details = s.details.replace("\\n", "\n")
        scale = s.nreff // 1000
        base = s.nreff % 1000
        s.details = s.details.replace("EFFECTIVENREFF", str((s.path1level * scale) + base))
        s.details = s.details.replace("NREFFSCALING", str(scale))
        s.details = s.details.replace("NREFF", str(s.nreff))
        scale = s.damage // 1000
        base = s.damage % 1000
        s.details = s.details.replace("EFFECTIVEDAMAGE", str((s.path1level * scale) + base))
        s.details = s.details.replace("DAMAGESCALING", str(scale))
        s.details = s.details.replace("DAMAGE", str(s.damage))

        # for globals: use aoe to denote the base amount
        finalglobalscaling = int(self.basescale + scaleamt)
        s.details = s.details.replace("SCALEAMT", str(finalglobalscaling))

        s.details = s.details.replace("EFFECTNUMBER_5XX", str((s.effect % 1000) - 499))
        s.details = s.details.replace("EFFECTNUMBER_ADDITIVE", str((s.effect % 1000) - 599))

        if s.aoe == 666:
            s.details += " This spell strikes 100% of the battlefield."
        elif s.aoe == 663:
            s.details += " This spell strikes 50% of the battlefield."
        elif s.aoe == 665:
            s.details += " This spell strikes 25% of the battlefield."
        elif s.aoe == 664:
            s.details += " This spell strikes 10% of the battlefield."
        elif s.aoe == 662:
            s.details += " This spell strikes 5% of the battlefield."

        # take shallow copy to avoid doing bad things to later spells using the same self
        names = self.names.get(s.path1, [])[:]

        # Banishes and smites need to get a name out of their path
        if self.paths == 256:
            godpath = forcesecondaryeff
            if forcesecondaryeff is None:
                if self.secondarypaths != 0:
                    godpath = self.secondarypaths
                else:
                    raise ValueError(f"Couldn't work out god path for holy spell {self.name} passed "
                                     f"with forcesecondaryeff {forcesecondaryeff} - probably means this holy effect"
                                     f" starts with a nextspell and ambiguous secondary paths. To fix"
                                     f" make secondary path for this effect NOT a compound of multiple paths ")

            names = self.names.get(godpath, [])[:]
            # The above will have scaled holy stuff which we don't want
            # override everything for holy spells here
            s.path1level = self.pathlevel
            s.path1 = PathFlags.HOLY
            s.path2 = -1
            s.researchlevel = 0
            s.school = SchoolFlags.DIVINE
            s.godpathspell = int(math.log(godpath, 2))
            # 256 means pure holy, aka force the backup of -1 so it's used when you have no god paths >=4
            if godpath == 256:
                s.godpathspell = -1

        # see which nameconds, if any, match, and add to the name pool
        for x in self.nameconds.get(s.path1, []):
            if x.test(s):
                # print("test success")
                names.append(x.text)

        if len(names) > 0:
            print(f"Begin naming for this spell, path is {s.path1}...")
            while 1:
                try:
                    name = names.pop(random.randint(0, len(names) - 1))
                    if secondary.unitmod != "":
                        um = utils.unitmods[secondary.unitmod]
                        name = name.replace("NAMEPREFIX", um.nameprefix)
                    name = name.replace("NAMEPREFIX", "")

                    # Fix unit names for stuff created from events
                    if self.eventset is not None:
                        realeventset = utils.eventsets[self.eventset]
                        if realeventset.lastunitname is not None:
                            name = name.replace("CREATURE", realeventset.lastunitname)

                    s.name = naming.parsestring(name, plural=plural, aoe=s.aoe, spelltype=self.spelltype,
                                                titlecase=True, isspell=True, spell=s)
                    break
                except naming.NameTooLongException:
                    pass
                if len(names) == 0:
                    print("Had to give up on this spell because no names were valid")
                    return None

        s.comments.append(f"Generated with effect {self.name} at research level {researchlevel}")
        s.comments.append(f"Chosen modifier is {mod.name}")
        s.comments.append(f"Secondary effect is {secondary.name}")
        s.comments.append(f"Main spell is {s.name}")
        try:
            s.comments.append(f"Final power level was {actualpowerlvl}")
            s.comments.append(f"Scaleamt was {scaleamt}")
        except:
            pass

        if self.skipflightspr == 1:
            s.flightspr = None
        if self.skipexplspr == 1:
            s.flightspr = None

        if mod.givecloudsfx == 1:
            if s.path1 == 1:
                s.explspr = 10053
            elif s.path1 == 2:
                s.explspr = 10056
            elif s.path1 == 4:
                s.explspr = 10045
            elif s.path1 == 8:
                s.explspr = 10058
            elif s.path1 == 16:
                s.explspr = 10041
            elif s.path1 == 32:
                s.explspr = 10057
            elif s.path1 == 64:
                s.explspr = 10044
            elif s.path1 == 128:
                s.explspr = 10043

        self.generated += 1

        # Implement research level modifier options
        s.researchlevel -= options.get("researchmodifier", 0)

        # If aoe is x% of field, nextspells seem to need it too?
        if 660 < s.aoe < 670:
            tmp = s.nextspell
            while 1:
                if tmp is not None and tmp != "":
                    tmp.aoe = s.aoe
                    print(f"Set aoe for nextspell {tmp.name} to {s.aoe}")
                    tmp = tmp.nextspell
                else:
                    break

        if utils.SPELL_ID >= 4000:
            raise ValueError("Too many spells. Dominions will reject this mod.")
        # print("Too many spells. Dominions will reject this mod.")
        s.id = utils.SPELL_ID
        utils.SPELL_ID += 1

        # Sanity check: the game doesn't like spells with a path requirement of over 9 and makes them become 1 instead
        s.path1level = min(9, s.path1level)
        s.path2level = min(9, s.path2level)

        # Blood ritual cost multiplier
        if s.path1 == 128 and (s.effect > 10000 or self.spelltype & SpellTypes.RITUAL):
            s.fatiguecost = int(s.fatiguecost * options.get("bloodcostscale", 1.0))

        # Free rituals are a big fat NOPE.
        if s.effect > 10000 and s.fatiguecost < 100:
            s.fatiguecost = 100

        # Blood combat spells get more fatigue if they don't cost a slave
        if s.path1 == 128 and s.fatiguecost < 100:
            s.fatiguecost *= 2

        # Fill in placeholders in modcmdsbefore
        # This is event stuff
        s.modcmdsbefore = s.modcmdsbefore.replace("SPELLNAME", s.name)
        # the game crashes out if any details are empty strings
        s.details = s.details.strip()
        if s.details == "":
            s.details = None

        # Add to permenant slot taking spell counts if appropriate
        if self.permanentslotusage:
            utils.permanent_slot_spells_by_path[s.path1] = utils.permanent_slot_spells_by_path.get(s.path1, 0) + 1
            print(f"Path {s.path1}: num permanent slots now {utils.permanent_slot_spells_by_path.get(s.path1, 0)}")

        return s
