from typing import List

from Enums.PathFlags import PathFlags
from Services import utils


class MagePathRandom(object):
    def __init__(self, chance, link, paths):
        self.chance: int = chance  # chance for generating
        self.link: int = link  # amount of levels it gives
        self.paths: int = paths  # path mask

    def get_possible_paths(self) -> List[int]:
        acc = []
        for i in range(0, 8):
            if self.paths & (2 **i):
                acc.append(2 ** i)
        return acc

    def get_number_of_possible_paths(self) -> int:
        acc: int = 0
        for i in range(0, 8):
            if self.paths & (2 ** i):
                acc += 1
        return acc

    def can_random_into_path(self, path: PathFlags) -> bool:
        return path in self.get_possible_paths()

    def to_text(self) -> str:
        acc = ""
        if self.link == 1:
            acc += f"{self.chance}%"
        else:
            acc += f"{self.link}x"
        acc += f"{utils.pathstotext(self.paths)}"
        return acc

    def __repr__(self):
        return f"MagePathRandom(Paths={self.paths}, link={self.link}, chance={self.chance})"
