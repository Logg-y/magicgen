from spellstructures import utils


class debugkeys:
    NATIONALSPELLGENERATIONWEIGHTING = False
    NATIONALSPELLGENERATION = True
    MAGESELECTIONFORPATHFORNATIONALSPELL = False


def debuglog(line, *debugareas):
    if not line.endswith("\n"):
        line += "\n"
    dolog = False
    for i in debugareas:
        dolog |= i
    if dolog:
        print(line)
