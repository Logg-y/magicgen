from . import utils
import math

class MontagResult(object):
    "Container to hold MontagBuilder results"
    def __init__(self):
        self.modcmds = ""
        self.weightingstring = ""
        self.numcreatures = 0
        self.montagid = None
        self.dummymonsterid = None

class MontagBuilder(object):
    def __init__(self):
        self.unitlist = []
        self.maxcostratio = -1.0
        self.makedummymonster = False
    def add(self, unitid, secondaryeffect, costratio):
        """Add a unit to the montag with the given secondary effect. Cost ratio should be a pessimistic estimate of:

        gems / number of effects
        (IE: the cost in gems per one creature)
        """
        self.unitlist.append((unitid, secondaryeffect, costratio))
        self.maxcostratio = max(self.maxcostratio, costratio)
    def process(self):
        out = MontagResult()
        out.numcreatures = len(self.unitlist)
        out.montagid = utils.MONTAG_ID
        weighttotal = 0
        maxweight = 0
        # quickly get the weight total, it is useful later
        for unitid, secondary, costratio in self.unitlist:
            montagweight = math.floor(self.maxcostratio / costratio)
            # the mod command only accept 1-100
            montagweight = max(1, min(100, montagweight))
            maxweight = max(maxweight, montagweight)
            weighttotal += montagweight
        weightmultiplier = math.floor(100 / maxweight)
        weighttotal *= weightmultiplier

        if utils.MONTAG_ID > 100000:
            # This is probably never ever going to happen but hey
            raise ValueError("Ran out of montag IDs, the game would reject this mod. Consider revising ID settings"
                             " or reducing the number of montags that are being created")
        utils.MONTAG_ID += 1
        out.weightingstring = f"Details of Montag#{out.montagid}\n\n"
        for unitid, secondary, costratio in self.unitlist:
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

