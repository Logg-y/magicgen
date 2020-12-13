import copy
import math
import random

import naming
from . import utils
from .utils import SpellTypes, PathFlags, SchoolFlags

# This seems to be how dominions autocalcs cast time
# keys are simply gems required
# 9 is a guess as I couldn't be bothered to mod a spell in for what seemed like an obvious progression
casttimes = {0: 100, 1: 125, 2: 175, 3: 200, 4: 225, 5: 250, 6: 275, 7: 300, 8: 325, 9: 350}


class Spell(object):
    def __init__(self):
        self.name = ""
        self.effect = -1
        self.damage = -1
        self.spec = 0
        self.school = -1
        self.aoe = 0
        self.range = 0
        self.nreff = 1
        self.precision = 0
        self.path1 = -1
        self.path2 = -1
        self.path1level = -1
        self.path2level = -1
        self.fatiguecost = 0
        self.researchlevel = -1
        self.nextspell = ""
        self.details = None
        self.name = "Unnamed"
        self.descr = "This spelleffect and path combination was given no descr!"
        self.flightspr = None
        self.explspr = None
        self.sound = None
        self.maxbounces = 0
        self.nolandtrace = 0
        self.onlyfriendlydst = 0
        self.onlygeosrc = 0
        self.copyspell = None
        self.casttime = None
        self.provrange = None
        self.onlygeodst = None
        self.nogeodst = None
        self.godpathspell = None
        self.comments = []
        self.modcmdsbefore = ""
        self.restricted = None
        self.aicastmod = 0
        self.isnextspell = False
        self.parenteffect = None

    def p(self):
        print(f"name {self.name}")
        print(f"effect {self.effect}")
        print(f"damage {self.damage}")
        print(f"spec {self.spec}")
        print(f"school {self.school}")
        print(f"aoe {self.aoe}")
        print(f"nreff {self.nreff}")
        print(f"path1level {self.path1level}")
        print(f"path1 {self.path1}")
        print(f"fatiguecost {self.fatiguecost}")
        print("\n" * 3)

    def output(self):
        # self.p()
        debugmode = False
        if debugmode:
            self.name = self.name + " {}".format(self.researchlevel)
            self.researchlevel = min(0, self.researchlevel)
        out = ""

        for comment in self.comments:
            out += f"-- {comment}\n"

        out += self.modcmdsbefore

        # this spec is "next effect on damage" which ALWAYS calls the next spell id and not the thing you ask for
        if self.nextspell != "" and self.nextspell is not None and not (self.spec & 1152921504606846976):
            out += self.nextspell.output()

        # They MUST have consecutive IDs
        # because of the way I generate them they are normally backwards
        # so this swaps them back round the right way
        if self.nextspell != "" and self.nextspell is not None and (self.spec & 1152921504606846976):
            firstid = copy.copy(self.nextspell.id)
            myid = copy.copy(self.id)
            self.id = firstid
            self.nextspell.id = myid

        out += f"#newspell {self.id}\n"
        if self.copyspell is not None:
            out += '#copyspell "{}"{}'.format(self.copyspell, "\n")
        out += "#name \"" + self.name + "\"\n"
        out += f"#effect {self.effect}\n"
        out += f"#damage {self.damage}\n"
        out += f"#spec {self.spec}\n"
        if self.school > -1:
            out += f"#school {int(math.log(self.school, 2))}\n"
        else:
            out += "#school -1\n"
        out += f"#aoe {self.aoe}\n"
        out += f"#range {self.range}\n"
        out += f"#nreff {self.nreff}\n"
        out += f"#precision {self.precision}\n"
        out += '#descr "{}"{}'.format(self.descr.strip(), "\n")
        out += '#path 0 {}{}'.format(int(math.log(self.path1, 2)), "\n")
        out += f"#researchlevel {self.researchlevel}\n"
        out += f"#pathlevel 0 {self.path1level}\n"
        if self.path2 != -1 and self.path2level > -1:
            out += f"#path 1 {int(math.log(self.path2, 2))}\n"
            out += f"#pathlevel 1 {self.path2level}\n"
        else:
            out += "#path 1 -1\n"
            out += "#pathlevel 1 0\n"
        out += f"#fatiguecost {self.fatiguecost}\n"
        if self.details is not None and len(self.details) > 0:
            out += '#details "{}"{}'.format(self.details.strip(), "\n")
        if self.nextspell != "" and self.nextspell is not None and not (self.spec & 1152921504606846976):
            out += '#nextspell "{}"{}'.format(self.nextspell.name, "\n")
        if self.flightspr is not None:
            out += f"#flightspr {self.flightspr}\n"
        if self.explspr is not None:
            out += f"#explspr {self.explspr}\n"
        if self.maxbounces > 0:
            out += f"#maxbounces {self.maxbounces}\n"
        if self.sound is not None:
            out += f"#sound {self.sound}\n"
        if self.casttime is not None:
            out += f"#casttime {self.casttime}\n"
        if self.provrange is not None:
            out += f"#provrange {self.provrange}\n"
        if self.onlygeodst is not None:
            out += f"#onlygeodst {self.onlygeodst}\n"
        if self.nogeodst is not None:
            out += f"#nogeodst {self.nogeodst}\n"
        if self.ainocast > 0:
            out += f"#ainocast {self.ainocast}\n"
        if self.nolandtrace > 0:
            out += f"#nolandtrace {self.nolandtrace}\n"
        if self.onlyfriendlydst > 0:
            out += f"#onlyfriendlydst {self.onlyfriendlydst}\n"
        if self.onlygeosrc > 0:
            out += f"#onlygeosrc {self.onlygeosrc}\n"
        if self.godpathspell is not None:
            out += f"#godpathspell {self.godpathspell}\n"
        if self.restricted is not None:
            out += f"#restricted {self.restricted}\n"
        if self.aicastmod != 0:
            out += f"#aicastmod {self.aicastmod}\n"
        out += "#end\n\n"

        if self.nextspell != "" and self.nextspell is not None and (self.spec & 1152921504606846976):
            out += self.nextspell.output()
        return out


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
		allowskipchance: if False, skipchances of any value less than 100 (IE: 100% skip) will be ignored
		setparams: a dict of params to set on the created Spell object
		
		secondarychance: int of % chance to roll a secondary effect
		summonsecondarychance: int of % chance to roll a secondary effect on a summoning spell
		"""

        if isnextspell:
            print(f"Starting nextspell: {self.name}")

        if random.random() * 100 < self.skipchance and not isnextspell and (allowskipchance or self.skipchance >= 100):
            print(f"Failed to generate {self.name} at {researchlevel}: random skipchance")
            return None

        if self.effect < 10000 and allowskipchance and forcepath == 128 and not isnextspell:
            # Gimme less combat blood spells
            if random.random() < 0.75:
                print(f"Failed as 75% to have less blood combat spells")
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

        while 1:
            s.path1 = utils._selectFlag(PathFlags, self.paths)
            if s.path1 == 128 and not allowblood:
                continue
            if random.random() * 100 <= self.pathskipchances.get(s.path1, 0):
                continue
            break

        if forcepath is not None:
            print(f"Forced path to {forcepath}")
            s.path1 = forcepath

        s.path1level = self.pathlevel + mod.pathlevel + secondary.pathlevel
        if forcepathlevel is not None:
            print(f"Calced path level was {s.path1level}, using override {forcepathlevel} instead")
            s.path1level = forcepathlevel
        # modifier fatigue cost is added later
        s.fatiguecost = self.fatiguecost

        scaleamt = 1

        # only do this if there is something to scale
        if self.spelltype & SpellTypes.POWER_SCALES_AOE or self.spelltype & SpellTypes.POWER_SCALES_DAMAGE or self.spelltype & SpellTypes.POWER_SCALES_NREFF or self.spelltype & SpellTypes.POWER_SCALES_MAXBOUNCES or self.spelltype & SpellTypes.POWER_SCALES_EFFECTNO:
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
                            if s.details is None: s.details = ""
                            s.details += "\nThis spell strikes 100% of the battlefield."
                        elif tmp >= 100:
                            s.aoe = 663
                            if s.details is None: s.details = ""
                            s.details += "\nThis spell strikes 50% of the battlefield."
                        elif tmp >= 80:
                            s.aoe = 665
                            if s.details is None: s.details = ""
                            s.details += "\nThis spell strikes 25% of the battlefield."

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

            scaleamt *= self.scalecost
            print(f"scaleamt now {scaleamt} after being multiplied by scalecost {self.scalecost}")
            if scaleamt > 0:
                scaleamt += 1  # otherwise the case where scaleamt = 1 yields no fatigue increase!

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

            s.fatiguecost += scaleamt * self.scalefatiguemult
            print(f"Fatiguemult: Added {scaleamt * self.scalefatiguemult} to fatigue cost, it is now {s.fatiguecost}")

            scaleexponent = (mod.scalefatigueexponent + self.scalefatigueexponent + secondary.scalefatigueexponent)
            if scaleamt != 0.0 and scaleexponent > 0.0:
                s.fatiguecost += (scaleamt ** scaleexponent)
                print(f"Exponent: Added {scaleamt ** scaleexponent} (exponent is {scaleexponent}) to fatigue cost, it is now {s.fatiguecost}")

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

        # scaling fatiguecost per effect
        flatnumeffects = s.nreff % 1000
        scalenumeffects = s.nreff // 1000
        realnumeffects = (scalenumeffects * s.path1level) + flatnumeffects
        s.fatiguecost += (realnumeffects * secondary.fatiguecostpereffect)

        # don't make spells uncastable at the minimum level
        if not self.spelltype & SpellTypes.RITUAL:
            if s.fatiguecost > 100 * s.path1level:
                s.comments.append(f"Reduced fatigue cost from {s.fatiguecost} to make it actually castable")
                s.fatiguecost = min(s.fatiguecost, 100 * s.path1level)

        plural = True if (s.aoe > 0 or s.nreff > 1) else False
        if self.spelltype & SpellTypes.EVOCATION:
            plural = True if (s.aoe > 1 or s.nreff > 1) else False

        
        # See if the secondary effect we took has a path requirement that we fail to meet
        if secondary.paths > 0:
            if not (secondary.paths & s.path1):
                s.path2 = utils._selectFlag(PathFlags, secondary.paths)
                print(f"Forced to take offpath {s.path2} due to secondary effect")
                # to be able to have an offpath the path requirement needs to be shifted to 2
                if s.path1level <= 1:
                    s.path1level = max(2, s.path1level)
                    # this is about all that can be done to compensate
                    if s.fatiguecost != 100:  # don't go from 1 gem to 0 gems
                        s.fatiguecost /= 2

        # Consider splitting paths
        if random.random() * 100 < self.secondarypathchance and s.path2 < 0:
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
            s.casttime = casttimes.get(int(s.fatiguecost / 100), 100)

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
                magiccostmod = self.magicvaluepercent * s.fatiguecost * secondary.magicpathvaluescaling * val
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
            s.sound = 32  # this is the blood spell sound that they ALL get

            # assume that blood rituals with non-blood primary path possibilities have numbers balanced for
            # gems and not slaves so multiply by 2
            if s.effect > 10000:
                if self.paths != 128:
                    s.fatiguecost *= 2

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
            descrs.append(self.descriptions.get(s.path1, "This spell and path combination have no description!"))

        # write a description
        s.descr = naming.parsestring(random.choice(descrs), plural=plural, aoe=s.aoe, spelltype=self.spelltype, spell=s)

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

        s.details = s.details.replace("EFFECTNUMBER_ADDITIVE", str((s.effect % 1000) - 599))

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
                                     f"with forcesecondaryeff {forcesecondaryeff} - this probably this holy effect"
                                     f" starts with a nextspell and ambiguous secondary paths. To fix"
                                     f" make secondary path for this effect NOT a compound of multiiple paths ")

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
            while 1:
                try:
                    name = names.pop(random.randint(0, len(names) - 1))
                    if secondary.unitmod != "":
                        um = utils.unitmods[secondary.unitmod]
                        name = name.replace("NAMEPREFIX", um.nameprefix)
                    name = name.replace("NAMEPREFIX", "")

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

        s.fatiguecost += options.get("fatiguemodflat", 0)
        s.fatiguecost *= options.get("fatiguemodmult", 1.0)
        s.fatiguecost = math.floor(s.fatiguecost)
        s.fatiguecost = max(0, s.fatiguecost)

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

        return s
