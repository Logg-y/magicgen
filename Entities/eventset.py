import copy
import re
import random
import math
from fileparser import unitinbasedatafinder
from Services import montagbuilder, utils, naming

UNITMOD_TO_SECONDARY_CACHE = {}


def _getscaleamt(L, rate):
    return rate * ((L*(L + 1)) / 2)


class EventSet(object):
    def __init__(self):
        self.selectunitmods = None
        self.usefixedunitid = -1
        self.allowedunitmods = []

        self.restrictunitstospellpaths = -1

        self.mincreaturepower = -999
        self.maxcreaturepower = 999

        self.desiredmontagsize = -1
        self.secondaryeffectchance = None

        self.name = ""

        self.requiredcodes = 0
        self.scaleparams = {}
        self.scaleparammults = {}
        self.modules = {}
        self.modulegroup = None
        self.incompatibilities = []

        self.rawdata = ""

        # For passing the unit name back...
        self.lastunitname = None
        self.lastunitid = None
        self.unitmodlist = None

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
        self.makebattledummymonster = 0
        self.dummymonsternames = {}
        self.moduleskipchance = 0
        self.setspelldamage = 0
        self.magicsite = ""
        self.effectnumberforunits = []
        self.fixedcreaturepower = False

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

    def _getScaleAmountForBase(self, realscaleamt, scaleamt):
        """Return the scale amount for a property with the passed base value and spell scale amount.
        Assumes only one scale rate for all properties."""
        if realscaleamt is not None:
            # bit of a dodge, assume that you only have one scale param
            val = None
            for key, value in self.scaleparams.items():
                if val is None:
                    val = value
                if val != value:
                    raise NotImplementedError(f"Module {self.name} has more than one "
                                              f"different parameter scale rate - unsupported operation")

            if val is not None:
                realscaleamt += (val * scaleamt)
                realscaleamt = int(realscaleamt)
                print(f"Flat scale addition: {val} * scale amount {scaleamt} -> {realscaleamt}")
            val = None

            for key, value in self.scaleparammults.items():
                if val is None:
                    val = value
                if val != value:
                    raise NotImplementedError(f"Module {self.name} has a more than one "
                                              f"different parameter scale rate - unsupported operation")

            if val is not None and scaleamt != 0:
                print(f"Multiplicative scale addition: {val} * scale amount {scaleamt} * {realscaleamt}")
                realscaleamt += realscaleamt * val * scaleamt
                print(f"Multiplicative scale addition: result is {realscaleamt}")
            realscaleamt = int(realscaleamt)

        else:
            realscaleamt = f"[Missing modulebasescale for module {self.name}]"
        print(f"Final replacement is {realscaleamt}")
        return str(realscaleamt)

    def formatdata(self, spelleffect, spell, scaleamt, forcedsecondaryeffect, actualpowerlvl, enchantid=None):
        "Format the data of this EventSet for the given parameters. Returns None on failure (and the spell should be aborted)"
        print(f"Begin formatdata for {self.name}")
        output = f"-- Generated from EventSet {self.name}, scaleamt = {scaleamt}; powerlevel = {actualpowerlvl}\n" \
                 + copy.copy(self.rawdata)

        self.moduletailingcode = ""

        if len(self.effectnumberforunits) == 0:
            self.effectnumberforunits.append(10001)


        # Get an enchant ID first, as any submodules need to know it
        # These are various local and global enchantment effect IDs
        if spelleffect is not None and spelleffect.effect in [10081, 10082, 10083, 10084, 10085, 10086]:
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

        modulepicks = self._pickmodules(spelleffect, spell, scaleamt, forcedsecondaryeffect, actualpowerlvl, modulelist)
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
                                                        forcedsecondaryeffect, powerlevel, enchantid)
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
                m = re.search(f"#{paramname}\\W+?([-0-9]*)", line)
                if m is not None:
                    oldparamval = int(m.groups()[0])
                    # I don't THINK there are any legal float params for events
                    # but could be mistaken here...
                    newparamval = int((scaleweight * scaleamt) + oldparamval)
                    print(f"Scaled event param {paramname} with weight {scaleweight} by {scaleweight * scaleamt}")
                    currlist[index] = re.sub(f"#{paramname}\\W+?([-0-9]*)", f"#{paramname} {newparamval}", line,
                                             count=1)
            output = "\n".join(currlist)

        for paramname, scaleweight in self.scaleparammults.items():
            output = f"-- Scaling param (multiplicative) {paramname} with weight {scaleweight}\n" + output
            currlist = output.split("\n")
            # Need to guarantee that each one only gets processed once
            for index, line in enumerate(currlist):
                m = re.search(f"#{paramname}\\W+?([-0-9]*)", line)
                if m is not None:
                    oldparamval = int(m.groups()[0])
                    # I don't THINK there are any legal float params for events
                    # but could be mistaken here...
                    newparamval = int(oldparamval + (oldparamval * scaleweight * scaleamt))
                    print(f"Scaled event param {paramname} with weight {scaleweight} by {scaleweight * scaleamt}")
                    currlist[index] = re.sub(f"#{paramname}\\W+?([-0-9]*)", f"#{paramname} {newparamval}", line,
                                             count=1)
            output = "\n".join(currlist)

        if self.desiredmontagsize == 1:
            numtogenerate = 1
        else:
            if self.selectunitmods is None and self.usefixedunitid <= 0:
                numtogenerate = 0
            else:
                numtogenerate = max(1, math.floor(self.desiredmontagsize * utils.MONTAG_SCALE))

        if numtogenerate > 0:
            retval = montagbuilder.generateUnit(self, numtogenerate, spell, forcedsecondaryeffect, actualpowerlvl)
            if retval is None:

                return None
            unitcode, montag = retval

        if self.modulegroup is not None:
            print(f"Writing module description for {self.name}")
            while 1:
                m = re.search("[{]SCALEAMT-([0-9]*)[}]", self.moduledetails)
                if m is None:
                    break
                base = int(m.groups()[0])
                replamt = self._getScaleAmountForBase(base, scaleamt)
                stringtoreplace = "{SCALEAMT-" + str(base) + "}"
                self.moduledetails = self.moduledetails.replace(stringtoreplace, replamt)
                print(f"Replace {stringtoreplace} with {replamt}")

            realscaleamt = self._getScaleAmountForBase(self.modulebasescale, scaleamt)

            spell.descr = spell.descr + " " + self.moduledescr
            spell.details = spell.details + " " + self.moduledetails.replace("SCALEAMT", str(realscaleamt))
            print(f"Replace SCALEAMT with {realscaleamt}")
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
                spelleffect.names[spell.path1] = []
                try:
                    noun = random.choice(picks.pop(0).nouns)
                    print(f"Selected noun is {noun}")
                    verb = random.choice(picks.pop(0).verbs)
                    print(f"Selected verb is {verb}")
                    # Write the name into the parent spelleffect
                    # this is necessary so it goes through all the normal name logic that protects against
                    spelleffect.names[spell.path1] = [f"{verb} {noun}".strip()]
                except IndexError:
                    # random.choice on empty list
                    picks = modulepicks[:]
                    random.shuffle(picks)
                    hasnouns = []
                    hasverbs = []
                    inboth = []
                    for pick in picks:
                        if len(pick.nouns) > 0:
                            hasnouns.append(pick)
                        if len(pick.verbs) > 0:
                            hasverbs.append(pick)
                        if len(pick.nouns) > 0 and len(pick.verbs) > 0:
                            inboth.append(pick)
                    if len(hasnouns) == 0:
                        print(f"All of the modules in {[x.name for x in modulepicks]} were missing nouns,"
                              f" skip name assignment")
                    elif len(hasverbs) == 0:
                        print(f"All of the modules in {[x.name for x in modulepicks]} were missing verbs,"
                              f" skip name assignment")
                    else:
                        if len(hasnouns) == len(inboth) and len(hasverbs) == len(inboth):
                            # If this is the case, the simple naming method would have worked
                            # unless only one module actually HAS name parts assigned
                            print(f"Only one of the modules in {[x.name for x in modulepicks]} has assigned name parts,"
                                  f" skip name assignment")
                        else:
                            usedalready = []
                            verb = None
                            noun = None
                            if len(hasnouns) == len(inboth):
                                random.shuffle(hasverbs)
                                for verbsource in hasverbs:
                                    if verbsource not in inboth:
                                        verb = random.choice(verbsource.verbs)
                                        usedalready.append(verbsource)
                                        break


                            if len(hasverbs) == len(inboth):
                                random.shuffle(hasnouns)
                                for nounsource in hasnouns:
                                    if nounsource not in inboth:
                                        noun = random.choice(nounsource.nouns)
                                        usedalready.append(nounsource)
                                        break

                            if noun is None:
                                random.shuffle(hasnouns)
                                for nounsource in hasnouns:
                                    if nounsource not in usedalready:
                                        noun = random.choice(nounsource.nouns)
                                        usedalready.append(nounsource)
                                        break

                            if verb is None:
                                random.shuffle(hasverbs)
                                for verbsource in hasverbs:
                                    if verbsource not in usedalready:
                                        verb = random.choice(verbsource.verbs)
                                        usedalready.append(verbsource)
                                        break

                            spelleffect.names[spell.path1] = [f"{verb} {noun}".strip()]
                    pass
                # ONLY do this if modules were picked, other eventset spells set this normally
                spelleffect.descriptions[spell.path1] = spell.descr

        if numtogenerate > 1:
            result = montag.process(spell=spell, secondaryeffect=forcedsecondaryeffect)
            self.lastunitid = -1*result.montagid
            resultcmds = result.modcmds

            if self.makedummymonster:
                output = output.replace("UNITID", str(result.dummymonsterid))
                if self.setspelldamage:
                    spell.damage = result.dummymonsterid
            else:
                output = output.replace("UNITID", str(-1*result.montagid))
                if self.setspelldamage:
                    spell.damage = -1*result.montagid
            if self.modulegroup is None:
                output = unitcode + "\n\n\n" + resultcmds + "\n\n\n" + output
            else:
                self.moduletailingcode += unitcode + "\n\n\n" + resultcmds + "\n\n\n" + output
            if result.numcreatures > 18:
                for line in result.weightingstring.split("\n"):
                    output = output + "--" + line + "\n"
                output += "\n"
                spell.details += "\n" + f"For details on the creatures and weightings of this spell, search " \
                                        f"the mod file for 'Montag#{result.montagid}'."
            else:
                spell.details += "\n" + result.weightingstring
        elif numtogenerate == 1:
            # Only one creature - don't need montags
            output = output.replace("UNITID", str(self.lastunitid))
            if self.modulegroup is None:
                output = unitcode + "\n\n\n" + output
            else:
                self.moduletailingcode += unitcode + "\n\n\n" + output

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

        if len(self.magicsite) > 0:
            magicsite = utils.magicsites[self.magicsite]
            sitedata = magicsite.formatdata(spelleffect, spell, scaleamt, forcedsecondaryeffect, actualpowerlvl)
            if sitedata is None:
                return None
            output += sitedata
            output = output.replace("SITEID", str(magicsite.lastsiteid))
            output = output.replace("SITENAME", magicsite.lastsitename)

        if self.modulegroup is None:
            output += tailcode
        else:
            self.moduletailingcode += tailcode



        print(f"EventSet {self.name} returning {len(output)} bytes of content")
        print(output)
        return output
