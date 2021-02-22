from DataObject.MontagResult import MontagResult
from Services import utils
import math

class MontagBuilder(object):
    def __init__(self):
        self.unitlist = []
        self.maxcostratio = -1.0
        self.makedummymonster = False
        # Dict: <index of unitlist>:<number of times it was added>
        self.numberofcopies = {}
    def add(self, unitid, secondaryeffect, costratio):
        """Add a unit to the montag with the given secondary effect. Cost ratio should be a pessimistic estimate of:

        gems / number of effects
        (IE: the cost in gems per one creature)
        """

        for i, data in enumerate(self.unitlist):
            unitid2 = data[0]
            secondaryeffect2 = data[1]
            costratio2 = data[2]
            if unitid2 == unitid and secondaryeffect2 == secondaryeffect and costratio2 == costratio:
                self.numberofcopies[i] = self.numberofcopies.get(i, 1) + 1
                return

        self.unitlist.append((unitid, secondaryeffect, costratio))
        self.maxcostratio = max(self.maxcostratio, costratio)
    def process(self):
        out = MontagResult()
        out.numcreatures = len(self.unitlist)
        out.montagid = utils.MONTAG_ID
        weighttotal = 0
        maxweight = 0
        # quickly get the weight total, it is useful later
        for i, data in enumerate(self.unitlist):
            unitid = data[0]
            secondaryeffect = data[1]
            # Adjust for multiple copies of the same thing
            costratio = data[2]
            duplicates = self.numberofcopies.get(i, 1)
            costratio = max(1, costratio/duplicates)

            montagweight = math.floor(self.maxcostratio / costratio)
            # the mod command only accepts 1-100
            montagweight = max(1, min(100, montagweight))
            maxweight = max(maxweight, montagweight)
            weighttotal += montagweight
        weightmultiplier = 100 / maxweight
        weighttotal *= weightmultiplier
        weighttotal = math.floor(weighttotal)

        if utils.MONTAG_ID > 100000:
            # This is probably never ever going to happen but hey
            raise ValueError("Ran out of montag IDs, the game would reject this mod. Consider revising ID settings"
                             " or reducing the number of montags that are being created")
        utils.MONTAG_ID += 1
        out.weightingstring = f"Details of Montag#{out.montagid}\n\n"
        for i, data in enumerate(self.unitlist):
            unitid = data[0]
            secondary = data[1]
            # Adjust for multiple copies of the same thing
            costratio = data[2]
            duplicates = self.numberofcopies.get(i, 1)
            costratio = max(1, costratio / duplicates)

            montagweight = math.floor((weightmultiplier*self.maxcostratio)/costratio)
            # the mod command only accept 1-100
            montagweight = max(1, min(100, montagweight))
            # If the secondary effect has a unitmod, use that
            # else use the legendary special unitmod "do nothing"!
            # (SOME kind of unit mod is needed to insert the montag commands)
            if len(secondary.unitmod) > 0:
                unitmod = utils.unitmods[secondary.unitmod]
            else:
                unitmod = utils.unitmods["Do Nothing"]
            modcmds = unitmod.applytounitid(None, unitid, additionals_firstshape={"#montagweight":montagweight,
                                                                        "#montag":out.montagid})
            modcmds = f"-- Montag: costratio was {costratio}, max for this montag was {self.maxcostratio}\n" + modcmds
            out.modcmds += modcmds + "\n"

            percentage = "{:.1f}%".format(montagweight/weighttotal * 100)

            if secondary is None or len(unitmod.nameprefix) < 1:
                out.weightingstring += f"Weighting {montagweight} ({percentage}): {unitmod.lastunitname} ({secondary.name})\n"
            else:
                out.weightingstring += f"Weighting {montagweight} ({percentage}): {unitmod.lastunitname}\n"
        out.weightingstring += f"Total creatures: {out.numcreatures}; Sum of weights: {weighttotal}\n\n"
        out.weightingstring = out.weightingstring.replace("Do Nothing", "No Modifier")
        if self.makedummymonster:
            out.modcmds += f"#newmonster {utils.MONSTER_ID}\n"
            # 284: wolf - it's one of the youngest creatures the game
            out.modcmds += "#copystats 284\n"
            out.modcmds += "#copyspr 284\n"
            out.modcmds += f"#firstshape -{out.montagid}\n"
            out.modcmds += f'#name "Dummy Montag {out.montagid}"' + "\n"
            out.modcmds += f'#descr "This unit has no purpose except to spawn in a unit of montag {out.montagid}."' + "\n"
            out.modcmds += "#end\n\n"
            out.dummymonsterid = utils.MONSTER_ID
            utils.MONSTER_ID += 1
        return out

