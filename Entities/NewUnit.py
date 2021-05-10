from fileparser import unitinbasedatafinder
import re

class NewUnit(object):
    def __init__(self):
        self.name = ""
        self.setcmds = []
        self.rawcmds = []

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
        else:
            retval = unitinbasedatafinder.UnitInBaseDataFinder()

        for attrib, value in self.setcmds:
            setattr(retval, attrib, value)

        retval.additionalmodcmds += f"\n-- Generated from NewUnit {self.name}\n"
        retval.additionalmodcmds += "\n".join(self.rawcmds)
        retval.additionalmodcmds += "\n"
        retval.uniqueid = f"newunit-{self.name}"

        return retval