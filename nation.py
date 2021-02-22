import debugkeys
from nationalmage import NationalMage
from typing import (
    Dict,
    List,
    Union,
)
import random
from spellstructures import utils,  Spell

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
        self.nationalspells: List[Spell] = []

    def add_mage(self, mage: NationalMage):
        if mage not in self.mages:
            self.mages.append(mage)

    def get_pathweights(self) -> Dict[int, int]:
        mageweights: Dict[NationalMage, float] = self._get_natspell_weight_distribution_for_mages()
        weights: Dict[int, float] = self._calculate_raw_pathweights(mageweights)
        weights: Dict[int, int] = {i: int(round(weights[i]))for i in weights}

        debugkeys.debuglog(f"Pathweights for nation {self.name} (ID{self.id})\n"
                           f"Mages:{[i.to_text() for i in self.mages]}\n"
                           f"MageWeights: {mageweights}\n"
                           f"Weights:{[str(utils.pathstotext(i)) + ' '  + str(weights[i]) + ', '  for i in weights]}"
                           , debugkeys.debugkeys.NATIONALSPELLGENERATIONWEIGHTING)
        return weights

    def _calculate_raw_pathweights(self, mageweights) -> Dict[int, float]:
        weights: Dict[int, float] = {2 ** i: 0 for i in range(0, 8)}
        for mage in self.mages:
            for i in range(0, 8):
                weights[2 ** i] += mage.get_weight_fraction_for_path(2 ** i) * mageweights[mage] * 100
        return weights

    def _get_natspell_weight_distribution_for_mages(self) -> Dict[NationalMage, float]:
        acc: Dict[NationalMage, float] = {}
        for mage in self.mages:
            if mage not in acc:
                acc[mage] = 0.0
            acc[mage] = mage.get_total_paths_amount() * 2 - 1
        return acc

    def get_commander_with_path(self, path: int) -> Union[NationalMage, None]:
        random.shuffle(self.mages)
        for mage in self.mages:
            debugkeys.debuglog(f"Testing {mage.to_text()} for {utils.pathstotext(path)}: {mage.has_access_to_path(path)}", debugkeys.debugkeys.MAGESELECTIONFORPATHFORNATIONALSPELL)
            if mage.has_access_to_path(path):
                return mage
        raise ValueError(f"Could not find mage for path {utils.pathstotext(path)} in {self.to_text()}")

    def to_text(self):
        acc = f"mages for {self.name} (ID:{self.id}):["
        k = 0
        for i in self.mages:
            if k != 0:
                acc += ", "
            k += 1
            acc += "(" + i.to_text() + ")"
        acc += "]"
        return acc

    def has_mages(self) -> bool:
        return len(self.mages) > 0

    def __str__(self):
        return f"Nation({self.name}, id {self.id})"

    def register_national_spell(self, spell: Spell):
        if spell is not None:
            self.nationalspells.append(spell)