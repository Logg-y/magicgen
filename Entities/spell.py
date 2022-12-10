import copy
import math

# This seems to be how dominions autocalcs cast time
# keys are simply gems required
# 9 is a guess as I couldn't be bothered to mod a spell in for what seemed like an obvious progression
casttimes = {0: 100, 1: 125, 2: 175, 3: 200, 4: 225, 5: 250, 6: 275, 7: 300, 8: 325, 9: 350}


class Spell(object):
    def __init__(self):
        self.name = ""
        self.effect = -1
        self.damage = -1
        self.spec = 0
        self.school = -1
        self.aoe = 0
        self.range = 0
        self.nreff = 1
        self.precision = 0
        self.path1 = -1
        self.path2 = -1
        self.path1level = -1
        self.path2level = -1
        self.fatiguecost = 0
        self.researchlevel = -1
        self.nextspell = ""
        self.prevspell = None
        self.details = None
        self.name = "Unnamed"
        self.descr = ""
        self.flightspr = None
        self.explspr = None
        self.sound = None
        self.maxbounces = 0
        self.nolandtrace = 0
        self.onlyfriendlydst = 0
        self.onlygeosrc = 0
        self.copyspell = None
        self.casttime = None
        self.provrange = None
        self.onlygeodst = None
        self.nogeodst = None
        self.godpathspell = None
        self.comments = []
        self.modcmdsbefore = ""
        self.restricted = None
        self.aicastmod = 0
        self.isnextspell = False
        self.parenteffect = None
        # This is used only for storing the unit object for eventsets
        # as they use compounded unitmods, this is where the intermediate goes
        self.globaleventunit = None
        self.hiddenench = None
        self.friendlyench = None

        self.hasgenerated = False

    def p(self):
        print(f"name {self.name}")
        print(f"effect {self.effect}")
        print(f"damage {self.damage}")
        print(f"spec {self.spec}")
        print(f"school {self.school}")
        print(f"aoe {self.aoe}")
        print(f"nreff {self.nreff}")
        print(f"path1level {self.path1level}")
        print(f"path1 {self.path1}")
        print(f"fatiguecost {self.fatiguecost}")
        print("\n" * 3)

    def multiplyAISpellMod(self, mult):
        "Multiply the AI casting priority by the given multiplier, taking into account existing modifiers."
        print(f"multiply AI spell mod: mult is {mult}; old mod was {self.aispellmod}")
        currentAIModMultiplicative = (self.aispellmod + 100) / 100
        newAIMod = 100 * ((currentAIModMultiplicative * mult) - 1)
        self.aispellmod = int(max(-100, min(1000, newAIMod)))
        print(f"New spell mod is {self.aispellmod}")

    def output(self):
        if self.hasgenerated:
            return ""
        # self.p()
        debugmode = False
        if debugmode:
            self.name = self.name + " {}".format(self.researchlevel)
            self.researchlevel = min(0, self.researchlevel)
        out = ""

        for comment in self.comments:
            out += f"-- {comment}\n"

        out += self.modcmdsbefore

        # this spec is "next effect on damage" which ALWAYS calls the next spell id and not the thing you ask for
        #if self.nextspell != "" and self.nextspell is not None and not (self.spec & 1152921504606846976):
        #    out += self.nextspell.output()

        # Nextspells and file/id arrangement.
        # Each spell currently tries put its nextspells before it
        # Meaning doing this top-down from parent to child yields:
        # on damage effect nextspell, X+3
        # on damage effect, X+2
        # main spell nextspell, X+1
        # Main spell, X

        # Which is probably fine and perfectly okay?
        if self.nextspell != "" and self.nextspell is not None:
            # Because nextspells are technically made before the main spell is finalised, their IDs
            # will decrease down the chain instead of increase
            # Just switching IDs at each level should fix that...
            nextspell = self
            depth = 0
            minid = None
            maxid = None
            while nextspell is not None and nextspell != "":
                print(f"Nextspell stack: depth={depth} {nextspell.name} -> {nextspell.id}")
                depth += 1
                if minid is None or minid > nextspell.id:
                    minid = copy.copy(nextspell.id)
                if maxid is None or maxid < nextspell.id:
                    maxid = copy.copy(nextspell.id)
                nextspell = nextspell.nextspell

            print(f"minid = {minid}, maxid = {maxid}")

            nextspell = self
            depth = 0
            while nextspell is not None and nextspell != "":
                print(f"Nextspell stack: depth={depth} {nextspell.name} -> {nextspell.id}")
                depth += 1
                if nextspell.id > maxid:
                    print(f"ERROR: Nextspell {nextspell.name} at depth {depth} in chain had too high id {nextspell.id} > expected max {maxid}")
                    return ""
                nextspell.id = minid
                print(f"Assigned {nextspell.name} at depth {depth} id {minid}")
                minid += 1
                nextspell = nextspell.nextspell

            out += self.nextspell.output()
        print(f"Writing: {self.name} -> {self.id}")
        out += f"#selectspell {self.id}\n"
        if self.copyspell is not None:
            out += '#copyspell "{}"{}'.format(self.copyspell, "\n")
        if self.restricted is not None:
            out += f"#restricted {self.restricted}\n"
        out += "#name \"" + self.name + "\"\n"
        out += f"#effect {self.effect}\n"
        out += f"#damage {self.damage}\n"
        out += f"#spec {self.spec}\n"
        if self.school > -1:
            out += f"#school {int(math.log(self.school, 2))}\n"
        else:
            out += "#school -1\n"
        out += f"#aoe {self.aoe}\n"
        out += f"#range {self.range}\n"
        out += f"#nreff {self.nreff}\n"
        out += f"#precision {self.precision}\n"
        out += '#descr "{}"{}'.format(self.descr.strip(), "\n")
        if self.path1 > 0:
            out += '#path 0 {}{}'.format(int(math.log(self.path1, 2)), "\n")
        else:
            out += '#path 0 {}{}'.format(int(self.path1), "\n")
        out += f"#researchlevel {self.researchlevel}\n"
        out += f"#pathlevel 0 {self.path1level}\n"
        if self.path2 != -1 and self.path2level > -1:
            out += f"#path 1 {int(math.log(self.path2, 2))}\n"
            out += f"#pathlevel 1 {self.path2level}\n"
        else:
            out += "#path 1 -1\n"
            out += "#pathlevel 1 0\n"
        out += f"#fatiguecost {self.fatiguecost}\n"
        if self.details is not None and len(self.details) > 0:
            out += '#details "{}"{}'.format(self.details.strip(), "\n")
        if self.nextspell != "" and self.nextspell is not None and not (self.spec & 1152921504606846976):
            out += '#nextspell "{}"{}'.format(self.nextspell.name, "\n")
        if self.flightspr is not None:
            out += f"#flightspr {self.flightspr}\n"
        if self.explspr is not None:
            out += f"#explspr {self.explspr}\n"
        if self.maxbounces > 0:
            out += f"#maxbounces {self.maxbounces}\n"
        if self.sound is not None:
            out += f"#sound {self.sound}\n"
        if self.casttime is not None:
            out += f"#casttime {self.casttime}\n"
        if self.provrange is not None:
            out += f"#provrange {self.provrange}\n"
        if self.onlygeodst is not None:
            out += f"#onlygeodst {self.onlygeodst}\n"
        if self.nogeodst is not None:
            out += f"#nogeodst {self.nogeodst}\n"
        if self.ainocast > 0:
            out += f"#ainocast {self.ainocast}\n"
        if self.nolandtrace > 0:
            out += f"#nolandtrace {self.nolandtrace}\n"
        if self.onlyfriendlydst > 0:
            out += f"#onlyfriendlydst {self.onlyfriendlydst}\n"
        if self.onlygeosrc > 0:
            out += f"#onlygeosrc {self.onlygeosrc}\n"
        if self.godpathspell is not None:
            out += f"#godpathspell {self.godpathspell}\n"
        if self.aispellmod != 0:
            out += f"#aispellmod {self.aispellmod}\n"
        if self.hiddenench is not None:
            out += f"#hiddenench {self.hiddenench}\n"
        if self.friendlyench is not None:
            out += f"#friendlyench {self.friendlyench}\n"
        out += "#end\n\n"

        #if self.nextspell != "" and self.nextspell is not None and (self.spec & 1152921504606846976):
        #    out += self.nextspell.output()
        self.hasgenerated = True
        return out


