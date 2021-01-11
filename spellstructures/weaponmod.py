from copy import copy

from . import utils
from .utils import breakdownflag

# Weaponmods are called only from UnitMods which in turn come from SecondaryEffects
# which means they can be a LOT simpler, in fact the only thing that really needs checking
# is that the unit has some weapon which can accept the weapon mod
# Everything else should be handled by the SecondaryEffect which applies it


flags_to_mod_cmds = {"def_": "def"}


class WeaponMod(object):
    def __init__(self):
        self.spelltype = 0
        self.name = ""
        self.params = ["att", "def_", "len", "nratt", "ammo", "secondaryeffectid", "secondaryeffectalwaysid", "effect",
                       "damage", "spec", "range", "aoe"]
        self.att = 0
        self.def_ = 0
        self.len = 0
        self.nratt = 0
        self.ammo = 0
        self.secondaryeffectid = 0
        self.secondaryeffectalwaysid = 0
        self.effect = 0
        self.damage = 0
        self.spec = 0
        self.range = 0
        self.aoe = 0
        self.nameprefix = ""
        self.setweaponmagic = 0

        self.reqs = []
        self.setcommands = []
        self.multcommands = []
        self.extracommands = []

    def compatibilityunit(self, unit):
        "Return True if this weapon mod is compatible with the given Unit."
        # We want to return true if this can apply to any weapon on the unit
        for wp in unit.weapons:
            if self.compatibility(wp):
                return True
        return False

    def compatibility(self, wpn):
        for r in self.reqs:
            if not r.test(wpn):
                # print(f"{wpn.name} missing req {r.param}")
                return False

        return True

    def apply(self, unit):
        "Apply the weaponmod to a unit's weapons. Returns: ({oldweaponid:newweaponid} of replaced weapons, string of mod commands for the new weapons)"
        out = ""
        replacements = {}
        for wpn in unit.weapons:
            # No need to make multiple replacements if a unit has multiple of the same eligible weapon
            if self.compatibility(wpn) and wpn.origid not in replacements:
                out += f"-- Modified weapon {wpn.origid} with weaponmod {self.name}\n"
                out += f"#newweapon {utils.WEAPON_ID}\n"
                if utils.WEAPON_ID >= 2000:
                    raise ValueError("Modded weapon ID is too high - consider reducing the number of modified"
                                     " creatures generated!")
                replacements[wpn.origid] = copy(utils.WEAPON_ID)
                utils.WEAPON_ID += 1
                out += f"#copyweapon {wpn.origid}\n"
                spec = copy(wpn.spec)

                for param in self.params:
                    paramv = getattr(self, param)
                    if paramv != 0:
                        newparamval = getattr(wpn, param) + paramv
                        modcmd = flags_to_mod_cmds.get(param, param)
                        out += f"#{modcmd} {newparamval}\n"
                    if param == "spec":
                        spec += paramv

                for param, val in self.setcommands:
                    modcmd = flags_to_mod_cmds.get(param, param)
                    out += f"#{modcmd} {val}\n"

                    if param == "spec":
                        spec = paramv

                for param in self.extracommands:
                    out += f"#{param}\n"

                for param, val in self.multcommands:
                    paramv = getattr(self, param)
                    newparamval = getattr(wpn, param) * paramv
                    modcmd = flags_to_mod_cmds.get(param, param)
                    out += f"#{modcmd} {newparamval}\n"

                if self.setweaponmagic:
                    if spec & 2097152:
                        spec -= 2097152

                breakdown = breakdownflag(spec)

                print(breakdown)

                # This flag is hard to hit ethereal
                # so add magic in its absence
                if 21 not in breakdown:
                    out += "#magic\n"

                # this flag is adds strength of wielder
                if 0 not in breakdown:
                    out += "#nostr\n"

                for n in breakdown:
                    if n == 1:
                        out += "#twohanded\n"
                    elif n == 2:
                        out += "#flail\n"
                    elif n == 3:
                        out += "#demonundead\n"
                    elif n == 4:
                        out += "#magiconly\n"
                    elif n == 5:
                        out += "#fire\n"
                    elif n == 6:
                        out += "#armorpiercing\n"
                    elif n == 7:
                        out += "#armornegating\n"
                    elif n == 9:
                        out += "#cold\n"
                    elif n == 11:
                        out += "#shock\n"
                    elif n == 12:
                        out += "#mrnegates\n"
                    elif n == 13:
                        out += "#poison\n"
                    elif n == 14:
                        out += "#ignoreshield\n"
                    elif n == 15:
                        out += "#sacredonly\n"
                    elif n == 16:
                        out += "#aironly\n"
                    elif n == 17:
                        out += "#mind\n"
                    elif n == 18:
                        out += "#friendlyimmune\n"
                    elif n == 19:
                        out += "#undeadimmune\n"
                    elif n == 20:
                        out += "#defnegate\n"
                    elif n == 21:
                        pass  # not #magic
                    elif n == 22:
                        out += "#enemyimmune\n"
                    elif n == 23:
                        out += "#uwok\n"
                    elif n == 24:
                        out += "#mrnegateseasily\n"
                    elif n == 25:
                        out += "#uwonly\n"
                    elif n == 26:
                        out += "#ironweapon\n"
                    elif n == 27:
                        out += "#bonus\n"
                    elif n == 28:
                        out += "#demonimmune\n"
                    elif n == 29:
                        out += "#inanimateimmune\n"
                    # elif n == 30: out += "#bloodletting\n"
                    elif n == 31:
                        out += "#charge\n"
                    elif n == 33:
                        out += "#usedinemelee\n"
                    # higher charge bonus cap
                    # elif n == 36: out += "#usedinemelee\n"
                    elif n == 37:
                        out += "#norepel\n"
                    elif n == 38:
                        out += "#pierce\n"
                    elif n == 39:
                        out += "#blunt\n"
                    elif n == 40:
                        out += "#slash\n"
                    elif n == 41:
                        out += "#acid\n"
                    elif n == 42:
                        out += "#sizeresist\n"
                    elif n == 43:
                        out += "#melee50\n"
                    elif n == 44:
                        out += "#hardmrneg\n"
                    elif n == 45:
                        out += "#unrepel\n"
                    elif n == 46:
                        out += "#flyingimmune\n"
                    elif n == 47:
                        out += "#constructimmune\n"
                    elif n == 48:
                        out += "#animalonly\n"
                    elif n == 49:
                        out += "#hithead\n"
                    elif n == 58:
                        out += "#halfstr\n"

                newname = self.nameprefix + " " + wpn.name
                newname = newname.strip()
                out += '#name "' + newname + '"' + "\n"

                out += "#end\n\n"

        return replacements, out
