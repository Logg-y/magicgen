from typing import List

from Entities.nationalmage import NationalMage


class Site(object):
    def __init__(self, id):
        self.id = 0
        self.mages: List[NationalMage] = []
        self.id = id
        self.name = ""
