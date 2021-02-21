from spellstructures import utils


class debugkeys:
    NATIONALSPELLGENERATIONWEIGHTING = True
    NATIONALSPELLGENERATION = False
    MAGESELECTIONFORPATHFORNATIONALSPELL = False


def debuglog(line, *debugareas):
    if not line.endswith("\n"):
        line += "\n"
    dolog = False
    for i in debugareas:
        dolog |= i
    if dolog:
        print(line)
