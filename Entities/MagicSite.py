from Enums.PathFlags import PathFlags
from Enums.SpellTypes import SpellTypes
from Services.utils import unitmods, eventsets
from Services import utils, naming, montagbuilder
from fileparser import unitinbasedatafinder
import random
import math
import copy

UNITPARAMS = ["com", "mon", "summon", "summonlvl2", "summonlvl3", "summonlvl4", "wallcom", "wallunit"]

class MagicSite(object):
    def __init__(self):
        self.spelltype = 0
        self.name = None
        self.params = ["rarity", "loc", "gold", "res", "level", "decunrest", "supply",
                        "incscale", "decscale", "conjcost", "altcost", "evocost", "constcost", "enchcost", "thaucost",
                       "bloodcost", "scry", "scryrange", "firerange", "airrange", "watterange", "earthrange",
                       "astralrange", "deathrange", "naturerange", "bloodrange", "elementrange", "sorceryrange",
                       "allrange", "heal", "curse", "disease", "horrormark", "holyfire", "holypower", "xp",
                       "adventureruin", "blesshp", "blessanimawe", "blessmr", "blessawe", "blessmor", "blessstr",
                       "blessdarkvis", "blessatt", "blessdef", "blessprec", "blessfireres", "blesscoldres",
                       "blessshockres", "blesspoisres", "blessairshield", "blessreinvig", "blessdtv", "recallgod",
                       "domwar", "wallmult"]

        for param in self.params:
            setattr(self, param, None)

        self.rarity = 5
        self.loc = 1023

        self.allowedunitmods = []
        self.scaleparams = {}

        self.effectnumberforunits = 10001
        self.usefixedunitid = -1
        self.desiredmontagsize = 0
        self.restrictunitstospellpaths = True
        self.mincreaturepower = -1
        self.maxcreaturepower = -1
        self.secondaryeffectchance = None

        self.makedummymonster = 1
        self.makebattledummymonster = 0
        self.dummymonsternames = {}
        self.desiredmontagsize = -1
        self.unitmodlist = None
        self.names = {}

        self.selectunitmod = None

        self.lastsiteid = None
        self.lastsitename = None

        for param in UNITPARAMS:
            setattr(self, param, None)

    #TODO: this is a direct copy of the eventset code with only minor changes, there is potential to share much of this
    # (and it probably should go in the montagbuilder)
    def _generateUnit(self, numtogenerate, spell, secondaryeffect, actualpowerlvl):
        output = ""
        montag = montagbuilder.MontagBuilder()
        montag.makedummymonster = self.makedummymonster
        montag.makebattledummymonster = self.makebattledummymonster
        dummynames = self.dummymonsternames.get(spell.path1, [])
        if len(dummynames) > 0:
            montag.dummymonstername = naming.parsestring(random.choice(dummynames))
        for n in range(0, numtogenerate):

            # Find a unit to use
            unittouse = None
            effectpool = []
            if self.usefixedunitid > 0:
                unittouse = unitinbasedatafinder.get(self.usefixedunitid)
                minnreff = 1
                costper = 1.0
                # Unitmod
            elif self.selectunitmod is not None:
                realunitmod = utils.unitmods[self.selectunitmod]
                # this unit mod should instead be a picker for a unit to grab
                # start by building a pool of spelleffects that we could use

                for effname, effect in utils.spelleffects.items():
                    if effect.effect == self.effectnumberforunits:  # ritual summon
                        unitid = effect.damage
                        # no montags
                        if unitid < 0:
                            continue
                        unitobj = unitinbasedatafinder.get(unitid)

                        if self.restrictunitstospellpaths > 0:
                            if not (effect.paths & spell.path1):
                                continue
                            if effect.secondarypathchance >= 85 and not (effect.secondarypaths & spell.path2):
                                continue

                        if realunitmod.compatibility(unitobj):
                            effectpool.append(effect)
                random.shuffle(effectpool)

            generateokay = False
            # Loop to deal with deadend failures
            # this is typically a bad unit choice for which there is no way to adjust
            # the power up/down with legal secondaries
            secondary = None

            print(f"Spell paths for this generation are {spell.path1} and {spell.path2}")


            while 1:
                if len(effectpool) > 0:
                    chosensummoneffect = effectpool.pop(0)
                    print(f"Consider effect {chosensummoneffect}, {len(effectpool)} remain after this ")
                    unittouse = chosensummoneffect.getUnit()
                    if chosensummoneffect.damage < 0:
                        print(f"Discard effect {chosensummoneffect}: it makes montag {chosensummoneffect.damage}")
                        continue

                elif unittouse is None:
                    #raise Exception(f"MagicSite {self.name} found no valid unit summon")
                    print(f"ERROR: {self.name} with paths {spell.path1} and {spell.path2} found no valid unit summon")
                    return None

                if (self.unitmodlist is not None or len(self.allowedunitmods) > 0) and unittouse is not None:
                    # If rollSpell enforces a secondary effect (unlikely), use that
                    if secondaryeffect.name != "Do Nothing" and len(secondaryeffect.unitmod) > 0:
                        realunitmod = utils.unitmods[secondaryeffect.unitmod]
                        unitobj = unittouse
                        if not realunitmod.compatibility(unitobj):
                            print(f"Forced unitmod {realunitmod.name} not allowed with unit {unittouse}")
                            unittouse = None
                            continue
                        output = f"-- EventSet {self.name} applied secondary effect unitmod {realunitmod.name} " \
                                 f"to {unittouse.uniqueid}\n\n" + output
                        secondary = utils.unitmodToSecondary(realunitmod, fallback=True)
                    else:
                        # Find a secondary effect to use for this creature
                        if self.secondaryeffectchance is not None and random.random() * 100 > self.secondaryeffectchance:
                            realunitmod = utils.unitmods["Do Nothing"]
                            secondary = utils.unitmodToSecondary(realunitmod, fallback=True)
                        else:
                            # shallow copy
                            unitmodlist = self.allowedunitmods[:]
                            if self.unitmodlist is not None:
                                unitmodlist += utils.unitmodlists[self.unitmodlist]
                            random.shuffle(unitmodlist)
                            bad = False
                            while 1:
                                if len(unitmodlist) == 0:
                                    print(f"No valid unitmod for unit {unittouse}")
                                    bad = True
                                    break
                                unitmodtouse = unitmodlist.pop(0)
                                realunitmod = utils.unitmods[unitmodtouse]

                                # Find the parent secondary effect to test it for paths
                                secondary = utils.unitmodToSecondary(realunitmod, fallback=True)

                                # Montags are only allowed do nothing
                                if unittouse.id < 0 and secondary.name != "Do Nothing":
                                    print(f"Block secondary {secondary.name}: summons montag {unittouse} "
                                          f"so only Do Nothing allowed")
                                    continue

                                if self.restrictunitstospellpaths > 0:
                                    # Allow Do Nothing through!
                                    if secondary is not None and secondary.paths != 0:
                                        primarypathmatch = spell.path1 & secondary.paths
                                        secondarypathmatch = spell.path2 & secondary.paths
                                        if spell.path2 <= 0:
                                            secondarypathmatch = False
                                        if not primarypathmatch and not secondarypathmatch:
                                            print(f"Discarded secondary {secondary.name}: needs paths {spell.path1} or "
                                                  f"{spell.path2} (allowed is {secondary.paths}), {len(unitmodlist)}"
                                                  f" remain")
                                            continue

                                # Enforce power restrictions
                                if self.mincreaturepower > -1 and self.maxcreaturepower > -1:
                                    finalcreaturepower = chosensummoneffect.power - secondary.power
                                    minpower = self.mincreaturepower + actualpowerlvl
                                    maxpower = self.maxcreaturepower + actualpowerlvl
                                    if finalcreaturepower > maxpower or finalcreaturepower < minpower:
                                        print(f"Discarded {chosensummoneffect.name} + {secondary.name} combo - "
                                              f"final power was {finalcreaturepower} and desired was between "
                                              f"{minpower} and {maxpower}")
                                        continue
                                    print(f"Accepted {chosensummoneffect.name} + {secondary.name} combo - "
                                          f"final power was {finalcreaturepower} and desired was between "
                                          f"{minpower} and {maxpower}")

                                unitobj = unittouse
                                if not realunitmod.compatibility(unitobj):
                                    continue

                                print(f"Successfully picked secondary {secondary.name} for {unittouse}")

                                output = f"-- MagicSite {self.name} applied non-secondary effect unitmod " \
                                         f"{realunitmod.name} to {unittouse.uniqueid}\n\n" + output
                                break

                            if bad:
                                # There was no unitmod, start by finding another chassis
                                unittouse = None
                                continue

                    if numtogenerate == 1:
                        unitcode = realunitmod.applytounit(None, unittouse)
                        if self.modulegroup is None:
                            output = unitcode + "\n\n" + output
                        else:
                            self.moduletailingcode += unitcode + "\n"

                        generateokay = True
                    else:
                        # work out the effective fatigue cost
                        scaleportion = chosensummoneffect.nreff // 1000
                        minnreff = (scaleportion * chosensummoneffect.pathlevel) + chosensummoneffect.nreff % 1000
                        basecostper = chosensummoneffect.fatiguecost / minnreff

                        # Secondary modification
                        fatiguemult = 1.0
                        if secondary is not None:
                            for attrib, val in secondary.multcommands:
                                if attrib == "fatiguecost":
                                    fatiguemult *= val

                        # The chassis/paths split for commanders
                        if chosensummoneffect.chassisvalue is not None and secondary is not None:
                            chosensummoneffect.calcchassisvalues()
                            magiccostmod = chosensummoneffect.magicvaluepercent * basecostper * secondary.magicpathvaluescaling * fatiguemult
                            chassiscostmod = chosensummoneffect.chassisvaluepercent * basecostper * (fatiguemult - 1.0)
                            costper = int(
                                basecostper *
                                (chosensummoneffect.magicvaluepercent + chosensummoneffect.chassisvaluepercent)
                                + magiccostmod + chassiscostmod)
                            costper += secondary.fatiguecostpereffect
                        elif secondary is None:
                            costper = basecostper
                        else:
                            costper = basecostper * fatiguemult
                            costper += secondary.fatiguecostpereffect

                        basepower = chosensummoneffect.power

                        montag.add(unittouse, secondary, costper)
                        generateokay = True

                if realunitmod.lastparentid is not None and numtogenerate == 1:
                    output = output.replace("UNITID", str(realunitmod.lastparentid))
                    output = f"-- EventSet {self.name} called by {spelleffect.name} generated with unitid " \
                             f"{realunitmod.lastparentid}\n\n" + output

                if generateokay:
                    break
        return (output, montag)


    def formatdata(self, spelleffect, spell, scaleamt, secondaryeffect, actualpowerlvl):
        siteid = copy.copy(utils.SITE_ID)
        utils.SITE_ID += 1
        output = f"#newsite {siteid}\n"

        names = self.names.get(spell.path1, [f"{self.name} {random.randint(-1000, 1000)}"])[:]
        chosenname = random.choice(names)
        formatted = naming.parsestring(chosenname)
        while formatted in utils.magicsitenames:
            formatted += " "
            if len(formatted) > 35:
                raise ValueError("Magic site name too long")
        utils.magicsitenames.append(formatted)
        self.lastsitename = formatted
        self.lastsiteid = siteid
        output += "#name {}{}{}\n".format('"', formatted, '"')
        path = int(math.log(spell.path1, 2))
        output += f"#path {path}\n"
        # Basic params
        for param in self.params:
            if param in self.scaleparams:
                scaleweight = self.scaleparams[param]
                output += f"-- Scaling param {param} with weight {scaleweight}\n"
                newparamval = int((scaleweight * scaleamt) + getattr(self, param))
                output += f"#{param} {newparamval}\n"
            else:
                paramval = getattr(self, param)
                if paramval is not None and paramval != 0:
                    output += f"#{param} {getattr(self, param)}\n"

        # Unit params
        generatedunitid = None
        outputsuffix = ""
        numtogenerate = max(1, math.floor(self.desiredmontagsize * utils.MONTAG_SCALE))

        for param in UNITPARAMS:
            paramval = getattr(self, param, None)
            if paramval is not None:
                if generatedunitid is not None:
                    output += f"#{param} {generatedunitid}\n"
                else:
                    retval = self._generateUnit(numtogenerate, spell, secondaryeffect, actualpowerlvl)
                    if retval is None:
                        return None
                    unitcode, montag = retval
                    montagoutput = montag.process()
                    output = unitcode + "\n\n\n" + montagoutput.modcmds + "\n\n\n" + output
                    if self.makedummymonster or self.makebattledummymonster:
                        generatedunitid = montagoutput.dummymonsterid
                    else:
                        generatedunitid = -1*montagoutput.montagid

                    if montagoutput.numcreatures > 16:
                        outputsuffix = outputsuffix + f"-- Montag#{montagoutput.montagid}\n"
                        for line in montagoutput.weightingstring.split("\n"):
                            outputsuffix = outputsuffix + "--" + line + "\n"
                        outputsuffix += "\n"
                        spell.details += "\n" + f"For details on the creatures and weightings of this spell, search " \
                                                f"the mod file for 'Montag#{montagoutput.montagid}'."
                    else:
                        spell.details += "\n" + montagoutput.weightingstring

                    output += f"#{param} {generatedunitid}\n"

        output += "#end\n"
        output += outputsuffix
        output += "\n"
        return output