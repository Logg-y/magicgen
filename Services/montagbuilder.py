from DataObject.MontagResult import MontagResult
from Services import utils, naming
from fileparser import unitinbasedatafinder
import math
import random

class MontagBuilder(object):
    def __init__(self):
        self.unitlist = []
        self.maxcostratio = -1.0
        self.makedummymonster = False
        self.makebattledummymonster = False
        # Dict: <index of unitlist>:<number of times it was added>
        self.numberofcopies = {}
        self.dummymonstername = None

        # If True, cheaper creatures are more common.
        # If False, creatures closer to the mean cost are more common, with outliers in either direction being rarer
        self.usemaximumweightingmethod = False

        # For the mean cost = popular method, how to scale rarity as things get further from the mean
        # If mean is 10 and unit costs 20 or 5, its weight will be 1/(2**this value) that of something which cost 10
        # technically, weights are:

        # duplicates/(ratio**this value), where ratio is is max(mean, this unit)/min(mean, this unit)
        # this is why both 20 and 5 produce a ratio of 2 in the example above
        # Reducing this value will make the cost extremes of the montag less rare
        self.extremeCostRarity = 1.5
    def add(self, unitobj, secondaryeffect, costratio):
        """Add a unit to the montag with the given secondary effect. Cost ratio should be a pessimistic estimate of:

        gems / number of effects
        (IE: the cost in gems per one creature)
        """

        for i, data in enumerate(self.unitlist):
            unitobj2 = data[0]
            secondaryeffect2 = data[1]
            costratio2 = data[2]
            if unitobj2.uniqueid == unitobj.uniqueid and secondaryeffect2 == secondaryeffect:
                self.numberofcopies[i] = self.numberofcopies.get(i, 1) + 1
                return

        self.unitlist.append((unitobj, secondaryeffect, costratio))
        self.maxcostratio = max(self.maxcostratio, costratio)
    def _calculateCostratioMaxWeightMethod(self, data, i):
        "Calculate costratio (gems per unit) for the given data triplet, taking into account number of duplicates"
        unitobj = data[0]
        secondaryeffect = data[1]
        # Adjust for multiple copies of the same thing
        costratio = data[2]
        duplicates = self.numberofcopies.get(i, 1)
        costratio = max(1, costratio / duplicates)
        return costratio

    def process(self, spell=None, secondaryeffect=None):
        out = MontagResult()
        out.numcreatures = len(self.unitlist)
        out.montagid = utils.MONTAG_ID
        weighttotal = 0
        maxweight = 0

        # maximum weighting method only
        if self.usemaximumweightingmethod:
            # quickly get the weight total, it is useful later
            for i, data in enumerate(self.unitlist):
                costratio = self._calculateCostratioMaxWeightMethod(data)

                montagweight = math.floor(self.maxcostratio / costratio)
                # the mod command only accepts 1-100
                montagweight = max(1, min(100, montagweight))
                maxweight = max(maxweight, montagweight)
                weighttotal += montagweight

        else:
            # Get the total costratio
            costratiototal = 0
            totalitems = 0
            for i, data in enumerate(self.unitlist):
                unitobj = data[0]
                secondaryeffect = data[1]
                # Adjust for multiple copies of the same thing
                costratio = data[2]
                duplicates = self.numberofcopies.get(i, 1)
                totalitems += duplicates
                costratiototal += (costratio * duplicates)
            costratiomean = costratiototal/totalitems
            print(f"Mean costratio is {costratiomean}")

            # Now, work out maxweight
            for i, data in enumerate(self.unitlist):
                unitobj = data[0]
                secondaryeffect = data[1]
                # Adjust for multiple copies of the same thing
                costratio = data[2]
                duplicates = self.numberofcopies.get(i, 1)
                print(f"Costratio for {data} is {costratio}")
                montagweight = duplicates/ \
                               ((max(costratio, costratiomean)/min(costratio, costratiomean))**self.extremeCostRarity)
                weighttotal += montagweight
                maxweight = max(montagweight, maxweight)

        weightmultiplier = 100 / maxweight
        weighttotal *= weightmultiplier
        weighttotal = math.floor(weighttotal)


        if utils.MONTAG_ID > 100000:
            # This is probably never ever going to happen but hey
            raise ValueError("Ran out of montag IDs, the game would reject this mod. Consider revising ID settings"
                             " or reducing the number of montags that are being created")
        utils.MONTAG_ID += 1
        out.weightingstring = f"Units for this spell:\n\n"
        for i, data in enumerate(self.unitlist):
            unitobj = data[0]
            secondary = data[1]
            duplicates = self.numberofcopies.get(i, 1)

            if self.usemaximumweightingmethod:
                costratio = _calculateCostratioMaxWeightMethod(data, i)
                montagweight = math.floor((weightmultiplier*self.maxcostratio)/costratio)
            else:
                # Adjust for multiple copies of the same thing
                costratio = data[2]
                montagweight = duplicates/ \
                               ((max(costratio, costratiomean)/min(costratio, costratiomean))**self.extremeCostRarity)
                montagweight *= weightmultiplier
                montagweight = math.floor(montagweight)

            # the mod command only accepts 1-100
            montagweight = max(1, min(100, montagweight))

            # If the secondary effect has a unitmod, use that
            # else use the legendary special unitmod "do nothing"!
            # (SOME kind of unit mod is needed to insert the montag commands)
            if len(secondary.unitmod) > 0:
                unitmod = utils.unitmods[secondary.unitmod]
            else:
                unitmod = utils.unitmods["Do Nothing"]
            modcmds = unitmod.applytounit(spell, unitobj, additionals_firstshape={"#montagweight":montagweight,
                                                                        "#montag":out.montagid},
                                          secondaryeffect=secondaryeffect)
            if self.usemaximumweightingmethod:
                modcmds = f"-- Montag: costratio was {costratio}, this unit was duplicated {duplicates} times," \
                          f" max for this montag was {self.maxcostratio}\n"  + modcmds
            else:
                modcmds = f"-- Montag: costratio was {costratio}, this unit was duplicated {duplicates} times," \
                          f" mean for this montag was {costratiomean}, weightmultiplier is {weightmultiplier}\n"\
                          + modcmds
            out.modcmds += modcmds + "\n"

            percentage = "{:.1f}%".format(montagweight/weighttotal * 100)

            unittoapplyto = unitobj
            woundshape = getattr(unittoapplyto, "secondshape", None)
            nametowrite = unitmod.lastunitname
            if woundshape is not None:
                for sizeindicator in ["Elemental", "Illearth", "Living Mercury"]:
                    if sizeindicator in unitmod.lastunitname:
                        nametowrite += f" (base size {unittoapplyto.size})"
                        break

            if secondary is None or len(unitmod.nameprefix) < 1:
                out.weightingstring += f"Weighting {montagweight} ({percentage}): {nametowrite} ({secondary.name})\n"
            else:
                out.weightingstring += f"Weighting {montagweight} ({percentage}): {nametowrite}\n"
        out.weightingstring += f"Total creatures: {out.numcreatures}; Sum of weights: {weighttotal}\n\n"
        out.weightingstring = out.weightingstring.replace("Do Nothing", "No Modifier")
        if self.makedummymonster:
            out.modcmds += f"#newmonster {utils.MONSTER_ID}\n"
            # 284: wolf - it's one of the youngest creatures the game
            out.modcmds += "#copystats 284\n"
            out.modcmds += "#copyspr 284\n"
            out.modcmds += f"#firstshape -{out.montagid}\n"
            out.modcmds += f"#secondshape -{out.montagid}\n"
            out.modcmds += f"#hp 1\n"
            out.modcmds += f"#woundfend 99\n"
            # Prevent drowning
            out.modcmds += "#amphibian\n"
            # Prevent anything built this way enters the vanilla transformation pool (as it's a wolf it defaults to included)
            out.modcmds += "#transformation 0\n"
            # These values allow MRN transformation spells with reasonable odds of failure
            # as well as preventing any items being dropped while in this form
            out.modcmds += "#mr 15\n"
            out.modcmds += "#itemslots 262143\n"
            if self.dummymonstername is None:
                out.modcmds += f'#name "Dummy Montag {out.montagid}"' + "\n"
            else:
                out.modcmds += f'#name "{self.dummymonstername}"' + "\n"
            out.modcmds += f'#descr "This unit has no purpose except to spawn in a unit of montag {out.montagid}, which it will do after battle or if this form is killed."' + "\n"
            out.modcmds += "#end\n\n"
            out.dummymonsterid = utils.MONSTER_ID
            utils.MONSTER_ID += 1
        elif self.makebattledummymonster:
            out.modcmds += f"#newmonster {utils.MONSTER_ID}\n"
            # 284: wolf - it's one of the youngest creatures the game
            out.modcmds += "#copystats 284\n"
            out.modcmds += "#copyspr 284\n"
            out.modcmds += f"#firstshape -{out.montagid}\n"
            out.modcmds += f"#secondshape -{out.montagid}\n"
            out.modcmds += f"#regeneration -999\n"
            out.modcmds += f"#landdamage 100\n"
            out.modcmds += f"#uwdamage 100\n"
            out.modcmds += f"#drawsize -99\n"
            out.modcmds += f"#woundfend 99\n"
            out.modcmds += f"#hp 1\n"
            # Prevent drowning
            out.modcmds += "#amphibian\n"
            # These values allow MRN transformation spells with reasonable odds of failure
            # as well as preventing any items being dropped while in this form
            out.modcmds += "#mr 15\n"
            out.modcmds += "#itemslots 262143\n"
            if self.dummymonstername is None:
                out.modcmds += f'#name "Dummy Montag {out.montagid}"' + "\n"
            else:
                out.modcmds += f'#name "{self.dummymonstername}"' + "\n"
            out.modcmds += f'#descr "This unit has no purpose except to spawn in a unit of montag {out.montagid}, which it will rapidly do once in combat."' + "\n"
            out.modcmds += "#end\n\n"
            out.dummymonsterid = utils.MONSTER_ID
            utils.MONSTER_ID += 1
        return out

def _CanUseUnitAndSecondaryCombo(parentobj, unittouse, secondary, realunitmod, spell, chosensummoneffect,
                                 actualpowerlvl):
    # Montags are only allowed do nothing
    if unittouse.id < 0 and secondary.name != "Do Nothing":
        print(f"Block secondary {secondary.name}: summons montag {unittouse} "
              f"so only Do Nothing allowed")
        return False

    if parentobj.restrictunitstospellpaths > 0:
        # Allow Do Nothing through!
        if secondary is not None and secondary.paths != 0:
            primarypathmatch = spell.path1 & secondary.paths
            secondarypathmatch = spell.path2 & secondary.paths
            if spell.path2 <= 0:
                secondarypathmatch = False
            if not primarypathmatch and not secondarypathmatch:
                print(f"Discarded secondary {secondary.name}: needs paths {spell.path1} or "
                      f"{spell.path2} (allowed is {secondary.paths})")
                return False

    # Enforce power restrictions
    if chosensummoneffect is not None:
        finalcreaturepower = chosensummoneffect.power - secondary.power
        minpower = parentobj.mincreaturepower + actualpowerlvl
        maxpower = parentobj.maxcreaturepower + actualpowerlvl
        if finalcreaturepower > maxpower or finalcreaturepower < minpower:
            print(f"Discarded {chosensummoneffect.name} + {secondary.name} combo - "
                  f"final power was {finalcreaturepower} and desired was between "
                  f"{minpower} and {maxpower}")
            return False
        print(f"Accepted {chosensummoneffect.name} + {secondary.name} combo - "
              f"final power was {finalcreaturepower} and desired was between "
              f"{minpower} and {maxpower}")

    unitobj = unittouse
    # Unitmod and secondary modifier should agree with the unit and its parent effect
    # before being allowed!
    if not realunitmod.compatibility(unitobj):
        return False
    if chosensummoneffect is not None:
        if not secondary.compatibility(chosensummoneffect, modifier=utils.modifiers["Do Nothing"], researchlevel=chosensummoneffect.power+secondary.power):
            return False

    return True

def generateUnit(parentobj, numtogenerate, spell, secondaryeffect, actualpowerlvl):
    # When dealing with nextspell chains, we need to update #details on the first one (the one the players see)
    firstspell = spell
    while True:
        if firstspell.prevspell is None:
            break
        firstspell = firstspell.prevspell
    output = ""
    montag = MontagBuilder()
    montag.makedummymonster = parentobj.makedummymonster
    montag.makebattledummymonster = parentobj.makebattledummymonster
    dummynames = parentobj.dummymonsternames.get(spell.path1, [])
    if len(dummynames) > 0:
        montag.dummymonstername = naming.parsestring(random.choice(dummynames))
    for n in range(0, numtogenerate):

        # Find a unit to use
        unittouse = None
        effectpool = []
        if parentobj.usefixedunitid > 0:
            unittouse = unitinbasedatafinder.get(parentobj.usefixedunitid)
            minnreff = 1
            costper = 1.0
            chosensummoneffect = None
            # Unitmod
        elif parentobj.selectunitmods is not None and len(parentobj.selectunitmods) > 0:
            for selectunitmodname in parentobj.selectunitmods:
                realunitmod = utils.unitmods[selectunitmodname]
                # this unit mod should instead be a picker for a unit to grab
                # start by building a pool of spelleffects that we could use

                for effname, effect in utils.spelleffects.items():
                    if effect.effect in parentobj.effectnumberforunits:
                        unitid = effect.damage
                        # no montags
                        if unitid < 0:
                            continue
                        #unitobj = unitinbasedatafinder.get(unitid)

                        if parentobj.restrictunitstospellpaths > 0:
                            if not (effect.paths & spell.path1):
                                continue
                            if effect.secondarypathchance >= 85 and not (effect.secondarypaths & spell.path2):
                                continue

                        if realunitmod.compatibilityWithSpellEffect(effect):
                            effectpool.append(effect)
            random.shuffle(effectpool)

        generateokay = False
        # Loop to deal with deadend failures
        # this is typically a bad unit choice for which there is no way to adjust
        # the power up/down with legal secondaries
        secondary = None

        print(f"Spell paths for this generation are {spell.path1} and {spell.path2}")
        print(f"Effect pool contains {len(effectpool)} effects from {parentobj.selectunitmods}")


        while 1:
            if len(effectpool) > 0:
                chosensummoneffect = effectpool.pop(0)
                print(f"Consider effect {chosensummoneffect}, {len(effectpool)} remain after this ")
                unittouse = chosensummoneffect.getUnit()
                if chosensummoneffect.damage < 0:
                    print(f"Discard effect {chosensummoneffect}: it makes montag {chosensummoneffect.damage}")
                    continue

            elif unittouse is None:
                print(f"ERROR: {parentobj.name} with paths {spell.path1} and {spell.path2} found no valid unit summon")
                return None

            if (parentobj.unitmodlist is not None or len(parentobj.allowedunitmods) > 0) and unittouse is not None:
                # If rollSpell enforces a secondary effect (unlikely), use that
                if secondaryeffect is not None and secondaryeffect.name != "Do Nothing" and len(secondaryeffect.unitmod) > 0:
                    realunitmod = utils.unitmods[secondaryeffect.unitmod]
                    unitobj = unittouse
                    secondary = utils.unitmodToSecondary(realunitmod, fallback=True)
                    if not _CanUseUnitAndSecondaryCombo(parentobj, unitobj, secondary, realunitmod, spell,
                                                        chosensummoneffect, actualpowerlvl):
                        print(f"Forced unitmod {realunitmod.name} not allowed with unit {unittouse}")
                        unittouse = None
                        continue
                    output = f"-- {parentobj.name} applied secondary effect unitmod {realunitmod.name} " \
                             f"to {unittouse.uniqueid}\n\n" + output
                else:
                    # Find a secondary effect to use for this creature
                    if parentobj.secondaryeffectchance is not None and random.random() * 100 > parentobj.secondaryeffectchance:
                        realunitmod = utils.unitmods["Do Nothing"]
                        secondary = utils.unitmodToSecondary(realunitmod, fallback=True)
                    else:
                        # shallow copy
                        unitmodlist = parentobj.allowedunitmods[:]
                        if parentobj.unitmodlist is not None:
                            unitmodlist += utils.unitmodlists[parentobj.unitmodlist]
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

                            isvalid = _CanUseUnitAndSecondaryCombo(parentobj, unittouse, secondary, realunitmod, spell,
                                                                   chosensummoneffect, actualpowerlvl)
                            if not isvalid:
                                print(f"... {len(unitmodlist)} unitmods remain...")
                                continue

                            print(f"Successfully picked secondary {secondary.name} for {unittouse}")

                            output = f"-- {parentobj.name} applied non-secondary effect unitmod " \
                                     f"{realunitmod.name} to {unittouse.uniqueid}\n\n" + output
                            break

                        if bad:
                            # There was no unitmod, start by finding another chassis
                            unittouse = None
                            continue

                if numtogenerate == 1:
                    unitcode = realunitmod.applytounit(None, unittouse)
                    if parentobj.modulegroup is None:
                        output = unitcode + "\n\n" + output
                    else:
                        parentobj.moduletailingcode += unitcode + "\n"
                    parentobj.lastunitid = realunitmod.lastparentid
                    parentobj.lastunitname = realunitmod.lastunitname
                    if parentobj.usefixedunitid is None or parentobj.usefixedunitid < 0:
                        if "SINGLERANDOMCREATURENAME" in firstspell.details:
                            firstspell.details = firstspell.details.replace("SINGLERANDOMCREATURENAME",
                                                                            realunitmod.lastunitname, 1)
                        else:
                            firstspell.details += f" The creature for this spell is always a {realunitmod.lastunitname}."
                            firstspell.details = firstspell.details.strip()

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
                output = f"-- {parentobj.name} generated with unitid " \
                         f"{realunitmod.lastparentid}\n\n" + output

            if generateokay:
                break
    return (output, montag)
