from spellstructures import utils


class debugkeys:
    NATIONALSPELLGENERATIONWEIGHTING = True
    NATIONALSPELLGENERATION = True
    MAGESELECTIONFORPATHFORNATIONALSPELL = True


def debuglog(line, *debugareas):
    if not line.endswith("\n"):
        line += "\n"
    dolog = False
    for i in debugareas:
        dolog |= i
    if dolog:
        utils._writetoconsole(line)
