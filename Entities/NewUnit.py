from fileparser import unitinbasedatafinder
from Entities import weapon
from Services import utils
import re

class NewUnit(object):
    def __init__(self):
        self.name = ""
        self.setcmds = []
        self.rawcmds = []
        self.clearweapons = 0
        self.addweapons = []
        self.addnewweapons = []
        self.spr1 = None
        self.spr2 = None

        self.baseunit = None
        self.init = False
        pass

    def _init(self):
        if not self.init:
            # Look for a base unit to load stats from
            self.baseunit = None
            for cmd in self.rawcmds:
                if cmd.startswith("#copystats"):
                    if self.baseunit is not None:
                        raise ValueError(f"Multiple copystats in new unit {self.name}")
                    m = re.match(r"#copystats (\d*)", cmd)
                    if m is None:
                        raise ValueError(f"Bad #copystats {cmd} in new unit {self.name}")
                    self.baseunit = int(m.groups()[0])
            self.init = True

    def toUnitBaseData(self) -> unitinbasedatafinder.UnitInBaseDataFinder:
        #self._init()
        if self.baseunit is not None:
            retval = unitinbasedatafinder.get(self.baseunit)
            if self.clearweapons != 0:
                retval.weapons = []
        else:
            retval = unitinbasedatafinder.UnitInBaseDataFinder()

        for wpnid in self.addweapons:
            retval.weapons.append(weapon.get(wpnid))
        for newwpnname in self.addnewweapons:
            newwpn = utils.newweapons[newwpnname].toWeapon()
            retval.weapons.append(newwpn)


        for attrib, value in self.setcmds:
            setattr(retval, attrib, value)

        retval.additionalmodcmds += f"\n-- Generated from NewUnit {self.name}\n"
        retval.additionalmodcmds += "\n".join(self.rawcmds) + "\n"
        if self.spr1 is not None:
            retval.additionalmodcmds += '#spr1 "{}"'.format(self.spr1) + "\n"
        if self.spr2 is not None:
            retval.additionalmodcmds += '#spr2 "{}"'.format(self.spr2) + "\n"
        retval.additionalmodcmds += "\n"
        retval.uniqueid = f"newunit-{self.name}"
        retval.newunit = self

        return retval