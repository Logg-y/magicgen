import math
import random
import copy

from Entities.spell import Spell
from Entities import spell
from Enums.PathFlags import PathFlags
from Enums.SchoolFlags import SchoolFlags
from Enums.SpellTypes import SpellTypes
from Enums.DebugKeys import debugkeys
from Services import utils, naming, DebugLogger
from fileparser import unitinbasedatafinder


# Prevent generation of more than this many effects in a single path that add to permanent slot usage
PERMANENT_SPELL_EFFECT_LIMIT_BY_PATH = 2

class SpellEffect(object):
    def __init__(self, fp=None):
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
        self.nameconds: Dict[int, Dict[int, list]] = {} # first map path id to its nameconds
        # second, map priority to its list of conds
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
        self.aispellmod = 0
        self.pathskipchances = {}
        self.banishment = 0
        self.smite = 0
        self.holyword = 0
        self.smitedemon = 0
        self.eventset = None
        self.noadditionalnextspells = 0
        self.basescale = 0
        self.secondaryeffectskipchance = 0
        self.permanentslotusage = 0
        self.hiddenench = None
        self.friendlyench = None
        self.newunit = None
        self.badaispell = 0
        self.noresearchdifferenceskip = 0
        self.siegepatrolchaff = 0
        self.fixeddurationenchantment = 0

    def __repr__(self):
        return f"SpellEffect({self.name})"

    def _initvariables(self):
        "Handles various once-and-done tasks that cannot be done during file parsing for some reason"
        # the secondary effect code expects secondarypathchance to tell the truth, set it to 0 if it isn't doing anything
        # (secondary and primary paths being the same is only a problem if they are an exact power of two
        # ie have only one path flag)
        if self.secondarypathchance > 0 and (self.secondarypaths == 0 or (
                self.paths == self.secondarypaths and math.log(self.paths, 2) % 1.0 == 0.0)):
            print(f"Set secondary path chance of {self.name} to 0 as it is useless")
            self.secondarypathchance = 0
        # Convenience for modifiers: set values equal to our nonscaling attributes
        for x in ["aoe", "damage", "range"]:
            setattr(self, f"nonscaling{x}", getattr(self, x) % 1000)

        # update nextspell to point to its SpellEffect instance
        if isinstance(self.nextspell, str) and len(self.nextspell) > 0:
            self.nextspell = utils.spelleffects[self.nextspell]

        self.calcchassisvalues()

        if self.paths == 0:
            self.paths = 255  # NOT HOLY unless otherwise stated
        if self.schools is None:
            self.schools = 127  # NOT HOLY

    def rollSpell(self, researchlevel, forceschool=None, forcepath=None, isnextspell=False, forcesecondaryeff=None,
                  blockmodifier=False, blocksecondary=False, allowblood=True, allowskipchance=True, setparams=None,
                  forcedmodifier=None, forcepathlevel=None, existingspells=None, allowedsecondarypaths=None, **options):
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
		existingspells: a dict of RL:[list of effect NAMES] that have already been made as generic spells.
		allowedsecondarypaths: if set, an integer of flags that dictates the secondary paths this spell is allowed. This is used to stop "natural" secondary paths like B/A for storm demons appearing inappropriately in national spells

		secondarychance: int of % chance to roll a secondary effect
		summonsecondarychance: int of % chance to roll a secondary effect on a summoning spell
		"""
        # Combine named args with the options dict. It's a lot tidier when passing around internal functions
        args = locals()
        options = {**options, **args}
        del options["self"]

        if setparams is None:
            options["isnational"] = False
        else:
            options["isnational"] = "restricted" in setparams

        self._initvariables()
        self.researchlevel = researchlevel
        self.isnextspell = isnextspell
        if self._shouldNotGenerate(**options):
            return None

        s = Spell()
        mod = self._rollModifier(**options)
        secondary = self._rollSecondary(mod, **options)
        if secondary is None:
            return None
        if not self._powerLevelIsValid(mod, secondary):
            return None
        self._setSpellDefaultValues(s, **options)
        s.school = self._selectSpellSchool(**options)

        # Guard against infinites if blood is the only legal option and we aren't allowed it
        if self.paths == 128 and not allowblood and not self.isnextspell:
            print(f"Failed to generate {self.name} at {researchlevel}: blood guard against infinite loop")
            return None

        if not self._selectAndApplySpellPathsAndLevels(mod, secondary, s, **options):
            return None

        actualpowerlvl = self.calcActualpowerlvl(mod, secondary)
        scaleamt = self.calcScaleamt(mod, secondary, actualpowerlvl)
        print(f"scaleamt = {scaleamt}")

        if self.spelltype & SpellTypes.RESEARCH_SCALES_AISPELLMOD:
            s.aispellmod = (actualpowerlvl + 1) * s.aispellmod

        # only do this if there is something to scale
        if self.spelltype & SpellTypes.POWER_SCALES_AOE or self.spelltype & SpellTypes.POWER_SCALES_DAMAGE or \
                self.spelltype & SpellTypes.POWER_SCALES_NREFF or self.spelltype & SpellTypes.POWER_SCALES_MAXBOUNCES \
                or self.spelltype & SpellTypes.POWER_SCALES_EFFECTNO or self.eventset is not None or self.scalerate > 0:

            if self.spelltype == -1:
                raise ValueError(f"Attempting to scale spell effect {self.name}, but no spell type is set!")

            self._scaleSpellEffectiveness(s, scaleamt, mod, secondary)
            self._scaleSpellPath1level(s, mod, secondary, **options)
            self._scaleFatigueCost(s, scaleamt, mod, secondary)

            # Have the event set generate
            if self.eventset is not None:
                realeventset = utils.eventsets[self.eventset]
                eventsetcmds = realeventset.formatdata(self, s, scaleamt, secondary, actualpowerlvl)
                if eventsetcmds is None:
                    print(f"Failed to generate {self.name}: event set failed to generate")
                    return None
                s.modcmdsbefore = eventsetcmds + "\n\n" + s.modcmdsbefore

        secondarypower = secondary.calcModifiedPowerForSpellEffect(self)
        ret = self._generateNextspell(s, mod, secondary, secondarypower, **options)
        if ret is None:
            return None


        # Assign cast time
        if s.casttime is None:
            s.casttime = spell.casttimes.get(int(s.fatiguecost / 100), 100)

        # don't make combat spells uncastable at the minimum level, eg X1 that requires 2+ gems
        self.handleOvercostSpell(s)
        self._splitSpellPathLevels(s)

        # buffs with aoe 0 should be self only, which means setting range to 0
        if self.spelltype & SpellTypes.BUFF and s.aoe == 0:
            s.range = 0

        mod.apply(s)

        # If path level dropped below 1, try to generate again
        if s.path1level < 1 and self.pathlevel > 0:
            print(f"Failed to generate, pathlevel has fallen to {s.path1level}")
            return self.rollSpell(researchlevel, forceschool=forceschool, forcepath=forcepath,
                                  isnextspell=isnextspell,
                                  forcesecondaryeff=forcesecondaryeff, blocksecondary=blocksecondary,
                                  allowblood=allowblood, allowskipchance=allowskipchance, setparams=setparams,
                                  forcepathlevel=forcepathlevel, forcedmodifier=forcedmodifier, **options)

        if not secondary.apply(self, s, mod, **options):
            return None
        self.setBloodSpellFatigueAndSchool(s, **options)

        # Battle effects that cost a gem, but didn't originally cost a gem, get a bit more scaling
        # but not blood effects, and this also won't apply to nextspells as their fatigue doesn't scale
        if s.path1 != 128 and s.effect < 10000 and s.fatiguecost >= 100 and self.fatiguecost < 100:
            additionalscale = (1 + actualpowerlvl) * (mod.scalerate + self.scalerate + secondary.scalerate)
            self._scaleSpellEffectiveness(s, additionalscale, mod, secondary)

        self._postScalingFatigueAdjustments(s, **options)
        plural = True if (s.aoe > 0 or s.nreff > 1) else False
        if self.spelltype & SpellTypes.EVOCATION:
            plural = True if (s.aoe > 1 or s.nreff > 1) else False
        self._writeDescription(s, mod, secondary, plural)
        # Dynamic scale number of effects, damage, etc
        self.dynamicScaleParams(s)
        self.formatDetails(s, mod, secondary)
        self.enforceGemCosts(s)
        if not self._nameSpell(s, mod, secondary, plural, **options):
            return None

        # Spells copied from record of creation allow fixed duration province enchantments
        # The duration is the difference of cost (in gems) between the primary and secondary spells
        # As all the fatigue scaling above can break this, put it back
        if (self.copyspell == "Record of Creation" or self.fixeddurationenchantment) and s.nextspell is not None:
            diff = self.fatiguecost - self.nextspell.fatiguecost
            print(f"This is a record of creation based spell, set nextspell's fatigue cost to defined difference"
                  f"of {diff}")
            s.nextspell.fatiguecost = s.fatiguecost + diff

        s.comments.append(f"Generated with effect {self.name} at research level {researchlevel}")
        s.comments.append(f"Chosen modifier is {mod.name}")
        s.comments.append(f"Secondary effect is {secondary.name}")
        s.comments.append(f"Main spell is {s.name}")
        if setparams is not None:
            for param, paramval in setparams.items():
                s.comments.append(f"Set param {param} to {paramval}")
        try:
            s.comments.append(f"Final power level was {actualpowerlvl}")
            s.comments.append(f"Scaleamt was {scaleamt}")
        except:
            pass

        self._updateSpellGraphics(s, mod)
        self.generated += 1
        # Implement research level modifier options
        s.researchlevel -= options.get("researchmodifier", 0)
        self._propagateAoEToNextspells(s)

        if utils.SPELL_ID >= 4000:
            raise ValueError("Spell ID has reached 4000. Dominions will reject this mod.")
        s.id = utils.SPELL_ID
        utils.SPELL_ID += 1

        # Sanity check: the game doesn't like spells with a path requirement of over 9 and makes them become 1 instead
        s.path1level = min(9, s.path1level)
        s.path2level = min(9, s.path2level)

        # Fill in placeholders in modcmdsbefore
        # This is from event sets
        s.modcmdsbefore = s.modcmdsbefore.replace("SPELLNAME", s.name)
        s.details = naming.parsestring(s.details, isspell=False, spell=s, dopluralisations=False)
        # Dominions crashes if any details are left as empty strings
        s.details = s.details.strip()
        if s.details == "":
            s.details = None

        self.calcAISpellMod(s)

        if secondary.unitmod != "":
            um = utils.unitmods[secondary.unitmod]
            self.calculateSummonAISpellMod(s, um.lastunitAIScore)
        elif s.effect in [1, 43]:
            # battle summon or edge of field battle summon
            if self.damage < 0 and self.newunit is None:
                # Built in montag: easiest to special case those values
                score = unitinbasedatafinder.getMontagSummonAIScore(self.damage)
            else:
                score = self.getUnit().calcSummonAIScore()
            self.calculateSummonAISpellMod(s, score)


        # Add to permenant slot taking spell counts if appropriate
        if self.permanentslotusage:
            utils.permanent_slot_spells_by_path[s.path1] = utils.permanent_slot_spells_by_path.get(s.path1, 0) + 1
            print(f"Path {s.path1}: num permanent slots now {utils.permanent_slot_spells_by_path.get(s.path1, 0)}")

        return s

    def dynamicScaleParams(self, s):
        "Dynamically scale attributes of the given spell."
        # never scale things at their lowest level
        if s.researchlevel > self.power and s.path1level > 0:
            for attribToScale in ("nreff", "damage", "aoe"):
                # Do not try to scale x% battlefield AoE spells
                if attribToScale == "aoe" and (600 < s.aoe < 700):
                    continue

                # Only mess with damage values for some effects
                if attribToScale == "damage" and s.effect not in [2, 3, 7, 8, 13, 24, 32, 33, 10040, 46, 66, 74, 73, 96,
                                                                  103, 104, 105, 128, 129, 134, 138, 142, 10117]:
                    continue

                # Leave 999 damage effects as they are
                elif attribToScale == "damage" and s.damage == 999:
                    continue

                attribScaleAmt = getattr(self, attribToScale) // 1000
                # Do not even think about scaling montags or anything else special
                if attribScaleAmt < 0:
                    continue
                if attribScaleAmt == 0:
                    # Default to 15% scaling, could add a command line option for this
                    scaleratio = 0.15
                    # Do not do this unless the spell naturally scales the attribute with research
                    if attribToScale == "nreff":
                        flag = SpellTypes.POWER_SCALES_NREFF
                    elif attribToScale == "damage":
                        flag = SpellTypes.POWER_SCALES_DAMAGE
                    elif attribToScale == "aoe":
                        flag = SpellTypes.POWER_SCALES_AOE
                    if not self.spelltype & flag:
                        print(f"Skip scaling attribute {attribToScale} as no research level progression")
                        continue
                else:
                    basespellvalue = (attribScaleAmt * self.power) + getattr(self, attribToScale) % 1000
                    if basespellvalue == 0:
                        print(f"Skip scaling attribute {attribToScale} as attribute value is zero")
                        continue
                    scaleratio = min(1.0, attribScaleAmt / basespellvalue)
                    print(f"Attribute scale amount is {attribScaleAmt}, base spell value is {basespellvalue}")

                newspellattrib = getattr(s, attribToScale)
                newspellvalue = ((newspellattrib // 1000) * s.path1level) + newspellattrib % 1000
                print(f"Desired scaling ratio for attribute {attribToScale}" \
                      f" is {scaleratio}; new spell has base value {newspellvalue}")
                desiredScalingAmount = newspellvalue * scaleratio
                newscale = math.floor(max(attribScaleAmt, min(newspellvalue/s.path1level, min(9, math.floor(desiredScalingAmount)))))
                newfixed = newspellvalue - (newscale * s.path1level)
                print(f"Desired scaling amount = {desiredScalingAmount}, split into {newscale} scaling + {newfixed};"
                      f" old value was {getattr(s, attribToScale)}, pathlevel={s.path1level}")
                setattr(s, attribToScale, ((newscale) * 1000) + newfixed)
                print(f"Final value is {getattr(s, attribToScale)}")

    def enforceGemCosts(self, s):
        # Certain effects should always have gem costs for safety reasons
        # These are: reinvigoration, summon commander
        if s.effect > 10000 and s.fatiguecost < 100 and self.fatiguecost >= 100:
            print(f"Increase gem cost of ritual from {s.fatiguecost} to 100 so it costs a gem")
            s.fatiguecost = 100
        if s.effect == 8 and self.fatiguecost >= 100:  # reinvigoration
            fatiguedifference = 100 - s.fatiguecost
            if s.fatiguecost < 100:
                print(f"Gem cost enforcing subtracted {fatiguedifference} from casting time")
                s.casttime = max(10, s.casttime - fatiguedifference)
                s.fatiguecost = 100
        elif s.effect == 21: # summon commander, in battle only
            if s.fatiguecost < 100:
                effectmult = 100 / max(1, s.fatiguecost)
                scalenreff = (s.nreff % 1000) + (s.path1level * (s.nreff // 1000))
                print(f"Gem cost enforcing multiplied number of effects by {scalenreff}")
                s.nreff = math.floor(effectmult * scalenreff)
                self.dynamicScaleParams(s)
                s.fatiguecost = 100
    def calcchassisvalues(self):
        "Calculates the mundane and magical chassis values for the summon attached to this effect, if any."
        self.magicvalue = 0.0
        if self.chassisvalue is not None:
            self.magicvalue = self.fatiguecost - self.chassisvalue
            self.magicvaluepercent = self.magicvalue / self.fatiguecost
            self.chassisvaluepercent = self.chassisvalue / self.fatiguecost
            if self.magicvalue < 0.0:
                raise ValueError(
                    f"Can't have a negative (fatiguecost-chassisvalue) of {self.magicvalue} for {self.name}")
    def getUnit(self) -> unitinbasedatafinder.UnitInBaseDataFinder:
        if self.newunit is None:
            return unitinbasedatafinder.get(self.damage)
        else:
            newunitobj = utils.newunits[self.newunit]
            return newunitobj.toUnitBaseData()
    def calcAISpellMod(self, spell):
        """Add an appropriate AI modifier to spell to deal with the fact the casting AI doesn't evaluate AoE
        very effectively. Most importantly, the largest AoE it considers is a 5x5 square once a spell reaches 11 AoE."""
        realaoe = spell.aoe % 1000 + (spell.path1level * (spell.aoe // 1000))
        if realaoe >= 16 and realaoe < 600:
            # but because it only evaluates a 5x5 square, some of the extra AoE could be wasted
            # this adds a progression at half speed
            additionalAoE = realaoe - 15
            additionalAoERatio = additionalAoE / realaoe
            proportionalIncrease = additionalAoERatio / 2
            print(f"AoE AI spell mod: additional AoE ratio is {additionalAoERatio}")
            spell.multiplyAISpellMod(1+proportionalIncrease)
        # x% of field spells are also not handled, and are assumed to be 100%
        elif realaoe == 665: # 25% of field
            spell.multiplyAISpellMod(0.25)
        elif realaoe == 664: # 10% of field
            spell.multiplyAISpellMod(0.1)
        elif realaoe == 663: # 50% of field
            spell.multiplyAISpellMod(0.5)
        elif realaoe == 662: # 5% of field
            spell.multiplyAISpellMod(0.05)

        # Adjust Illwinter AI score for multi projectiles, because 16+ projectiles turns it into a 5x5 aoe consideration
        # with each square's weight being (nreff*100)/26 (and twice as much for the mid square)
        realnreff = spell.nreff % 1000 + (spell.path1level * (spell.nreff // 1000))
        if (realaoe == 0 and realnreff >= 16) or (realaoe == 0 and realnreff > 1):
            mult = 1.0 / (realnreff / 2.0)
            spell.multiplyAISpellMod(mult)


    def scaleSpellEffectsToFatigue(self, s, desiredfatigue):
        flatnumeffects = s.nreff % 1000
        scalenumeffects = s.nreff // 1000
        realnumeffects = (scalenumeffects * s.path1level) + flatnumeffects
        realaoe = s.aoe % 1000 + (s.path1level * (s.aoe // 1000))


        if s.fatiguecost > desiredfatigue:
            print(f"Spell is overcosted! Fatigue is {s.fatiguecost} but path level is {s.path1level}")
            reductionfactor = desiredfatigue / s.fatiguecost
            for attri in ["nreff", "aoe"]:
                print(f"Adjusting attrib: {attri}")
                if s.fatiguecost <= desiredfatigue:
                    break
                reductionfactor = desiredfatigue / s.fatiguecost
                if attri == "nreff":
                    attribvalue = realnumeffects
                else:
                    attribvalue = realaoe
                    if 600 < realaoe < 700:
                        print(f"Skip trying to scale AoE, this is x% of battlefield!")
                        continue
                if attribvalue > 1:
                    desirednumeffects = max(1, int(round(attribvalue * reductionfactor)))
                    numeffectstolose = attribvalue - desirednumeffects
                    # Take from scaling first
                    while 1:
                        # can't reduce scaling if it would drop below the number to lose
                        if numeffectstolose < s.path1level:
                            print(
                                f"Effects to lose: {numeffectstolose}, less than path level of {s.path1level}, exit scaling changes")
                            break
                        # don't reduce scaling below 1 if it doesn't exist
                        if (getattr(s, attri) // 1000) <= 1:
                            break
                        if numeffectstolose <= 0:
                            break
                        setattr(s, attri, getattr(s, attri) - 1000)
                        numeffectstolose -= s.path1level
                        print(
                            f"Effects to lose: {numeffectstolose}, drop 1 scaling and {s.path1level} effects, spell attri is {getattr(s, attri)}")

                    while 1:
                        # Don't reduce the flat number of effects below 0
                        if (getattr(s, attri) % 1000) == 0:
                            break
                        if numeffectstolose <= 0:
                            break
                        setattr(s, attri, getattr(s, attri) - 1)
                        numeffectstolose -= 1
                        print(f"{numeffectstolose} remaining to lose, spell attri is {getattr(s, attri)}")

                    s.comments.append(f"Reduced attribute {attri} from {attribvalue} to fit cost "
                                      f"reduction scale of {reductionfactor}")

            reductionfactor = desiredfatigue / s.fatiguecost
            if reductionfactor > 1.0:
                s.comments.append(f"Alter cast time by {reductionfactor} to make up remaining reductionfactor")
                s.casttime = math.floor(min(999, (s.casttime * reductionfactor)))

            s.comments.append(f"Reduced fatigue cost from {s.fatiguecost} to make it actually castable")
            s.fatiguecost = min(s.fatiguecost, desiredfatigue)
        else:
            print(f"Spell is undercosted! Fatigue is {s.fatiguecost} but desired min is {desiredfatigue}")
            increasefactor = desiredfatigue/s.fatiguecost
            for attri in ["nreff", "aoe"]:
                print(f"Adjusting attrib: {attri}")
                if s.fatiguecost >= desiredfatigue:
                    break
                increasefactor = desiredfatigue / s.fatiguecost
                if attri == "nreff":
                    attribvalue = realnumeffects
                else:
                    attribvalue = realaoe
                    if 600 < realaoe < 700:
                        print(f"Skip trying to scale AoE, this is x% of battlefield!")
                        continue
                if attribvalue > 1:
                    desirednumeffects = max(1, int(round(attribvalue * increasefactor)))
                    numeffectstogain = desirednumeffects - attribvalue
                    # Take from scaling first
                    while 1:
                        # can't increase scaling if it would put spell above the number to gain
                        if numeffectstogain > s.path1level:
                            print(
                                f"Effects to gain: {numeffectstogain}, less than path level of {s.path1level}, exit scaling changes")
                            break
                        # don't increase scaling if it doesn't exist
                        if (getattr(s, attri) // 1000) <= 1:
                            break
                        if numeffectstogain <= 0:
                            break
                        setattr(s, attri, getattr(s, attri) + 1000)
                        numeffectstogain -= s.path1level
                        print(
                            f"Effects to gain: {numeffectstogain}, add 1 scaling and {s.path1level} effects, spell attri is {getattr(s, attri)}")

                    while 1:
                        if numeffectstogain <= 0:
                            break
                        setattr(s, attri, getattr(s, attri) + 1)
                        numeffectstogain -= 1
                        print(f"{numeffectstogain} remaining to gain, spell attri is {getattr(s, attri)}")

                    s.comments.append(f"Increased attribute {attri} from {attribvalue} to fit cost "
                                      f"increase scale of {increasefactor}")

            s.comments.append(f"Increased fatigue cost from {s.fatiguecost} to meet desired fatigue cost")
            s.fatiguecost = max(s.fatiguecost, desiredfatigue)

    def handleOvercostSpell(self, s):
        if not self.spelltype & SpellTypes.RITUAL and s.effect < 10000 and s.school > -1:
            maxfatiguecost = 99 + (100 * s.path1level)
            if s.fatiguecost > maxfatiguecost:
                self.scaleSpellEffectsToFatigue(s, maxfatiguecost)





    def calculateSummonAISpellMod(self, spell, aiscore):
        """Fight back against Illwinter's casting AI by calculating an aispellmod to better represent how magicgen
        values the summons."""
        if spell.effect in [1, 43]:
            realnreff = spell.nreff % 1000 + (spell.path1level * (spell.nreff // 1000))
            print(f"Spell nreff is {spell.nreff}: calced real nreff as {realnreff}")
            finalaiscore = realnreff * aiscore
            # Calculate what we want the AI score to be
            # this is fluffed to 40-160% of the calculated value

            # Illwinter formula values for reference:
            # 1 longdead: ~72
            # 5 longdead (HoS): ~360
            # phantasmal wolf: 64
            # wight: 124
            # magma child: 162

            # Mine:
            myaiscore = 5 + (spell.path1level + max(0, spell.path2level)) * 15 + (spell.researchlevel * 15)
            myaiscore *= (0.5 + (spell.fatiguecost/100))
            proportion = myaiscore/finalaiscore
            spell.multiplyAISpellMod(proportion)
            print(f"AI spell mod for summon: Illwinter base = {finalaiscore}, mine={myaiscore}: ratio={proportion}" \
                  f" final spell mod = {spell.aispellmod}")
    def _scaleSpellEffectiveness(self, s, scaleamt, mod, secondary):
        """Adds scaleamt to the values of the parameters this effect wants to scale, according to its spelltype flags.
        Also handles other issues such as making spells battlefield wide at very high AoE."""
        # scale the thing
        if self.spelltype & SpellTypes.POWER_SCALES_AOE:
            s.aoe += scaleamt

            # Do I make it battlefield wide?
            if self.spelltype & SpellTypes.BUFF and self.spelltype & SpellTypes.ALLOW_BATTLEFIELD and not mod.nobattlefield and not secondary.nobattlefield:
                tmp = s.aoe % 1000
                if tmp > 31:
                    print("Made buff battlefield wide")
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
            s.damage += scaleamt
            print(f"scaled damage by {scaleamt}, val is now {s.damage}")
        if self.spelltype & SpellTypes.POWER_SCALES_NREFF:
            s.nreff += scaleamt
            print(f"scaled nreff by {scaleamt}, val is now {s.nreff}")
        if self.spelltype & SpellTypes.POWER_SCALES_MAXBOUNCES:
            s.maxbounces += scaleamt
            print(f"scaled maxbounces by {scaleamt}, val is now {s.maxbounces}")
        if self.spelltype & SpellTypes.POWER_SCALES_EFFECTNO:
            s.effect += scaleamt
            print(f"scaled effect by {scaleamt}, val is now {s.effect}")

        # Remove decimal stuff
        s.nreff = int(math.floor(s.nreff))
        s.aoe = int(math.floor(s.aoe))
        s.damage = int(math.floor(s.damage))
        s.maxbounces = int(math.floor(s.maxbounces))
        s.effect = int(math.floor(s.effect))
    def calculateExpectedFinalFatigue(self, researchlevel, modifier, secondary=None):
        if secondary is None:
            secondary = utils.secondaries["Do Nothing"]

        actualpowerlvl = (researchlevel - self.power) + secondary.power + modifier.power
        scaleamt = self.scalerate * ((actualpowerlvl * (actualpowerlvl + 1)) / 2)
        scaleamt = scaleamt * (self.scalecost + secondary.scalecost + modifier.scalecost)
        DebugLogger.debuglog(f"Expected final scaleamt: {scaleamt}", debugkeys.FATIGUECOSTCONSTRAINTS)

        finalfatigue = self.fatiguecost
        fatiguefromresearch = 10 * actualpowerlvl
        scaleexponent = self.scalefatigueexponent + secondary.scalefatigueexponent + modifier.scalefatigueexponent
        DebugLogger.debuglog(f"Expected fatigue exponent: {scaleexponent}", debugkeys.FATIGUECOSTCONSTRAINTS)
        exponentcomponent = scaleamt ** abs(scaleexponent)
        finalfatigue += fatiguefromresearch
        DebugLogger.debuglog(f"Expected from RL: {fatiguefromresearch}", debugkeys.FATIGUECOSTCONSTRAINTS)
        DebugLogger.debuglog(f"Expected from exponentcomponent: {exponentcomponent}", debugkeys.FATIGUECOSTCONSTRAINTS)
        if scaleexponent >= 0.0:
            finalfatigue += exponentcomponent
        else:
            finalfatigue -= exponentcomponent
        finalfatigue = math.floor(finalfatigue)

        DebugLogger.debuglog(f"Expected fatigue after exponent: {finalfatigue}", debugkeys.FATIGUECOSTCONSTRAINTS)

        for attrib, mult in secondary.multcommands:
            if attrib == "fatiguecost":
                finalfatigue *= mult
        for attrib, mult in modifier.multcommands:
            if attrib == "fatiguecost":
                finalfatigue *= mult
        finalnreff = self.nreff

        DebugLogger.debuglog(f"Expected after mults: {finalfatigue}", debugkeys.FATIGUECOSTCONSTRAINTS)

        finalfatigue += (scaleamt * self.scalefatiguemult)

        DebugLogger.debuglog(f"Expected after scalefatiguemult: {finalfatigue}", debugkeys.FATIGUECOSTCONSTRAINTS)

        if self.spelltype & SpellTypes.POWER_SCALES_NREFF:
            finalnreff += scaleamt
        finalfatigue += (finalnreff * (secondary.fatiguecostpereffect))
        DebugLogger.debuglog(f"Expected after cost per effect: {finalfatigue}", debugkeys.FATIGUECOSTCONSTRAINTS)

        # blood gets doubled
        # (this will unfortunately miss blood versions of other paths' spells, but alas)
        if self.paths == 128:
            finalfatigue *= 2

        if debugkeys.FATIGUECOSTCONSTRAINTS:
            print(f"fatiguecalc = {self.fatiguecost} (base) + {fatiguefromresearch} from RL + {exponentcomponent} "
                  f"from exponent: {scaleamt}**{scaleexponent}")

        return finalfatigue

    def _shouldSkipDueToProximityToRelatedSpells(self, **options):
        existingspells = options.get("existingspells", None)
        allowskipchance = options.get("allowskipchance", True)
        if not self.isnextspell and (allowskipchance or self.skipchance >= 100) and not self.noresearchdifferenceskip:
            # if we were passed the dict of spells that already exist, skipchance based on proximity to effects that
            # already exist - this is the case for non-holy non-national spells
            if existingspells is not None:
                smallestdiff = None
                for rl, effectlist in existingspells.items():
                    if self.name in effectlist:
                        thisdiff = abs(rl - self.researchlevel)
                        if smallestdiff is None or thisdiff < smallestdiff:
                            smallestdiff = thisdiff
                print(f"Smallest research level diff to an already generated spell is {smallestdiff}")
                if smallestdiff is None:
                    powerdiff = max(0, self.researchlevel - self.power)
                    powerskipchance = min(90, powerdiff * 4)
                    if random.random() * 100 < powerskipchance:
                        print(f"Failed to generate {self.name} at {self.researchlevel}: "
                              f"base research difference skipchance of {powerskipchance}")
                        return True
                else:
                    tempvalue = (4 - smallestdiff)
                    powerskipchance = min(100, (tempvalue * tempvalue) * 15)
                    if random.random() * 100 < powerskipchance:
                        print(f"Failed to generate {self.name} at {self.researchlevel}: "
                              f"research difference to existing spell skipchance of {powerskipchance}")
                        return True
            else:
                powerdiff = max(0, researchlevel - self.power)
                powerskipchance = min(90, powerdiff * 8)
                if random.random() * 100 < powerskipchance:
                    print(f"Failed to generate {self.name} at {self.researchlevel}: "
                          f"base research difference skipchance of {powerskipchance}")
                    return True
        return False

    def _shouldNotGenerate(self, **options):
        "True if this spell effect should not generate a spell with the passed params for some reason, else False."
        isnational = options.get("isnational", False)
        allowskipchance = options.get("allowskipchance", True)
        forcepath = options.get("forcepath", False)
        forceschool = options.get("forceschool", False)

        if self.badaispell and options.get("nobadaispells", 0) > 0:
            print(f"Fail {self.name}: is a bad AI spell")
            return True

        if isnational and self.permanentslotusage:
            print(f"Fail {self.name} as this is a national generation and the effect wants to fill permanent slots")
            return True

        if random.random() * 100 < self.skipchance and not self.isnextspell and (
                allowskipchance or self.skipchance >= 100):
            print(f"Failed to generate {self.name} at {self.researchlevel}: random skipchance")
            return True

        if self._shouldSkipDueToProximityToRelatedSpells(**options):
            return True

        # less combat blood spells
        # bypasses allowskipchance
        if self.effect < 10000 and forcepath == 128 and not self.isnextspell:
            if random.random() < 0.85:
                print(f"Failed as 85% to have less blood combat spells")
                return True
            # Even less likely if they have other primary paths
            if self.paths != 128 and random.random() < 0.95:
                print(f"Failed as 95% to fail other path combat spells")
                return True

        if self.unique and self.generated > 0:
            print(f"Failed to generate {self.name} at {self.researchlevel}: effect is unique and already exists")
            return True

        # Don't make lots of generations from the same effect
        if allowskipchance and not self.isnextspell and self.generated > 0:
            repeatedskipchance = 1 - (1 / (1 + (self.generated * 3)))
            if random.random() < repeatedskipchance:
                print(f"Skipped based on {self.generated} previous generations")
                return True

        if forceschool and not (self.schools & forceschool):
            print(
                f"Failed to generate {self.name} at {self.researchlevel}: school is forced to {forceschool} which is incompatible")
            return True

        # path -1 means nextspells, and they can't be cast normally
        # so don't generate them if we aren't a next spell or have a forced path for some other reason
        if self.paths == -1 and not forcepath:
            print(f"Failed to generate {self.name} at {self.researchlevel}: spell has no paths")
            return True

        if self.schools == -1 and not self.isnextspell:
            # nextspells go in the unresearchable school!
            print(f"{self.name} is unresearchable and not next spell, fail this generation")
            return True

        return False

    def _rollModifier(self, **options):
        blockmodifier = options.get("blockmodifier", False)
        forcedmodifier = options.get("forcedmodifier", None)
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
                print(f"Consider mod: {m.name}")
                if m.compatibility(self, self.researchlevel, self.isnextspell):
                    if random.random() * 100 < m.skipchance:
                        if m.skipchance < 100.0:
                            modlist.append(m.name)
                    else:
                        print(f"Using mod {m.name} for {self.name}")
                        mod = m
                        break
                if len(modlist) == 0:
                    print(f"No valid modifiers for {self.name} at research {self.researchlevel}")
                    raise Exception(f"No valid modifiers for {self.name} at research {self.researchlevel}")

                    raise ValueError(f"No valid modifiers for {self.name}")
        return mod

    def _decideSecondaryPathLimitations(self, **options):
        blocksecondary = options.get("blocksecondary", False)
        forcesecondaryeff = options.get("forcesecondaryeff", None)
        self.allowSecondary = True
        self.allowOnlySamePathSecondaryEffect = False
        self.allowOnlyDiffPathSecondaryEffect = False

        if self.effect in [1, 10001, 10050, 10038, 21, 10021]:
            diffpathchance = options.get("summondiffpathsecondarychance", 10)
            samepathchance = options.get("summonsamepathsecondarychance", 40)
        else:
            diffpathchance = options.get("diffpathsecondarychance", 10)
            samepathchance = options.get("samepathsecondarychance", 40)

        if blocksecondary:
            self.allowSecondary = False
            print(f"Secondary effect is blocked for this effect")
        elif forcesecondaryeff is None and random.random() * 100 <= self.secondaryeffectskipchance:
            print(f"Secondary effect skipchance of {self.secondaryeffectskipchance}")
            self.allowSecondary = False
        elif forcesecondaryeff is None:
            # this should stop 100% secondary path spells getting a different offpath secondary effect
            if random.random() * 100 >= diffpathchance or random.random() * 100 < self.secondarypathchance:
                if random.random() * 100 >= samepathchance:
                    print(f"Failed both secondary effect chances of {diffpathchance} and {samepathchance}")
                    self.allowSecondary = False
                else:
                    print(f"Allowed only same path secondary effect")
                    self.allowOnlySamePathSecondaryEffect = True
            else:
                print(f"Allowed only diff path secondary effect")
                self.allowOnlyDiffPathSecondaryEffect = True

    def _rollSecondary(self, mod, **options):
        forcesecondaryeff = options.get("forcesecondaryeff", None)
        secondarylist = list(utils.secondaries.keys())
        random.shuffle(secondarylist)
        secondary = None


        self._decideSecondaryPathLimitations(**options)
        print("roll secondary")

        if self.allowSecondary:
            while secondary is None:
                if len(secondarylist) == 0:
                    if self.allowOnlySamePathSecondaryEffect or self.allowOnlyDiffPathSecondaryEffect:
                        print("Forced to take Do Nothing as secondary as no others were valid")
                        secondary = utils.secondaries["Do Nothing"]
                        break
                    print(f"Failed to generate {self.name} at {self.researchlevel}: no valid secondaries")
                    return None
                toconsider = utils.secondaries[secondarylist.pop(0)]
                if toconsider.compatibility(self, mod, self.researchlevel):
                    if forcesecondaryeff is None:
                        # Check path eligibility
                        if self.allowOnlySamePathSecondaryEffect and toconsider.paths & self.paths == 0:
                            # Have a reduced chance to be allowed, if the path is normally a secondary path of the spell
                            if toconsider.paths & self.secondarypaths != 0 and self.secondarypathchance > 0:
                                if random.random() * 100 < self.secondarypathchance:
                                    # Allow it, this time
                                    pass
                                else:
                                    continue
                            else:
                                continue
                        if self.allowOnlyDiffPathSecondaryEffect and toconsider.paths & self.paths != 0:
                            continue
                        if random.random() * 100 < toconsider.skipchance:
                            if toconsider.skipchance < 100.0:
                                secondarylist.append(toconsider.name)
                        else:
                            secondary = toconsider
                            break
                    else:
                        # Make sure its path matches what was asked for
                        if toconsider.paths & forcesecondaryeff:
                            # ignore skipchance for this
                            print(f"Forced paths: Using secondary {toconsider.name}")
                            secondary = toconsider
                            break
                        else:
                            print(f"Bad paths for forced secondary: {forcesecondaryeff}")
        else:
            secondary = utils.secondaries["Do Nothing"]


        print(f"using secondary {secondary.name} for {self.name} with mod {mod.name}")
        return secondary

    def _powerLevelIsValid(self, mod, secondary):
        "True if this effect can legally generate with the passed research level, selected modifier, and secondary."
        # Holy spells need to escape this
        # Also, Nextspells without a scale rate should still be allowed
        secondarypower = secondary.calcModifiedPowerForSpellEffect(self)

        if self.researchlevel + mod.power + secondarypower < self.power and self.paths != 256 and not (
                self.isnextspell and self.scalerate == 0):
            print(f"Failed to generate {self.name} at {self.researchlevel}: final power level too low")
            return False

        if self.researchlevel + mod.power + secondarypower > self.maxpower and self.paths != 256 and not (
                self.isnextspell and self.scalerate == 0):
            print(f"Failed to generate {self.name} at {self.researchlevel}: final power level too high")
            return False
        return True

    def _setSpellDefaultValues(self, s, **options):
        "Unload base attribute values onto the passed spell object. Deals exclusively with simple copying of data"
        setparams = options.get("setparams", None)
        s.name = self.name + " " + str(random.randint(-9999, 9999))
        s.effect = self.effect
        s.damage = self.damage
        s.range = self.range
        s.nreff = self.nreff
        s.precision = self.precision
        s.aoe = self.aoe
        s.spec = self.spec
        s.details = self.details
        s.researchlevel = self.researchlevel
        s.fatiguecost = self.fatiguecost
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
        s.aispellmod = self.aispellmod
        s.hiddenench = self.hiddenench
        s.friendlyench = self.friendlyench
        s.parenteffect = self
        if s.details is None:
            s.details = ""
        if self.isnextspell:
            s.isnextspell = True

        if setparams is not None:
            for key, val in setparams.items():
                setattr(s, key, val)

        if self.copyspell is not None:
            s.copyspell = self.copyspell
        if self.casttime is not None:
            s.casttime = self.casttime
        if options.get("prevspell", None) is not None:
            s.prevspell = options.get("prevspell")

        # modifier fatigue cost is added later
        s.fatiguecost = self.fatiguecost
    def _selectSpellSchool(self, **options):
        "Select a valid research school for this spell effect"
        forceschool = options.get("forceschool", None)
        if self.schools > -1:
            if forceschool is not None:
                return forceschool
            return utils._selectFlag(SchoolFlags, self.schools)
        else:
            return -1

    def _selectAndApplySpellPathsAndLevels(self, mod, secondary, s, **options):
        "As per the name. Returns False if the task is impossible and spell creation should abort"
        forcepath = options.get("forcepath", None)
        allowblood = options.get("allowblood", True)
        forcepathlevel = options.get("forcepathlevel", None)
        forcesecondaryeff = options.get("forcesecondaryeff", None)
        allowedsecondarypaths = options.get("allowedsecondarypaths", None)
        allowskipchance = options.get("allowskipchance", True)

        possibleillwinterpaths = utils.breakdownflag(511 & self.paths)
        random.shuffle(possibleillwinterpaths)
        print(f"Possible path with illwinter ids are {possibleillwinterpaths}")

        # If we are trying to pick a same path secondary, be very biased towards those path(s) as path1
        if self.allowOnlySamePathSecondaryEffect:
            possibleillwinterpaths = utils.breakdownflag(self.paths & secondary.paths) + possibleillwinterpaths
            print(f"After same path secondary bias: paths with illwinter ids are {possibleillwinterpaths}")

        if forcepath is None:
            while 1:
                if len(possibleillwinterpaths) == 0:
                    print(f"Failed to generate: no valid paths")
                    return False
                illwinterpath = possibleillwinterpaths.pop(0)
                s.path1 = 2 ** illwinterpath
                if s.path1 == 128 and not allowblood:
                    continue
                if random.random() * 100 <= self.pathskipchances.get(s.path1, 0) and len(possibleillwinterpaths) > 0:
                    if self.pathskipchances.get(s.path1, 0) < 100.0:
                        possibleillwinterpaths.append(illwinterpath)
                    continue
                # Effects taking permanent slots need to be limited in number to avoid mechanic abuse
                if self.permanentslotusage \
                        and utils.permanent_slot_spells_by_path.get(s.path1, 0) >= PERMANENT_SPELL_EFFECT_LIMIT_BY_PATH:
                    print(f"Path {s.path1} not allowed due to permanent slot taking spell limit")
                    continue
                print(f"Accepting path {s.path1} (illwinter path {illwinterpath})")
                break

        if forcepath is not None:
            if allowskipchance and random.random() * 100 <= self.pathskipchances.get(forcepath, 0):
                print(f"Forced path was {forcepath}, failed this pathskipchance")
                return False
            if self.permanentslotusage \
                    and utils.permanent_slot_spells_by_path.get(forcepath, 0) >= PERMANENT_SPELL_EFFECT_LIMIT_BY_PATH:
                print(f"Attempted to forcepath into a path that has too many permanent spell effects")
                return False
            print(f"Forced path to {forcepath}")
            s.path1 = forcepath

        s.path1level = self.pathlevel + mod.pathlevel + secondary.pathlevel
        if forcepathlevel is not None:
            print(f"Calced path level was {s.path1level}, using override {forcepathlevel} instead")
            s.path1level = forcepathlevel

        # See if the secondary effect we took has a path requirement that we fail to meet
        # (decide on offpath here if there will be one!)
        if secondary.paths > 0:
            if not (secondary.paths & s.path1):
                s.path2 = utils._selectFlag(PathFlags, secondary.paths)
                print(f"Forced to take offpath {s.path2} due to secondary effect:"
                      f" spell is currently {s.path1} and secondary wants {secondary.paths}")

        # Chance to roll a secondary path (if the secondary effect we picked doesn't demand one)
        if random.random() * 100 < self.secondarypathchance and s.path2 < 0 and forcesecondaryeff is None:
            print("Try to roll a secondary path")
            if self.secondarypaths > 0 and s.path1level >= 2 and self.secondarypaths != s.path1:
                p = self.secondarypaths
                if p & s.path1:
                    p -= s.path1
                if p > 0:
                    attempts = 0
                    while 1:
                        attempts += 1
                        s.path2 = utils._selectFlag(PathFlags, p)
                        if s.path2 != s.path1:
                            if random.random() * 100 > self.pathskipchances.get(s.path2, 0):
                                break
                        if attempts == 1000000:
                            raise Exception("Failed to select a secondary path, reached attempt limit")
                if allowedsecondarypaths is not None and allowedsecondarypaths & s.path2 == 0:
                    print(f"Failed to generate: not allowed selected secondary path of {s.path2}")
                    return False
        return True
    def calcActualpowerlvl(self, mod, secondary):
        """Return the spell's 'actual power level': this is the amount of levels above the
        minimum research level it is trying to generate at"""
        # Calc this even if the spell doesn't scale - this is for the sake of SCALEAMT in #details
        secondarypower = secondary.calcModifiedPowerForSpellEffect(self)
        actualpowerlvl = (self.researchlevel - self.power) + mod.power + secondarypower
        return actualpowerlvl
    def calcScaleamt(self, mod, secondary, actualpowerlvl=None):
        "Return the spell's scale amount: the amount its scaling attributes should be increased by."
        if actualpowerlvl is None:
            actualpowerlvl = self.calcActualpowerlvl(mod, secondary)
        scaleamt = 0
        for x in range(0, actualpowerlvl):
            scaleamt += (x + 1) * (mod.scalerate + self.scalerate + secondary.scalerate)
        scaleamt = int(round(scaleamt))
        return scaleamt


    def _scaleSpellPath1level(self, s, mod, secondary, **options):
        actualpowerlvl = self.calcActualpowerlvl(mod, secondary)
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

    def _scaleFatigueCost(self, s, scaleamt, mod, secondary, **options):
        actualpowerlvl = self.calcActualpowerlvl(mod, secondary)
        scaleamt2 = scaleamt * self.scalecost
        print(f"scaleamt now {scaleamt2} after being multiplied by scalecost {self.scalecost}")

        s.fatiguecost += scaleamt2 * self.scalefatiguemult
        print(f"Fatiguemult: Added {scaleamt2 * self.scalefatiguemult} to fatigue cost, it is now {s.fatiguecost}")
        if scaleamt2 > 0:
            scaleamt2 += 1  # otherwise the case where scaleamt = 1 yields no fatigue increase!

        s.fatiguecost += 10 * actualpowerlvl
        print(f"Power level: Added {10 * actualpowerlvl} to fatigue cost, it is now {s.fatiguecost}")


        scaleexponent = (mod.scalefatigueexponent + self.scalefatigueexponent + secondary.scalefatigueexponent)
        if scaleamt2 != 0.0 and scaleexponent > 0.0:
            s.fatiguecost += (scaleamt2 ** scaleexponent)
            print(
                f"Exponent: Added {scaleamt2 ** scaleexponent} (exponent is {scaleexponent}) to fatigue cost, it is now {s.fatiguecost}")
        elif scaleexponent < 0.0 and scaleamt2 != 0:
            s.fatiguecost -= (scaleamt2 ** (-1 * scaleexponent))
            print(
                f"Exponent: Subtracted {(scaleamt2 ** (-1 * scaleexponent))} (exponent is {scaleexponent}) to fatigue cost, it is now {s.fatiguecost}")

        s.fatiguecost = max(0, s.fatiguecost)

        # scaling fatiguecost per effect
        flatnumeffects = s.nreff % 1000
        scalenumeffects = s.nreff // 1000
        realnumeffects = (scalenumeffects * s.path1level) + flatnumeffects
        # blood gets double, as with most things
        if s.path1 == 128:
            s.fatiguecost += (realnumeffects * secondary.fatiguecostpereffect * 2)
        else:
            s.fatiguecost += (realnumeffects * secondary.fatiguecostpereffect)
    def _generateNextspell(self, s, mod, secondary, secondarypower, **options):
        forceschool = options.get("forceschool", None)
        setparams = options.get("setparams", None)
        optionscopy = copy.copy(options)
        optionscopy["isnextspell"] = True
        optionscopy["allowskipchance"] = False
        optionscopy["prevspell"] = s
        # Nextspells and extraspells can't necessarily get secondaries, trying to force them means they don't generate
        if optionscopy.get("forcesecondaryeff") is not None:
            optionscopy["forcesecondaryeff"] = None
        if self.nextspell != "":
            optionscopy["forcepath"] = s.path1
            optionscopy["blockmodifier"] = True
            optionscopy["researchlevel"] = self.researchlevel + mod.power + secondarypower
            s.nextspell = self.nextspell.rollSpell(**optionscopy)
            if s.nextspell is None:
                print(f"WARNING: Failed to generate nextspell {self.nextspell.name}")
                return None
        # Extraspell = "hangers on", eg communion master always generates a corresponding communion slave
        if self.extraspell != "":
            extraspell = utils.spelleffects[self.extraspell]
            optionscopy["forcepathlevel"] = s.path1level
            optionscopy["forceschool"] = s.school
            optionscopy["blockmodifier"] = False
            optionscopy["forcedmodifier"] = mod
            # communions do want to mimic the path of the parent, otherwise the slave might not
            # have the same path requirement as the master spell (which would be a bit unhelpful!)
            if self.donotsetextraspellpath == 0:
                optionscopy["forcepath"] = s.path1
                s.modcmdsbefore += extraspell.rollSpell(**optionscopy).output()
            else:
                # Elemental royalty all come together, and should NOT mimic the paths of the parents
                s.modcmdsbefore += extraspell.rollSpell(**optionscopy).output()
        return 1
    def _splitSpellPathLevels(self, s):
        "Move some path1levels into path2levels for the given spell"
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
            exponent = 1.9
            pathpoints = s.path1level ** exponent
            maxdivert = pathpoints / 2
            divert = max(1, random.random() * maxdivert)
            # Avoid the case where for instance x9 -> x8y1 has a lot of leftover points
            # that could be used to push y1 up higher
            secondarypathlevel = math.floor(divert ** (1 / exponent))
            remainingpoints = pathpoints - secondarypathlevel ** exponent
            primarypathlevel = math.floor(remainingpoints ** (1 / exponent))
            while 1:
                remainingpoints2 = pathpoints - (secondarypathlevel**exponent) - (primarypathlevel**exponent)
                if secondarypathlevel < primarypathlevel:
                    remainingpointsafteradjust = pathpoints - ((secondarypathlevel+1)**exponent) - (primarypathlevel**exponent)
                    if remainingpointsafteradjust >= 0.0:
                        print(f"Increase secondary path level from {secondarypathlevel}: {remainingpointsafteradjust} "
                              f"after adjustment")
                        secondarypathlevel += 1
                        continue
                break

            print(f"Split into secondary paths: primary was {s.path1level} -> X{primarypathlevel}Y{secondarypathlevel}")
            print(f"Pathpoints: {pathpoints}, diverted {divert} and had {remainingpoints} for path 1")
            s.path2level = secondarypathlevel
            s.path1level = primarypathlevel
            if not self.spelltype & SpellTypes.RITUAL:
                s.fatiguecost = min(s.fatiguecost, 100 * s.path1level)
    def setBloodSpellFatigueAndSchool(self, s, **options):
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

        # Blood ritual cost multiplier
        if s.path1 == 128 and (s.effect > 10000 or self.spelltype & SpellTypes.RITUAL):
            s.fatiguecost = int(s.fatiguecost * options.get("bloodcostscale", 1.0))
    def _postScalingFatigueAdjustments(self, s, **options):
        s.fatiguecost += options.get("fatiguemodflat", 0)
        s.fatiguecost *= options.get("fatiguemodmult", 1.0)
        s.fatiguecost = math.floor(s.fatiguecost)
        s.fatiguecost = max(0, s.fatiguecost)

        # Block free rituals
        if s.effect > 10000 and s.fatiguecost < 100:
            s.fatiguecost = 100

        # Fatigue cost should not exceed 999 for non rituals
        if s.effect < 10000:
            s.fatiguecost = min(999, s.fatiguecost)

            # Blood combat spells get more fatigue if they don't cost a slave
            if s.path1 == 128 and s.fatiguecost < 100:
                s.fatiguecost *= 2

            # If the spell is now uncastable, rescale number of effects
            self.handleOvercostSpell(s)

            # make fatigue nice round numbers
            if s.fatiguecost > 100:
                s.fatiguecost = int(100 * (s.fatiguecost // 100.0))
            else:
                s.fatiguecost = int(5 * (s.fatiguecost // 5.0))
        else:
            s.fatiguecost = int(100 * (s.fatiguecost // 100.0))
    def _writeDescription(self, s, mod, secondary, plural):


        priorities = sorted(list(self.descrconds.get(s.path1, {}).keys()), reverse=True)

        descrs = []

        for priority in priorities:
            thisPrioValid = False
            for cond in self.descrconds[s.path1][priority]:
                if cond.test(s):
                    # blood description changes if it doesn't require a slave to cast
                    if s.fatiguecost < 100:
                        descrs.append(cond.text.replace("$BLOOD_INTRO$", "$BLOOD_INTRO2$"))
                    else:
                        descrs.append(cond.text)
                    thisPrioValid = True
            if thisPrioValid:
                break

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
        print(f"Final description for spell: {s.descr}")
    def formatDetails(self, s, mod, secondary):
        if s.effect == 10038:
            if s.nreff > 1000:
                s.details += " This spell summons EFFECTIVENREFF creatures, with an additional NREFFSCALING per additional caster level. The creatures will attack anything in the target province, including friendlies, and will then disappear."
            else:
                s.details += " This spell summons EFFECTIVENREFF creatures, regardless of caster level. The creatures will attack anything in the target province, including friendlies, and will then disappear."

            s.details = s.details.strip()
        elif s.effect == 10037:
            s.details += " This spell summons EFFECTIVENREFF creatures, with an additional NREFFSCALING per additional caster level."

            s.details = s.details.strip()

        if s.flightspr is not None and s.flightspr > 0:
            s.details += " This is a projectile spell."
            s.details = s.details.strip()

        # Damage clouds
        if s.effect > 1000 and s.effect < 10000 and s.effect % 1000 in utils.DAMAGING_EFFECTS:
            s.details += " The cloud created by this spell inflicts a third of the final damage, rounded up."
            s.details = s.details.strip()
        if s.effect > 1000 and s.effect < 10000:
            dur = s.effect // 1000
            # Chain lightning clouds want different text really
            if s.effect % 1000 != 134:
                s.details += f" The cloud affects those standing within it every 1280 ticks (or 5.859375 times a round). It lasts for approximately {dur:.1f} rounds, for a total of {dur * 3} total activations."
                s.details = s.details.strip()
            else:
                s.details += f" The cloud releases chain lightning every 1280 ticks (or 5.859375 times a round). It lasts for approximately {dur:.1f} rounds, for a total of {dur * 3} total activations."
                s.details = s.details.strip()

        if s.ainocast > 0 and s.effect < 10000:
            s.details += " This spell will not be cast unless scripted."
            s.details = s.details.strip()

        s.details = s.details.strip() + "\n" + mod.details
        s.details = s.details.strip() + "\n" + secondary.details

        s.descr = s.descr.strip()
        s.details = s.details.replace("\\n", "\n")
        scale = s.nreff // 1000
        base = s.nreff % 1000
        print(f"Nreff breakdown: spell {s.nreff} = {scale} scale + {base} base, path 1 level is {s.path1level}")
        s.details = s.details.replace("EFFECTIVENREFF", str((s.path1level * scale) + base))
        s.details = s.details.replace("NREFFSCALING", str(scale))
        s.details = s.details.replace("NREFF", str(s.nreff))
        scale = s.damage // 1000
        base = s.damage % 1000
        print(f"Damage breakdown: on spell {s.damage} = {scale} scale + {base} base, path 1 level is {s.path1level}")
        s.details = s.details.replace("EFFECTIVEDAMAGE", str((s.path1level * scale) + base))
        s.details = s.details.replace("DAMAGESCALING", str(scale))
        s.details = s.details.replace("DAMAGE", str(s.damage))

        scaleamt = self.calcScaleamt(mod, secondary)
        # for globals: use aoe to denote the base amount
        finalglobalscaling = int(self.basescale + scaleamt)
        s.details = s.details.replace("SCALEAMT", str(finalglobalscaling))

        if s.nextspell != "" and s.nextspell is not None:
            s.details = s.details.replace("NEXTSPELL_EFFECTNUMBER_5XX", str((s.nextspell.effect % 1000) - 499))
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


    def _nameSpell(self, s, mod, secondary, plural, **options):
        "Return True on success, or False on failure"
        names = []
        forcesecondaryeff = options.get("forcesecondaryeff", None)

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



        # Naming needs these variables
        s.effectiveaoe = s.aoe % 1000 + ((s.aoe // 1000) * s.path1level)
        s.effectivenreff = s.nreff % 1000 + ((s.nreff // 1000) * s.path1level)
        # This one will be wrong for nondamaging spells, but shouldn't be used for them
        s.effectivedamage = s.damage % 1000 + ((s.damage // 1000) * s.path1level)

        # see which nameconds, if any, match, and add to the name pool
        priorities = sorted(list(self.nameconds.get(s.path1, {}).keys()), reverse=True)

        print(f"Priorities: {priorities}; the nameconds: {self.nameconds}")

        for priority in priorities:
            thisPrioValid = False
            for cond in self.nameconds[s.path1][priority]:
                if cond.test(s):
                    names.append(cond.text)
                    thisPrioValid = True
            if priority == 0:
                # take shallow copy to avoid doing bad things to later spells using the same self
                names += self.names.get(s.path1, [])[:]
            if thisPrioValid:
                break
        # must add this if there were no nameconds
        if 0 not in priorities and len(names) == 0:
            names += self.names.get(s.path1, [])[:]

        print(f"Possible names are {names}")

        if len(names) > 0:
            print(f"Begin naming for this spell, path is {s.path1}...")
            while 1:
                try:
                    print(f"Pick name: {len(names)} remain...")
                    name = names.pop(random.randint(0, len(names) - 1))
                    if secondary.unitmod != "":
                        um = utils.unitmods[secondary.unitmod]
                        name = name.replace("NAMEPREFIX", um.nameprefix)
                    if len(secondary.nameprefixes) > 0:
                        name = name.replace("NAMEPREFIX", random.choice(secondary.nameprefixes))
                    name = name.replace("NAMEPREFIX", "")

                    # Fix unit names for stuff created from events
                    if self.eventset is not None:
                        realeventset = utils.eventsets[self.eventset]
                        if realeventset.lastunitname is not None:
                            name = name.replace("CREATURE", realeventset.lastunitname)

                    if debugkeys.SUMMONSPELLNREFFDISPLAY and s.effect % 1000 in [1, 21, 37, 38, 43, 68]:
                        basenreff = s.nreff % 1000
                        scalenreff = (s.path1level * (s.nreff // 1000))
                        realnreff = basenreff + scalenreff
                        if scalenreff > 0:
                            name = f"{realnreff}x ({(s.nreff // 1000)}+) {name}"
                        else:
                            name = f"{realnreff}x {name}"

                    s.name = naming.parsestring(name, plural=plural, aoe=s.aoe, spelltype=self.spelltype,
                                                titlecase=True, isspell=True, spell=s)
                    break
                except naming.NameTooLongException:
                    pass
                if len(names) == 0:
                    print("Had to give up on this spell because no names were valid")
                    return False
        return True
    def _updateSpellGraphics(self, s, mod):
        if self.skipflightspr == 1:
            s.flightspr = None
        if self.skipexplspr == 1:
            s.flightspr = None

        if mod.givecloudsfx == 1:
            # 10123 may be usable but it's a bit dense
            if s.path1 == 1:
                s.explspr = random.choice([10053, 10011, 10014, 10203, 10311])
            elif s.path1 == 2:
                s.explspr = random.choice([10056, 10048, 10002, 10048, 10228, 10291, 10318, 10338])
            elif s.path1 == 4:
                s.explspr = random.choice([10045, 10054, 10005, 10008, 10015, 10196, 10230, 10275])
            elif s.path1 == 8:
                s.explspr = random.choice([10058, 10018, 10051, 10053, 10192, 10193, 10260, 10279])
            elif s.path1 == 16:
                s.explspr = random.choice([10041, 10001, 10121, 10159, 10207, 10266])
            elif s.path1 == 32:
                s.explspr = random.choice([10060, 10009, 10020, 10049, 10141, 10142, 10160, 10188, 10212, 10234, 10257,
                                           10261, 10317])
                #s.explspr = 10057
            elif s.path1 == 64:
                s.explspr = random.choice([10044, 10017, 10004, 10007, 10012, 10013, 10016, 10047, 10052, 10055, 10161,
                                           10184, 10231, 10237, ])
            elif s.path1 == 128:
                s.explspr = random.choice([10043, 10003, 10259])
    def _propagateAoEToNextspells(self, s):
        # If aoe is x% of field, nextspells seem to need it too?
        if 660 < s.aoe < 670:
            tmp = s.nextspell
            attempts = 0
            # not if the primary effect is extra effect on damage
            if not (s.spec & 1152921504606846976):
                while 1:
                    attempts += 1
                    if attempts > 10000:
                        raise Exception(f"Likely infinite nextspell loop for {self.name}")
                    if tmp is not None and tmp != "":
                        # nextspell on damage does not need this done to it or anything that follows
                        if tmp.spec & 1152921504606846976:
                            break
                        tmp.aoe = s.aoe
                        print(f"Set aoe for nextspell {tmp.name} to {s.aoe}")
                        tmp = tmp.nextspell
                    else:
                        break