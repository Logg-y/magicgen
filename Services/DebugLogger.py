from Services import utils

def debuglog(line, *debugareas):
    if not line.endswith("\n"):
        line += "\n"
    dolog = False
    for i in debugareas:
        dolog |= i
    if dolog:
        print(line.strip())
