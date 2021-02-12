from nationalmage import NationalMage
from typing import (
    Dict,
    List,
    Union,
)
import random

from site import Site


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

        # _writetoconsole(f"Mages:{self.mages}\nWeights:{weights}")

        # TODO include randoms
        return weights

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

    # def printmages(self):
    # _writetoconsole(self.totext() + "\n")
