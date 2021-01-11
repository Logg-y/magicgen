from . import utils
import copy
import re
import random
import math
from spellstructures import unit
from . import montagbuilder

UNITMOD_TO_SECONDARY_CACHE = {}

class EventSet(object):
    def __init__(self):
        self.selectunitmod = None
        self.usefixedunitid = -1
        self.allowedunitmods = []

        self.restrictunitstospellpaths = -1

        self.mincreaturepower = -1
        self.maxcreaturepower = -1

        self.desiredmontagsize = -1
        self.secondaryeffectchance = None



        self.name = ""

        self.requiredcodes = 0
        self.scaleparams = {}

        self.rawdata = ""

        # For passing the unit name back...
        self.lastunitname = None

    def formatdata(self, spelleffect, spell, scaleamt, secondaryeffect, actualpowerlvl):
        "Format the data of this EventSet for the given parameters. Returns None on failure (and the spell should be aborted)"
        output = copy.copy(self.rawdata)

        # These are various local and global enchantment effect IDs
        if spelleffect.effect in [10081, 10082, 10083, 10084, 10085, 10086]:
            # only take an enchant id if the spell actually wants one
            if "ENCHANTID" in output:
                output = output.replace("ENCHANTID", str(utils.ENCHANTMENT_ID))
                spell.damage = copy.copy(utils.ENCHANTMENT_ID)
                utils.ENCHANTMENT_ID += 1

        for codeindex in range(0, self.requiredcodes):
            # Replacement of codes should be done backwards
            # this is purely so that CODE10 doesn't become <code1>0
            # on the offchance that anyone uses more than 9 codes for a single spell...
            realcodeid = self.requiredcodes - codeindex
            newcode = utils.EVENT_CODE
            output = output.replace(f"CODE{realcodeid}", str(newcode))
            utils.EVENT_CODE = utils.EVENT_CODE - 1

        for paramname, scaleweight in self.scaleparams.items():
            output = f"-- Scaling param {paramname} with weight {scaleweight}\n" + output
            currlist = output.split("\n")
            # Need to guarantee that each one only gets processed once
            for index, line in enumerate(currlist):
                m = re.search(f"#{paramname}\\W+?([-0-9]*)", output)
                if m is not None:
                    oldparamval = int(m.groups()[0])
                    # I don't THINK there are any legal float params for events
                    # but could be mistaken here...
                    newparamval = int((scaleweight * scaleamt) + oldparamval)
                    print(f"Scaled event param {paramname} with weight {scaleweight} by {scaleweight*scaleamt}")
                    currlist[index] = re.sub(f"#{paramname}\\W+?([-0-9]*)", f"#{paramname} {newparamval}", line, count=1)
            output = "\n".join(currlist)


        numtogenerate = max(1, math.floor(self.desiredmontagsize*utils.MONTAG_SCALE))

        if numtogenerate > 1:
            montag = montagbuilder.MontagBuilder()
            montag.makedummymonster = True

        for n in range(0, numtogenerate):

            # Find a unit to use
            unittouse = None
            effectpool = []
            if self.usefixedunitid > 0:
                unittouse = self.usefixedunitid
                minnreff = 1
                costper = 1.0
                # Unitmod
            elif self.selectunitmod is not None:
                realunitmod = utils.unitmods[self.selectunitmod]
                # this unit mod should instead be a picker for a unit to grab
                # start by building a pool of spelleffects that we could use

                for effname, effect in utils.spelleffects.items():
                    if effect.effect == 10001: #ritual summon
                        unitid = effect.damage
                        unitobj = unit.get(unitid)

                        if self.restrictunitstospellpaths > 0:
                            if not (effect.paths & spell.path1):
                                continue
                            if effect.secondarypathchance >= 85 and not (effect.secondarypaths & spell.path2):
                                continue

                        if realunitmod.compatibility(unitobj):
                            effectpool.append(effect)
                random.shuffle(effectpool)

            if numtogenerate == 1 and self.selectunitmod is None and self.usefixedunitid <= 0:
                output = f"-- EventSet {self.name} called by {spelleffect.name} generated without unit\n\n" + output
                break

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
                    unittouse = chosensummoneffect.damage

                elif unittouse is None:
                    raise Exception(f"EventSet {self.name} called by {spelleffect.name} found no valid unit summon")
                    return None

                if len(self.allowedunitmods) > 0 and unittouse is not None:
                    # If rollSpell enforces a secondary effect (unlikely), use that
                    if secondaryeffect.name != "Do Nothing" and len(secondaryeffect.unitmod) > 0:
                        realunitmod = utils.unitmods[secondaryeffect.unitmod]
                        output = f"-- EventSet {self.name} applied secondary effect unitmod {realunitmod.name} " \
                                 f"to {unittouse}\n\n" + output
                        secondary = utils.unitmodToSecondary(realunitmod, fallback=True)
                    else:
                        # Find a secondary effect to use for this creature
                        # shallow copy
                        if self.secondaryeffectchance is not None and random.random() * 100 > self.secondaryeffectchance:
                            realunitmod = utils.unitmods["Do Nothing"]
                            secondary = utils.unitmodToSecondary(realunitmod, fallback=True)
                        else:
                            unitmodlist = self.allowedunitmods[:]
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

                                if self.restrictunitstospellpaths > 0:
                                    # Allow Do Nothing through!
                                    print(f"Check secondary...")
                                    if secondary is not None and secondary.paths != 0:
                                        print(f"secondary has paths {secondary.paths}")
                                        if not (spell.path1 & secondary.paths) and not (spell.path2 & secondary.paths):
                                            print(f"Discarded secondary {secondary.name}: needs paths {spell.path1} or "
                                                  f"{spell.path2}, {len(unitmodlist)} remain")
                                            continue


                                # Enforce power restrictions
                                if self.mincreaturepower > -1 and self.maxcreaturepower > -1:
                                    finalcreaturepower = chosensummoneffect.power + secondary.power
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

                                unitobj = unit.get(unittouse)
                                if not realunitmod.compatibility(unitobj):
                                    continue

                                print(f"Successfully picked secondary {secondary.name} for {unittouse}")

                                output = f"-- EventSet {self.name} applied non-secondary effect unitmod " \
                                         f"{realunitmod.name} to {unittouse}\n\n" + output
                                break

                            if bad:
                                # There was no unitmod, start by finding another chassis
                                continue

                    if numtogenerate == 1:
                        unitcode = realunitmod.applytounitid(None, unittouse)
                        unittouse = realunitmod.lastparentid
                        self.lastunitname = realunitmod.lastunitname
                        output = unitcode + "\n\n" + output
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


                if unittouse is not None and numtogenerate == 1:
                    output = output.replace("UNITID", str(unittouse))
                    output = f"-- EventSet {self.name} called by {spelleffect.name} generated with unitid {unittouse}\n\n"


                if generateokay:
                    break

        if numtogenerate > 1:
            result = montag.process()
            output += result.modcmds
            output = output.replace("UNITID", str(result.dummymonsterid))
            if result.numcreatures > 10:
                for line in result.weightingstring.split("\n"):
                    output = output + "--" + line + "\n"
                output += "\n"
                spell.details += "\n" + f'For details on the creatures and weightings of this spell, search ' \
                                        f'the mod file for "Montag#{result.montagid}".'
            else:
                spell.details += "\n" + result.weightingstring



        return output
