from DataObject.MontagResult import MontagResult
from Services import utils
from fileparser import unitinbasedatafinder
import math

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
        self.extremeCostRarity = 2.0
    def add(self, unitobj, secondaryeffect, costratio):
        """Add a unit to the montag with the given secondary effect. Cost ratio should be a pessimistic estimate of:

        gems / number of effects
        (IE: the cost in gems per one creature)
        """

        for i, data in enumerate(self.unitlist):
            unitobj2 = data[0]
            secondaryeffect2 = data[1]
            costratio2 = data[2]
            if unitobj2.uniqueid == unitobj.uniqueid and secondaryeffect2 == secondaryeffect and costratio2 == costratio:
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
            # These values allow MRN transformation spells with reasonable odds of failure
            # as well as preventing any items being dropped while in this form
            out.modcmds += "#mr 15\n"
            out.modcmds += "#itemslots 262143\n"
            if self.dummymonstername is None:
                out.modcmds += f'#name "Dummy Montag {out.montagid}"' + "\n"
            else:
                out.modcmds += f'#name "{self.dummymonstername}"' + "\n"
            out.modcmds += f'#descr "This unit has no purpose except to spawn in a unit of montag {out.montagid}."' + "\n"
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
            out.modcmds += f'#descr "This unit has no purpose except to spawn in a unit of montag {out.montagid}."' + "\n"
            out.modcmds += "#end\n\n"
            out.dummymonsterid = utils.MONSTER_ID
            utils.MONSTER_ID += 1
        return out

