from Enums.DebugKeys import debugkeys
from Services.DebugLogger import debuglog


class NameCond(object):
    def __init__(self):
        self.param = None
        self.op = None
        self.val = None
        self.path = None
        self.text = None
        self.val2 = None
        self.op2 = None

    def test(self, spell):
        self.op = self.op.strip()
        if not hasattr(spell, self.param.strip()):
            paramval = -1
        else:
            paramval = getattr(spell, self.param.strip())	
        self.val = self.val.strip()
        val = int(self.val)
        if self.val2 is not None:
            val2 = int(self.val2)
            good = False
            self.op2 = self.op2.strip()
            # val2 op2 paramval op1 val1
            # 1 < paramval < 3
            descrstring = f"test: {val2} ({self.val2}) {self.op2} {paramval} ({self.param}) {self.op} {val} ({self.val})"

            if self.op2 == ">":
                good = val2 > paramval
            elif self.op2 == "<":
                good = val2 < paramval
            elif self.op2 == ">=":
                good = val2 >= paramval
            elif self.op2 == "<=":
                good = val2 <= paramval
            else:
                raise Exception(f"Unknown operator: {self.op2}")
            if not good:
                debuglog(descrstring + " -> false", debugkeys.CONDITIONTESTING)
                return False

        descrstring = f"condition test: {paramval} ({self.param}) {self.op} {val}"

        returnval = None

        if self.op == ">":
            returnval = paramval > val
        elif self.op == "==":
            returnval = paramval == val
        elif self.op == "<":
            returnval = paramval < val
        elif self.op == ">=":
            returnval = paramval >= val
        elif self.op == "<=":
            returnval = paramval <= val
        elif self.op == "!=":
            returnval = paramval != val
        elif self.op == "&":
            returnval = bool(paramval & val)
        elif self.op == "!&":
            returnval = not bool(paramval & val)

        if returnval is None:
            raise Exception(f"Unknown operator: {self.op}")

        debuglog(f"{descrstring} -> {returnval}", debugkeys.CONDITIONTESTING)
        return returnval
    def __repr__(self):
        if self.val2 is None:
            return(f"NameCond({self.param} {self.op} {self.val})")
        else:
            return(f"NameCond({self.val2} {self.op2} {self.param} {self.op} {self.val})")
