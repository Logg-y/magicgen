from spellstructures import utils


class debugkeys:
    NATIONALSPELLGENERATIONWEIGHTING = True
    NATIONALSPELLGENERATION = True
    MAGESELECTIONFORPATHFORNATIONALSPELL = True
    
    # Writes details on the outcome of every single condition test
    CONDITIONTESTING = False


def debuglog(line, *debugareas):
    if not line.endswith("\n"):
        line += "\n"
    dolog = False
    for i in debugareas:
        dolog |= i
    if dolog:
        print(line)
