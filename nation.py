import debugkeys
from nationalmage import NationalMage
from typing import (
    Dict,
    List,
    Union,
)
import random
from spellstructures import utils

from nationalsite import Site


class Nation(object):
    "Container for modded nation info, used for the UI only"

    def __init__(self, id):
        self.era = None
        self.name: str = ""
        self.epithet: str = ""
        self.id: int = id
        self.sites: List[Site] = []
        self.mages: List[NationalMage] = []

    def addmage(self, mage: NationalMage):
        if (mage not in self.mages):
            self.mages.append(mage)

    def getpathweights(self) -> Dict[int, int]:
        mageweights: Dict[NationalMage, float] = self.getmagetotalweightdistribution()
        weights: Dict[int, float] = {}
        for i in range(0, 8):
            weights[2 ** i] = 0.0

        for mage in self.mages:
            for i in range(0, 8):
                weights[2 ** i] += mage.getweightfractionforpath(2 ** i) * mageweights[mage]

        debugkeys.debuglog(f"Mages:{[i.totext() for i in self.mages]}\n"
                           f"Weights:{[str(utils.pathstotext(i)) + ' '  + str(weights[i]) + ', '  for i in weights]}"
                           , debugkeys.debugkeys.NATIONALSPELLGENERATIONWEIGHTING)
        return self._sanitizeweights(weights)

    def sanitizeweights(self, unsanitizedweights: Dict[int, int] ):
        # touch up output for compatability
        output: Dict[int, int] = {}
        hasweight = False
        for i in unsanitizedweights:
            output[i] = int(round(unsanitizedweights[i]))
            if output[i] != 0:
                hasweight = True
        if not hasweight:  # If all weights are 0 set all to 1
            for i in output:
                output[i] = 1
        return output

    def getmagetotalweightdistribution(self) -> Dict[NationalMage, float]:
        acc: Dict[NationalMage, float] = {}
        for i in self.mages:
            acc[i] = 0.0
        for mage in acc:
            acc[mage] = mage.gettotalpathsamount() * 2 - 1
        return acc

    def getcommanderwithpath(self, path: int) -> Union[NationalMage, None]:
        random.shuffle(self.mages)
        for mage in self.mages:
            debugkeys.debuglog(f"Testing {mage.totext()} for {utils.pathstotext(path)}: {mage.hasaccesstopath(path)}", debugkeys.debugkeys.MAGESELECTIONFORPATHFORNATIONALSPELL)
            if mage.hasaccesstopath(path):
                return mage
        raise ValueError(f"Could not find mage for path {utils.pathstotext(path)} in {self.totext()}")

    def totext(self):
        acc = f"mages for {self.name} (ID:{self.id}):["
        k = 0
        for i in self.mages:
            if k != 0:
                acc += ", "
            k += 1
            acc += i.totext()
        acc += "]"
        return acc

    def hasmages(self) -> bool:
        return len(self.mages) > 0

    def __repr__(self):
        return(f"Nation({self.name}, id {self.id})")
