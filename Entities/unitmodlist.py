
class UnitModList(object):
    def __init__(self):
        self.name = None
        self.allowedunitmods = []
    def __iter__(self):
        return iter(self.allowedunitmods)
