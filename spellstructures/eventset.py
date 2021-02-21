from . import utils
import copy
import re
import random
import math
from spellstructures import unit
import montagbuilder

UNITMOD_TO_SECONDARY_CACHE = {}

def _getscaleamt(L, rate):
    return rate * ((L*(L + 1)) / 2)

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
        self.modules = {}
        self.modulegroup = None
        self.incompatibilities = []

        self.rawdata = ""

        # For passing the unit name back...
        self.lastunitname = None

        # The below is for module reqs ONLY
        self.reqs = []
        self.minpowerlevel = None
        self.maxpowerlevel = None
        self.nouns = []
        self.verbs = []
        self.textrepls = {}
        self.moduledescr = ""
        self.moduledetails = ""
        self.modulebasescale = None
        self.makedummymonster = 1
        self.moduleskipchance = 0

        self.moduletailingcode = ""


    def moduleCompatibility(self, current, spelleffect, spell, scaleamt, secondaryeffect, actualpowerlvl, modules,
                           selection):
        islast = False
        if len(selection) + 1 == len(self.modules):
            islast = True

        for req in current.reqs:
            if not req.test(spell):
                print(f"Module {current.name} is not compatible: missing req")
                return False

        for realmod in selection:
            if current.name in realmod.incompatibilities:
                print(f"Module {current.name} is not compatible: specific incompatibilities")
                return False

        if islast:
            totalmin = 0
            totalmax = 0
            for realmod in selection:
                totalmin += realmod.minpowerlevel
                totalmax += realmod.maxpowerlevel
            totalmin += current.minpowerlevel
            totalmax += current.maxpowerlevel

            if totalmin <= actualpowerlvl <= totalmax:
                pass
            else:
                print(f"Module {current.name} is not compatible: power level out of range")
                return False

        print(f"Module {current.name} is compatible!")
        return True


    def _pickmodules(self, spelleffect, spell, scaleamt, secondaryeffect, actualpowerlvl, modules, selection=None):
        "Recursive module picker."
        if selection is None:
            selection = []
        if len(modules) == 0:
            return []
        # shallow copy
        considerations = utils.eventmodulegroups[modules[0]][:]
        remainingmodules = modules[1:]
        random.shuffle(considerations)
        while 1:
            if len(considerations) == 0:
                print(f"No more considerations for {self.name} on effect {spelleffect.name}")
                return None
            current = considerations.pop(0)
            if random.random() * 100 < current.moduleskipchance:
                if len(considerations) > 0:
                    considerations.append(current)
                    continue

            if self.moduleCompatibility(current, spelleffect, spell, scaleamt,
                                        secondaryeffect, actualpowerlvl, modules, selection):
                if len(remainingmodules) == 0:
                    return [current]
                else:
                    proposedselection = selection[:]
                    proposedselection.append(current)
                    print(f"Pick {current.name}, begin recursive with {[x.name for x in proposedselection]}")
                    remainder = self._pickmodules(spelleffect, spell, scaleamt,
                                             secondaryeffect, actualpowerlvl, remainingmodules, proposedselection)
                    if remainder is not None:
                        return [current] + remainder


    def _assignPowerLevels(self, modulepicks, modulesbypowerlevel, powerlevelsleft, picksleft=None):
        # Start with smallest deviations, as there is less chance to backtrack on a choice


        powerlevels = list(modulesbypowerlevel.keys())
        powerlevels.sort()

        if picksleft == 0:
            return {}

        # Find the module to assign this call
        done = False
        for powerlevel in powerlevels:
            for module in modulesbypowerlevel[powerlevel]:
                if module in modulepicks:
                    done = True
                    break

            if done:
                break

        # Sanity
        if not done:
            raise ValueError(f"Eventset {self.name} can't find a module in the list! {modulepicks}")
        print(f"There are {powerlevelsleft} power levels left")
        powerlevelrange = list(range(0, powerlevel+1))
        random.shuffle(powerlevelrange)

        nextassignment = modulepicks[:]
        nextassignment.remove(module)


        while 1:
            if len(powerlevelrange) == 0:
                raise ValueError(f"No power level to assign to {module.name} for {self.name}?")
            attempt = powerlevelrange.pop(0)
            attempt += module.minpowerlevel
            if picksleft == 1:
                attempt = powerlevelsleft
                print(f"This is the last module, attempt to assign all {attempt} left")
            print(f"Attempt to assign {attempt} power levels")
            powerlevelsleft -= attempt

            ret = self._assignPowerLevels(nextassignment, modulesbypowerlevel, powerlevelsleft, picksleft - 1)
            if ret is not None:
                ret[module.name] = attempt
                return ret
            powerlevelsleft += attempt

            if picksleft == 1:
                return None

        return None



    def formatdata(self, spelleffect, spell, scaleamt, secondaryeffect, actualpowerlvl, enchantid=None):
        "Format the data of this EventSet for the given parameters. Returns None on failure (and the spell should be aborted)"
        print(f"Begin formatdata for {self.name}")
        output = f"-- Generated from EventSet {self.name}, scaleamt = {scaleamt}; powerlevel = {actualpowerlvl}\n" \
                 + copy.copy(self.rawdata)

        self.moduletailingcode = ""


        # Get an enchant ID first, as any submodules need to know it
        # These are various local and global enchantment effect IDs
        if spelleffect.effect in [10081, 10082, 10083, 10084, 10085, 10086]:
            # only take an enchant id if the spell actually wants one
            if "ENCHANTID" in output:
                if enchantid is None:
                    enchantid = copy.copy(utils.ENCHANTMENT_ID)
                    utils.ENCHANTMENT_ID += 1
                output = output.replace("ENCHANTID", str(enchantid))
                spell.damage = copy.copy(enchantid)

        # Work out the modules we are going to use, if any, and modify actualpowerlvl accordingly

        moduledata = {}
        realmodules = []
        replacements = []

        for replacement, modulename in self.modules.items():
            realmodule = utils.eventmodulegroups[modulename]
            realmodules.append(realmodule)
            replacements.append(replacement)

        modulelist = list(self.modules.values())

        modulepicks = self._pickmodules(spelleffect, spell, scaleamt, secondaryeffect, actualpowerlvl, modulelist)
        if modulepicks is None:
            print(f"ERROR: No module picks for {self.name}")
            return None
        print(f"Module picks are {modulepicks}")

        # Decide on the power levels for each module
        minpowerlevel = 0
        maxpowerlevel = 0
        # The picking process makes sure that actualpowerlvl is somewhere between the min and max
        modulesbypowerlevel = {}
        for module in modulepicks:
            minpowerlevel += module.minpowerlevel
            maxpowerlevel += module.maxpowerlevel
            dev = module.maxpowerlevel - module.minpowerlevel
            if dev not in modulesbypowerlevel:
                modulesbypowerlevel[dev] = []
            modulesbypowerlevel[dev].append(module)

        powerlevelsleft = actualpowerlvl

        # Recursively find a solution that all modules accept
        # this is quite unoptimised and will get increasingly bad as you add more modules
        # due to testing the same thing in different orders
        powerlevelassignments = self._assignPowerLevels(modulepicks, modulesbypowerlevel, powerlevelsleft, len(modulelist))
        print(f"Power assignments picks are {powerlevelassignments}")

        tailcode = ""

        for i, module in enumerate(modulepicks):
            replacement = replacements[i]
            powerlevel = powerlevelassignments[module.name]
            moduledata[replacement] = module.formatdata(spelleffect, spell,
                                                        _getscaleamt(powerlevel-module.minpowerlevel, spelleffect.scalerate),
                                                        secondaryeffect, powerlevel, enchantid)
            if moduledata[replacement] is None:
                print(f"ERROR: formatdata for module {module.name} failed")
                return None
            print(f"Add {len(moduledata[replacement])} bytes of replacement code from module {module.name} to tag {replacement}")
            print(f"Add {len(module.moduletailingcode)} bytes of tail code from module {module.name}")
            tailcode += module.moduletailingcode + "\n"



        while 1:
            replmade = False
            for replacement, data in moduledata.items():
                for replacement2, data2 in moduledata.items():
                    if replacement2 in data:
                        print(f"Made one replacement for module symbol {replacement2} with length {len(data2)}")
                        moduledata[replacement] = data.replace(replacement2, data2)
                        replmade = True
                        break
                if replmade:
                    break
            if not replmade:
                break



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
                    print(f"Scaled event param {paramname} with weight {scaleweight} by {scaleweight * scaleamt}")
                    currlist[index] = re.sub(f"#{paramname}\\W+?([-0-9]*)", f"#{paramname} {newparamval}", line,
                                             count=1)
            output = "\n".join(currlist)

        numtogenerate = max(1, math.floor(self.desiredmontagsize * utils.MONTAG_SCALE))

        if numtogenerate > 1:
            montag = montagbuilder.MontagBuilder()
            montag.makedummymonster = self.makedummymonster

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
                    if effect.effect == 10001:  # ritual summon
                        unitid = effect.damage
                        # no montags
                        if unitid < 0:
                            continue
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
                    if unittouse < 0:
                        print(f"Discard effect {chosensummoneffect}: it makes montag {unittouse}")
                        continue

                elif unittouse is None:
                    # raise Exception(f"EventSet {self.name} called by {spelleffect.name} found no valid unit summon")
                    print(f"ERROR: {self.name} called by {spelleffect.name} found not valid unit summon")
                    return None

                if len(self.allowedunitmods) > 0 and unittouse is not None:
                    # If rollSpell enforces a secondary effect (unlikely), use that
                    if secondaryeffect.name != "Do Nothing" and len(secondaryeffect.unitmod) > 0:
                        realunitmod = utils.unitmods[secondaryeffect.unitmod]
                        unitobj = unit.get(unittouse)
                        if not realunitmod.compatibility(unitobj):
                            print(f"Forced unitmod {realunitmod.name} not allowed with unit {unittouse}")
                            unittouse = None
                            continue
                        output = f"-- EventSet {self.name} applied secondary effect unitmod {realunitmod.name} " \
                                 f"to {unittouse}\n\n" + output
                        secondary = utils.unitmodToSecondary(realunitmod, fallback=True)
                    else:
                        # Find a secondary effect to use for this creature
                        if self.secondaryeffectchance is not None and random.random() * 100 > self.secondaryeffectchance:
                            realunitmod = utils.unitmods["Do Nothing"]
                            secondary = utils.unitmodToSecondary(realunitmod, fallback=True)
                        else:
                            # shallow copy
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

                                # Montags are only allowed do nothing
                                if unittouse < 0 and secondary.name != "Do Nothing":
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

                                unitobj = unit.get(unittouse)
                                if not realunitmod.compatibility(unitobj):
                                    continue

                                print(f"Successfully picked secondary {secondary.name} for {unittouse}")

                                output = f"-- EventSet {self.name} applied non-secondary effect unitmod " \
                                         f"{realunitmod.name} to {unittouse}\n\n" + output
                                break

                            if bad:
                                # There was no unitmod, start by finding another chassis
                                unittouse = None
                                continue

                    if numtogenerate == 1:
                        unitcode = realunitmod.applytounitid(None, unittouse)
                        unittouse = realunitmod.lastparentid
                        self.lastunitname = realunitmod.lastunitname
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
                    output = f"-- EventSet {self.name} called by {spelleffect.name} generated with unitid " \
                             f"{unittouse}\n\n" + output

                if generateokay:
                    break

        if self.modulegroup is not None:
            print(f"Writing module description for {self.name}")
            if self.modulebasescale is not None:
                realscaleamt = self.modulebasescale
                # bit of a dodge, assume that you only have one scale param
                val = None
                for key, value in self.scaleparams.items():
                    if val is None:
                        val = value
                    if val != value and "SCALEAMT" in self.moduledetails:
                        raise NotImplementedError(f"Module {self.name} has a SCALEAMT in its details and more than one "
                                                  f"different parameter scale rate - unsupported operation")

                if val is None:
                    val = 1
                realscaleamt += (val * scaleamt)
                realscaleamt = int(realscaleamt)
            else:
                realscaleamt = f"[Missing modulebasescale for module {self.name}]"

            spell.descr = spell.descr + " " + self.moduledescr
            spell.details = spell.details + " " + self.moduledetails.replace("SCALEAMT", str(realscaleamt))
        else:
            # do module textrepl stuff
            for module in modulepicks:
                for symbol, replacement in module.textrepls.items():
                    spell.descr = spell.descr.replace(symbol, replacement)

            print(f"Attempt naming: number of modules picked = {len(modulepicks)}")
            if len(modulepicks) > 0:
                # Pick noun and verb name combo
                # the usual shallow copy + pop stuff is probably okay
                picks = modulepicks[:]
                random.shuffle(picks)
                try:
                    noun = random.choice(picks.pop(0).nouns)
                    print(f"Selected noun is {noun}")
                    verb = random.choice(picks.pop(0).verbs)
                    print(f"Selected verb is {verb}")
                    # Write the name into the parent spelleffect
                    # this is necessary so it goes through all the normal name logic that protects against
                    spelleffect.names[spell.path1] = [f"{verb} {noun}"]
                except IndexError:
                    # random.choice on empty list
                    print(f"One of the modules in {[x.name for x in modulepicks]} was missing a noun or verb,"
                          f" skip name assignment")
                    pass
                # ONLY do this if modules were picked, other eventset spells set this normally
                spelleffect.descriptions[spell.path1] = spell.descr

        if numtogenerate > 1:
            result = montag.process()
            resultcmds = result.modcmds
            if self.makedummymonster:
                output = output.replace("UNITID", str(result.dummymonsterid))
            else:
                output = output.replace("UNITID", str(-1*result.montagid))
            if self.modulegroup is None:
                output += resultcmds
            else:
                self.moduletailingcode += resultcmds
            if result.numcreatures > 16:
                for line in result.weightingstring.split("\n"):
                    output = output + "--" + line + "\n"
                output += "\n"
                spell.details += "\n" + f"For details on the creatures and weightings of this spell, search " \
                                        f"the mod file for 'Montag#{result.montagid}'."
            else:
                spell.details += "\n" + result.weightingstring

        # module replacements

        while 1:
            replmade = False
            for replacement, data in moduledata.items():
                if replacement in output:
                    print(output)
                    print(f"Latereplace made one replacement for module symbol {replacement} with length {len(data)}")
                    output = output.replace(replacement, data)
                    print(output)
                    replmade = True
                    break
            if not replmade:
                break

        if self.modulegroup is None:
            output += tailcode
        else:
            self.moduletailingcode += tailcode

        print(f"EventSet {self.name} returning {len(output)} bytes of content")
        print(output)
        return output
