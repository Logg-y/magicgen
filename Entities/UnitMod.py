from copy import copy

from Services import naming, utils
from fileparser import unitinbasedatafinder

# Weaponmods are called only from SecondaryEffects
# which means they can be a LOT simpler
# Most stuff should be handled in the SecondaryEffect

flags_to_mod_cmds = {"def_":"def", "explodeondeath":"deathfire", "acidsplash":"acidshield", "vineshield":"entangle", "deathwail":"deathparalyze", "undeadleader":"undcommand", "poisonbarbs":"poisonarmor", "invisibility":"invisible", "poweroftheturningyear":"yearturn", "graphicsize":"drawsize"}
argless_cmds = ["eyeloss", "horrormark", "aquatic", "amphibian", "pooramphibian", "flying", "illusion", "heal", "ethereal", "immortal", "domimmortal", "springimmortal", "entangle", "spiritsight", "deathcurse", "noundeadleader", "invisible", "invisibility"]


class UnitMod(object):
    def __init__(self):
        self.name = ""
        self.params = ["wpn1", "wpn2", "wpn3", "wpn4", "wpn5", "wpn6", "wpn7", "armor1", "armor2", "armor3", "armor4", "rt", "reclimit", "basecost", "rcost", "size", "ressize", "hp", "prot", "mr", "mor", "str", "att", "def", "prec", "enc", "mapmove", "ap", "ambidextrous", "mounted", "reinvigoration", "leader", "undeadleader", "magicleader", "startage", "maxage", "hand", "head", "body", "foot", "misc", "crownonly", "pathcost", "startdom", "bonusspells", "F", "A", "W", "E", "S", "D", "N", "B", "H", "rand1", "nbr1", "link1", "mask1", "rand2", "nbr2", "link2", "mask2", "rand3", "nbr3", "link3", "mask3", "rand4", "nbr4", "link4", "mask4", "holy", "inquisitor", "mind", "inanimate", "undead", "demon", "magicbeing", "stonebeing", "animal", "coldblood", "female", "forestsurvival", "mountainsurvival", "wastesurvival", "swampsurvival", "cavesurvival", "aquatic", "amphibian", "pooramphibian", "float", "flying", "stormimmune", "teleport", "immobile", "noriverpass", "sailingshipsize", "sailingmaxunitsize", "stealthy", "illusion", "spy", "assassin", "patience", "seduce", "succubus", "corrupt", "heal", "immortal", "domimmortal", "reinc", "noheal", "neednoteat", "homesick", "undisciplined", "formationfighter", "slave", "standard", "inspirational", "taskmaster", "beastmaster", "bodyguard", "waterbreathing", "iceprot", "invulnerable", "slashres", "bluntres", "pierceres", "shockres", "fireres", "coldres", "poisonres", "voidsanity", "darkvision", "blind", "animalawe", "awe", "haltheretic", "fear", "berserk", "cold", "heat", "fireshield", "banefireshield", "damagerev", "poisoncloud", "diseasecloud", "slimer", "mindslime", "reform", "regeneration", "reanimator", "poisonarmor", "petrify", "eyeloss", "ethereal", "ethtrue", "deathcurse", "trample", "trampswallow", "stormpower", "firepower", "coldpower", "darkpower", "chaospower", "magicpower", "winterpower", "springpower", "summerpower", "fallpower", "forgebonus", "fixforgebonus", "mastersmith", "resources", "autohealer", "autodishealer", "alch", "nobadevents", "event", "insane", "shatteredsoul", "leper", "taxcollector", "gem", "gemprod", "chaosrec", "pillagebonus", "patrolbonus", "castledef", "siegebonus", "incprovdef", "supplybonus", "incunrest", "popkill", "researchbonus", "drainimmune", "inspiringres", "douse", "adeptsacr", "crossbreeder", "makepearls", "pathboost", "allrange", "voidsum", "heretic", "elegist", "shapechange", "firstshape", "secondshape", "secondtmpshape", "landshape", "watershape", "forestshape", "plainshape", "xpshape", "unique", "fixedname", "special", "nametype", "summon", "n_summon", "autosum", "n_autosum", "batstartsum1", "batstartsum2", "domsummon", "domsummon20", "raredomsummon", "bloodvengeance", "bringeroffortune", "realm1", "realm2", "realm3", "batstartsum3", "batstartsum4", "batstartsum5", "batstartsum1d6", "batstartsum2d6", "batstartsum3d6", "batstartsum4d6", "batstartsum5d6", "batstartsum6d6", "turmoilsummon", "coldsummon", "scalewalls", "deathfire", "uwregen", "shrinkhp", "growhp", "transformation", "startingaff", "fixedresearch", "divineins", "lamialord", "preanimator", "dreanimator", "mummify", "onebattlespell", "fireattuned", "airattuned", "waterattuned", "earthattuned", "astralattuned", "deathattuned", "natureattuned", "bloodattuned", "magicboostF", "magicboostA", "magicboostW", "magicboostE", "magicboostS", "magicboostD", "magicboostN", "magicboostALL", "eyes", "heatrec", "coldrec", "spreadchaos", "spreaddeath", "corpseeater", "poisonskin", "bug", "uwbug", "spreadorder", "spreadgrowth", "startitem", "spreaddom", "battlesum5", "acidshield", "drake", "prophetshape", "horror", "enchrebate50p", "latehero", "sailsize", "uwdamage", "landdamage", "rpcost", "buffer", "rand5", "nbr5", "link5", "mask5", "rand6", "nbr6", "link6", "mask6", "mummification", "diseaseres", "raiseonkill", "raiseshape", "sendlesserhorrormult", "xploss", "theftofthesunawe", "incorporate", "hpoverslow", "blessbers", "dragonlord", "curseattacker", "uwheat", "slothresearch", "horrordeserter", "mindvessel", "elementrange", "sorceryrange", "older", "disbelieve", "firerange", "astralrange", "landreinvigoration", "naturerange", "beartattoo", "horsetattoo", "reincarnation", "wolftattoo", "boartattoo", "sleepaura", "snaketattoo", "appetite", "astralfetters", "foreignmagicboost", "templetrainer", "infernoret", "kokytosret", "addrandomage", "unsurr", "combatcaster", "homeshape", "speciallook", "aisinglerec", "nowish", "bugreform", "mason", "onisummon", "sunawe", "spiritsight", "defenceorganiser", "invisible", "startaff", "ivylord", "spellsinger", "magicstudy", "triplegod", "triplegodmag", "unify", "triple3mon", "yearturn", "fortkill", "thronekill", "digest", "indepmove", "unteleportable", "reanimpriest", "stunimmunity", "entangle", "alchemy", "woundfend", "singlebattle", "falsearmy", "summon5", "ainorec", "researchwithoutmagic", "slaver", "autocompete", "deathparalyze", "adventurers", "cleanshape", "reqlab", "reqtemple", "horrormarked", "changetargetgenderforseductionandseductionimmune", "corpseconstruct", "guardianspiritmodifier", "isashah", "iceforging", "isayazad", "isadaeva", "blessfly", "plant", "clockworklord", "commaster", "comslave", "minsizeleader", "snowmove", "swimming", "stupid", "skirmisher", "ironvul", "heathensummon", "unseen", "illusionary", "reformtime", "immortalrespawn", "nomovepen", "wolf", "dungeon", "graphicsize", "twiceborn", "aboleth", "tmpastralgems", "localsun", "tmpfiregems", "defiler", "mountedbeserk", "lanceok", "startheroab", "minprison", "uwfireshield", "saltvul", "landenc", "plaguedoctor", "curseluckshield", "pathboostuw", "pathboostland", "noarmormapmovepenalty", "farthronekill", "hpoverflow", "indepstay", "polyimmune", "horrormark", "deathdisease", "allret", "percentpathreduction", "aciddigest", "beckon", "slaverbonus", "carcasscollector", "mindcollar", "labpromotion", "mountainrec", "indepspells", "enchrebate50", "summon1", "randomspell", "deathpower", "deathrec", "norange", "insanify", "reanimator", "defector", "nohof", "batstartsum1d3", "enchrebate10", "end"]
        self.descr = ""
        self.nameprefix = ""
        self.weaponmod = ""
        self.landok = 0
        self.uwok = 0
        self.reqmage = 0

        self.reqs = []
        self.setcommands = []
        self.multcommands = []

        # The event unitmod code relies on having some way to pull the parent unit id back
        # which this sorts out
        self.lastparentid = None
        self.lastunitname = None

    def compatibility(self, unitobj, tested=None):
        # print(f"{self.name} testing against {unit.id} {unit.name}")
        if tested is None:
            tested = []
        if unitobj.id in tested:
            return True

        for r in self.reqs:
            if not r.test(unitobj):
                return False

        # These need only be true for the first shape in the collection
        # ... except I'm getting bugs from this
        if self.landok:
            if unitobj.aquatic != -1:
                return False

        if self.uwok:
            if unitobj.aquatic != -1 and unitobj.amphibian != -1 and unitobj.pooramphibian != -1:
                return False

        if self.reqmage and len(tested) == 0:
            haspaths = False
            for path in ["F", "A", "W", "E", "S", "D", "N", "B"]:
                if hasattr(unitobj, path) and getattr(unitobj, path, 0) > 0:
                    haspaths = True
                    break
            if not haspaths:
                return False

        # I cannot support shrink or growhp
        if unitobj.shrinkhp != -1:
            return False
        if unitobj.growhp != -1:
            return False

        if self.weaponmod != "":
            wpnmod = utils.weaponmods[self.weaponmod]
            if not wpnmod.compatibilityunit(unitobj):
                return False
        tested.append(unitobj.id)

        # Must recursively check for eligibility on all subshapes too
        for x in ["shapechange", "firstshape", "secondshape", "secondtmpshape", "forestshape", "plainshape",
                  "foreignshape", "homeshape", "domshape", "notdomshape", "springshape", "summershape", "autumnshape",
                  "wintershape", "landshape", "watershape"]:
            if hasattr(unitobj, x):
                uid = getattr(unitobj, x)
                if uid not in tested and uid > 0:
                    unittottest = unitinbasedatafinder.get(uid)
                    if not self.compatibility(unittottest, tested=tested):
                        return False


        return True

    def apply(self, spelleffect, spell):
        "Apply this unit mod to the given spell of type spelleffect."
        # Globals with events apply this through the eventset instead
        if spelleffect.eventset is None:
            unitnr = spell.damage
            return self.applytounitid(spell, unitnr)
        return ""

    def applytounitid(self, spell, unitnr, extrashapechain=None, additionals_firstshape=None):
        """Apply this effect to the given unitnr, returning mod code for the new unit.

        spell can be None. If given, spell.damage is set to the correct unit ID for the new unit.
        extrashapechain should not be set manually as it is used to track wounded shapes and make them all
        join together neatly

        additionals_firstshape should be a dict of {modcommand:value} that is appended to the first shape ONLY.
        So far this is used for things like adding units to montags and giving them a montagweight.
        The modcommand given should INCLUDE A HASH.
        """
        # Turns out that value given as default arguments are not created fresh every call
        # which is an interesting bit of python trivia I didn't know before I wrote this
        # needless to say, this persisting between calls created all kinds of weird abominations
        # of creatures that would turn into each other
        if extrashapechain is None:
            extrashapechain = {}

        u = unitinbasedatafinder.get(unitnr)
        return self.applytounit(spell, u, extrashapechain, additionals_firstshape=additionals_firstshape)

    def applytounit(self, spell, u, extrashapechain=None, additionals_firstshape=None):

        u.descr += " " + self.descr
        u.descr = u.descr.replace("CREATURE", u.name)
        u.descr = naming.parsestring(u.descr)
        u.name = self.nameprefix + " " + u.name
        u.name = u.name.strip()
        self.lastunitname = u.name

        out = ""

        # Weapon mod
        if self.weaponmod != "":
            wpnmod = utils.weaponmods[self.weaponmod]
            wpnreplacements, wpnoutput = wpnmod.apply(u)
            for wpn in u.weapons:
                if wpn.origid in wpnreplacements:
                    wpn.origid = wpnreplacements[wpn.origid]
            out += wpnoutput

        if utils.MONSTER_ID >= 9000:
            raise ValueError("New Monster ID is too high for Dominions! Consider lowering montag sizes.")

        out += f"-- Modified unit {u.origid} with unitmod {self.name}\n"
        out += f"#newmonster {utils.MONSTER_ID}\n"
        # Update the spell to summon the new creature
        # needless to say, don't do this if the current monster is a secondshape something caused by running in recursive mode1
        # or the spell will be left summoning the last thing in the secondshape chain
        if len(extrashapechain) == 0:
            if spell is not None:
                print("is first pass, fixed spell.damage")
                spell.damage = utils.MONSTER_ID
            else:
                self.lastparentid = utils.MONSTER_ID
        utils.MONSTER_ID += 1
        out += f"#copystats {u.origid}\n"
        out += f"#copyspr {u.origid}\n"
        out += "#descr {}{}{}\n".format('"', u.descr, '"')
        out += "#name {}{}{}\n".format('"', u.name, '"')

        # Disable transformation
        if hasattr(u, "transformation"):
            if u.transformation != 0:
                out += "#transformation 0\n"

        for param in self.params:
            if hasattr(self, param):
                paramv = getattr(self, param)
                if paramv != 0:
                    if not hasattr(u, param):
                        print(
                            f"Unit {u.name} didn't have param {param} when affected by unitmod {self.name}, assumed 0")
                        setattr(u, param, 0)
                    newparamval = getattr(u, param) + paramv
                    modcmd = flags_to_mod_cmds.get(param, param)
                    if modcmd not in argless_cmds:
                        out += f"#{modcmd} {newparamval}\n"
                    else:
                        out += f"#{modcmd}\n"

        for param, val in self.setcommands:
            modcmd = flags_to_mod_cmds.get(param, param)
            if modcmd not in argless_cmds:
                if isinstance(val, str):
                    out += "#{} {}{}{}\n".format(modcmd, '"', val, '"')
                else:
                    out += f"#{modcmd} {val}\n"
            else:
                out += f"#{modcmd}\n"

        for param, val in self.multcommands:
            paramv = getattr(u, param)
            newparamval = int(val * paramv)
            modcmd = flags_to_mod_cmds.get(param, param)
            out += f"#{modcmd} {newparamval}\n"

        # Overwritten weapons will not be any of those commands
        if self.weaponmod != "":
            out += f"#clearweapons\n"
            for wpn in u.weapons:
                out += f"#weapon {wpn.origid}\n"

        secondshapeextra = ""
        # Second shape needs to propagate
        for x in ["shapechange", "firstshape", "secondshape", "secondtmpshape", "forestshape", "plainshape",
                  "foreignshape", "homeshape", "domshape", "notdomshape", "springshape", "summershape", "autumnshape",
                  "wintershape", "landshape", "watershape"]:
            if hasattr(u, x):
                uid = getattr(u, x)
                if uid not in extrashapechain and uid > 0:
                    extrashapechain[uid] = copy(utils.MONSTER_ID)
                    print(f"UID {uid} is a {x} of {u.name}, applying to that too...")
                    secondshapeextra += self.applytounitid(spell, uid, extrashapechain)
                if uid in extrashapechain and uid > 0:
                    # update this creature's secondshape or whatever with the new creature
                    out += f"#{x} {extrashapechain[uid]}\n"

        if additionals_firstshape is not None:
            for modcmd, val in additionals_firstshape.items():
                out += f"{modcmd} {val}\n"

        # Special case: Do nothing should firstshape to the original unit
        # This makes montags built with Do Nothing-modified units quickly transform to their normal version
        # which means double click correctly selects all of them amongst other things
        if self.name == "Do Nothing":
            out += f"#firstshape {u.id}\n"

        out += "#end\n\n"

        out += secondshapeextra

        return out
