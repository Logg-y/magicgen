from fileparser import unitinbasedatafinder
from Entities import weapon
import re

class NewWeapon(object):
    def __init__(self):
        self.name = ""
        self.setcmds = []
        self.rawcmds = []

        self.baseweapon = None
        self.init = False
        pass

    def toWeapon(self) -> weapon.Weapon:
        if self.baseweapon is not None:
            retval = weapon.get(self.baseweapon)
        else:
            retval = weapon.Weapon(None)

        for attrib, value in self.setcmds:
            setattr(retval, attrib, value)

        retval.additionalmodcmds += f"\n-- Generated from NewWeapon {self.name}\n"
        retval.additionalmodcmds += "\n".join(self.rawcmds)
        retval.additionalmodcmds += "\n"
        retval.uniqueid = f"newweapon-{self.name}"
        retval.newweapon = self
        retval.isnewweapon = True

        return retval