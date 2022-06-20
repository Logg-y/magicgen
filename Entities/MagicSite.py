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

        self.effectnumberforunits = []
        self.usefixedunitid = -1
        self.desiredmontagsize = 0
        self.restrictunitstospellpaths = True
        self.mincreaturepower = -1
        self.maxcreaturepower = -1
        self.secondaryeffectchance = None
        # A list of (mod command, new unit name) pairs to resolve
        self.newuniteffects = []

        self.makedummymonster = 1
        self.makebattledummymonster = 0
        self.dummymonsternames = {}
        self.desiredmontagsize = -1
        self.unitmodlist = None
        self.names = {}

        self.selectunitmods = None

        self.lastsiteid = None
        self.lastsitename = None

        for param in UNITPARAMS:
            setattr(self, param, None)

    def formatdata(self, spelleffect, spell, scaleamt, secondaryeffect, actualpowerlvl):
        siteid = copy.copy(utils.SITE_ID)
        utils.SITE_ID += 1
        output = f"#newsite {siteid}\n"

        if len(self.effectnumberforunits) == 0:
            self.effectnumberforunits.append(10001)

        names = self.names.get(spell.path1, [f"{self.name} {random.randint(-1000, 1000)}"])[:]
        chosenname = random.choice(names)
        formatted = naming.parsestring(chosenname)
        while formatted in utils.magicsitenames:
            formatted += " "
            if len(formatted) > 35:
                print(f"Error: site name ({formatted}) is too long")
                return None
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

        # Resolve newunits
        for pair in self.newuniteffects:
            modcmd = pair[0]
            newunitname = pair[1]
            newunitobj = utils.newunits[newunitname]
            unitmod = utils.unitmods["Do Nothing"]
            modcode = unitmod.applytounit(None, newunitobj.toUnitBaseData())
            output = modcode + output
            output += f"{modcmd} {utils.MONSTER_ID - 1}\n"

        # Unit params
        generatedunitid = None
        outputsuffix = ""
        numtogenerate = max(1, math.floor(self.desiredmontagsize * utils.MONTAG_SCALE))

        for param in UNITPARAMS:
            paramval = getattr(self, param, None)
            if paramval is not None:
                print(f"Generate unit for param {param}...")
                if generatedunitid is not None:
                    output += f"#{param} {generatedunitid}\n"
                else:
                    retval = montagbuilder.generateUnit(self, numtogenerate, spell, secondaryeffect, actualpowerlvl)
                    if retval is None:
                        return None
                    unitcode, montag = retval
                    montagoutput = montag.process()
                    output = unitcode + "\n\n\n" + montagoutput.modcmds + "\n\n\n" + output
                    if self.makedummymonster or self.makebattledummymonster:
                        generatedunitid = montagoutput.dummymonsterid
                    else:
                        generatedunitid = -1*montagoutput.montagid

                    if montagoutput.numcreatures > 18:
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