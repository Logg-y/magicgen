from nationalmage import NationalMage
from typing import (
    Dict,
    List,
    Union,
)
import random

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
        weights: Dict[int, int] = {}
        for i in range(0, 8):
            weights[2 ** i] = 0

        for mage in self.mages:
            for i in range(0, 8):
                weights[2 ** i] += mage.getlevelinpath(2 ** i)
            for random in mage.randoms:
                randomweight = float(random.chance * random.link)
                randompaths = random.getpossiblepaths()
                randomweight = randomweight / len(randompaths)
                for i in randompaths:
                    weights[i] += randomweight

        # _writetoconsole(f"Mages:{self.mages}\nWeights:{weights}")

        # touch up output for compatability
        output: Dict[int, int] = {}
        hasweight = False
        for i in weights:
            output[i] = int(round(weights[i]))
            if output[i] != 0:
                hasweight = True
        if not hasweight:  # If all weights are 0 set all to 1
            for i in output:
                output[i] = 1
        return output

    def getcommanderwithpath(self, path: int) -> Union[NationalMage, None]:
        random.shuffle(self.mages)
        for mage in self.mages:
            if (mage.hasaccesstopath(path)):
                return mage
        return None

    def totext(self):
        acc = f"mages for {self.id}:["
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
