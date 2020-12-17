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
                return False

        if self.op == ">":
            return paramval > val
        elif self.op == "==":
            return paramval == val
        elif self.op == "<":
            return paramval < val
        elif self.op == ">=":
            return paramval >= val
        elif self.op == "<=":
            return paramval <= val
        elif self.op == "!=":
            return paramval != val
        elif self.op == "&":
            return bool(paramval & val)
        elif self.op == "!&":
            return not bool(paramval & val)
        else:
            raise Exception(f"Unknown operator: {self.op}")
