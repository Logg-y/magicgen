import argparse
import copy
import csv
import random
import sys

import fileparser
import nationals
from spellstructures import utils

# List of spells to not push to uncastable: these are only divine spells
spellstokeep = [150, 167, 166, 165, 168, 169, 189, 190, 151, 170]

START_ID = 1300
ver = "1.0.0"

ALL_PATH_FLAGS = [utils.PathFlags(2 ** x) for x in range(0, 8)]


def rollspells(**options):
    with open("log.txt", "w") as logfile:
        sys.stdout = logfile
        # sys.stderr = logfile
        with open("spells.csv", "r") as f:
            r = csv.DictReader(f, delimiter="\t")
            for line in r:
                utils.spellnames.append(line["name"])

        modname = options.get("modname", None)
        if modname is None:
            modname = random.random()

        with open(f"magicgen-{modname}.dm", "w") as f:
            l = []
            sys.stderr.write("Parsing data files...\n")
            fileparser.readModifiersFromDir(r".\data\spells\modifiers")
            fileparser.readSecondariesFromDir(r".\data\spells\secondaries")
            fileparser.readSecondariesFromDir(r".\data\spells\secondaries\summons")
            fileparser.readUnitModsFromDir(r".\data\spells\secondaries\summons\unitmods")
            fileparser.readWeaponModsFromDir(r".\data\spells\secondaries\summons\unitmods\weaponmods")
            # dict merging
            # (or I could upgrade to py3.9 to use |=)
            s = fileparser.readEffectsFromDir(r".\data\spells\secondaries\nextspells")
            s = {**s, **fileparser.readEffectsFromDir(r".\data\spells\summons")}
            s = {**s, **fileparser.readEffectsFromDir(r".\data\spells\summons\commanders")}
            s = {**s, **fileparser.readEffectsFromDir(r".\data\spells\rituals")}

            s = {**s, **fileparser.readEffectsFromDir(r".\data\spells")}

            # Keep track of which effects have been done at which research levels
            # this is because we don't want to duplicate any with national spells
            generatedeffectsatlevels = {}

            for k in s:
                sp = s[k]
                if sp.nextspell != "":
                    sp.nextspell = s[sp.nextspell]

            for school in [1, 2, 4, 8, 16, 32, 64]:
                schoolname = utils.SchoolFlags(school).name
                spellsperlevel = options.get("spellsperlevel", 14)
                if school == 8:
                    spellsperlevel = int(spellsperlevel * options.get("constructionfactor", 0.33))
                for research in range(0, 10):
                    if school == 8 and research in [2, 4, 6, 8]:
                        # construction crafting levels don't get spells
                        continue
                    sys.stderr.write(
                        f"Generating {spellsperlevel} spells at research {research} for school {schoolname}...\n")
                    effectpool = copy.copy(s)
                    for x in range(0, spellsperlevel):
                        while 1:
                            spell = None
                            if len(effectpool) == 0:
                                print(
                                    f"WARNING: no valid spells at research {research} for school {schoolname}, generated {x}/{spellsperlevel} successfully")
                                sys.stderr.write(
                                    f"No more valid spells at research {research} for school {schoolname}, generated {x}/{spellsperlevel} successfully\n")
                                break
                            sp = effectpool[random.choice(list(effectpool.keys()))]
                            # These are the things used to denote things that should be nextspell ONLY
                            if sp.paths > 0 and sp.schools > 0:
                                # Special rules for blood
                                if school == 64:
                                    if sp.paths & 128:
                                        spell = sp.rollSpell(research, forcepath=128, allowblood=True, **options)

                                elif sp.schools & school:
                                    spell = sp.rollSpell(research, forceschool=school, allowblood=False, **options)

                            del effectpool[sp.name]

                            if spell is not None:
                                l.append(spell)
                                if research not in generatedeffectsatlevels:
                                    generatedeffectsatlevels[research] = []
                                generatedeffectsatlevels[research].append(sp.name)
                                print(
                                    f"Successfully generated spell {spell.name} from effect {sp.name} at research level {research}")
                                break
                        if len(effectpool) == 0:
                            break

            # Always generated effects
            for name, spelleff in s.items():
                if spelleff.alwaysgenerate > 0 and not spelleff.generated:
                    print(f"Trying to generate a spell of effect {spelleff.name} as it hasn't generated yet")
                    spell = spelleff.rollSpell(random.randint(spelleff.power, spelleff.maxpower), allowskipchance=False,
                                               **options)
                    if spell is not None:
                        l.append(spell)
                elif spelleff.alwaysgenerate > 0:
                    print(f"Spell effect {spelleff.name} has already generated so doesn't need to be forced")

            # Make holy spells
            holy = fileparser.readEffectsFromDir(r".\data\spells\holy")
            for name, spelleff in holy.items():
                for path in [1, 2, 4, 8, 16, 32, 64, 128]:
                    l.append(spelleff.rollSpell(spelleff.power, forcesecondaryeff=path, blockmodifier=True,
                                                allowskipchance=False, **options))

            sys.stderr.write("Generating national spells...\n")

            # Generate some national spells
            nationals.readVanilla()
            nationals.readMods(options.get("modlist", ""))
            nationcount = len(list(nationals.nationals.keys()))
            for index, nation in enumerate(list(nationals.nationals.keys())):
                if (index + 1) % 20 == 0:
                    sys.stderr.write(f"Progress: Beginning nation {index + 1} of {nationcount}...\n")
                successfuleffectnames = []
                print(f"Generating spells for nation {nation}")
                for x in range(0, options.get("nationalspells", 12)):
                    chosencomm = random.choice(nationals.nationals[nation])
                    # researchlevel = random.randint(1, 9)
                    effectpool = copy.copy(s)
                    researchlevelstotry = list(range(1, 10))
                    random.shuffle(researchlevelstotry)
                    researchlevel = researchlevelstotry.pop(0)
                    while 1:
                        succeeded = False
                        choseneffect = effectpool[random.choice(list(effectpool.keys()))]

                        # avoid duplicates, either in this national set or with stuff in the generic set
                        if (choseneffect.name not in successfuleffectnames) and (
                                choseneffect.name not in generatedeffectsatlevels[researchlevel]):
                            allowedpaths = [utils.PathFlags(2 ** x) for x in utils.breakdownflag(choseneffect.paths)]
                            if len(allowedpaths) > 0:
                                primarypath = None
                                if chosencomm.guaranteedpaths == 0 or random.random() < 0.33:
                                    primarypath = utils._selectFlag(copy.copy(allowedpaths), chosencomm.allpaths)
                                if primarypath is None:
                                    print(f"guaranteedpaths {chosencomm.guaranteedpaths}")
                                    primarypath = utils._selectFlag(copy.copy(allowedpaths), chosencomm.guaranteedpaths)

                                if primarypath is not None:
                                    allowblood = (primarypath == 128 or chosencomm.allpaths & 128)
                                    print(
                                        f"Try generating national spell for {nation} with effect {choseneffect.name}, primarypath={primarypath}, secondaries={chosencomm.allpaths}, there are {len(effectpool)} effects")
                                    for attempt in range(0, 2):
                                        if attempt == 0:
                                            spell = choseneffect.rollSpell(researchlevel, forcepath=primarypath,
                                                                           forcesecondaryeff=chosencomm.allpaths,
                                                                           allowblood=allowblood, allowskipchance=False,
                                                                           setparams={"restricted": nation}, **options)
                                        else:
                                            spell = choseneffect.rollSpell(researchlevel, forcepath=primarypath,
                                                                           blocksecondary=True, allowblood=allowblood,
                                                                           allowskipchance=False,
                                                                           setparams={"restricted": nation}, **options)
                                        if spell is not None:
                                            l.append(spell)
                                            succeeded = True
                                            successfuleffectnames.append(copy.copy(choseneffect.name))
                                            # print(f"Successful names now {successfuleffectnames}")
                                            break

                        if succeeded:
                            break

                        del effectpool[choseneffect.name]

                        if len(effectpool) == 0:
                            if len(researchlevelstotry) == 0:
                                raise ValueError(
                                    f"Couldn't make a national spell for nation {nation}, guaranteed={chosencomm.guaranteedpaths}, randoms={chosencomm.allpaths}")
                            researchlevel = researchlevelstotry.pop(0)
                            effectpool = copy.copy(s)

            sys.stderr.write(f"Writing output magicgen-{modname}.dm...\n")
            f.write('#modname "MagicGen{}"{}'.format(modname, "\n"))
            # f.write("#clearallspells\n\n\n")
            for x in range(1, 1 + START_ID):
                if x not in spellstokeep:
                    f.write(f"#selectspell {x}\n")
                    f.write(f"#school -1\n")
                    f.write(f"#researchlevel -1\n")
                    f.write(f"#end\n")

            print(f"There are {len(l)} spells to write!")
            for spell in l:
                if spell is not None:
                    # print(spell.name)
                    f.write(spell.output())
            f.flush()
            f.close()
            sys.stderr.write(f"Finished writing magicgen-{modname}.dm!\n")
    sys.stdout = sys.stderr


# Stuff to make this usable on a non-CL basis
class Option(object):
    def __init__(self, optname, help="", type=None, default=None):
        self.optname = optname
        self.type = type
        self.help = help
        self.default = default

    def toArgparse(self, parser):
        parser.add_argument(self.optname, help=self.help, type=self.type, default=self.default)

    def askInConsole(self):
        print("\n\n-----------------------")
        s = self.help
        if self.type is bool:
            s += " [y/n]"
        print(s)
        if self.type is bool:
            if self.default:
                print("Default: y")
            else:
                print("Default: n")
        elif self.type in [float, int]:
            print(f"Default: {self.default}")
        else:
            if self.default is None:
                print("Default: <NONE>")
            else:
                print(f"Default: {self.default}")
        print("")
        r = input()
        if r.strip() == "":
            return self.default
        if self.type is float:
            try:
                return float(r)
            except:
                print("Could not convert input to a number. Try again!\n")
                return self.askInConsole()
        if self.type is int:
            try:
                return int(r)
            except:
                print("Could not convert input to a number. Try again!\n")
                return self.askInConsole()
        if self.type is bool:
            if r.lower() == "y":
                return True
            elif r.lower() == "n":
                return False
            print("Please enter y or n.")
            return self.askInConsole()

        else:
            return r


def main():
    opts = []
    opts.append(
        Option("-spellsperlevel", help="Number of spells to try making at each research level", type=int, default=14))
    opts.append(Option("-constructionfactor",
                       help="Construction will get only this proportion of the normal number of spells. This is intended to be less than 1.0.",
                       type=float, default=0.33))
    opts.append(Option("-modlist",
                       help="A list of .dm file paths, separated by commas. Files in the list will be scanned and nations defined in them will get national spells.",
                       type=str, default=""))
    opts.append(Option("-nationalspells",
                       help="Number of national spells to try to make per nation. These spells will be directed towards the paths the nation has access to.",
                       type=int, default=12))
    opts.append(
        Option("-modname", help="Name of the mod. If left blank a rather unhelpful number will be generated at random.",
               default=None))

    if len(sys.argv) > 1:
        parser = argparse.ArgumentParser(prog=f"MagicGen v{ver}",
                                         description="Procedural generator for Dom5 spellbooks!",
                                         formatter_class=argparse.ArgumentDefaultsHelpFormatter)
        for opt in opts:
            opt.toArgparse(parser)

        parser.add_argument("-run",
                            help="Pass this if you want to run commmand line mode and not be forced into guided interactive!",
                            default=None)
        args = parser.parse_args()
        rollspells(**vars(args))
    else:
        print(f"MagicGen v{ver}: Procedural generator for Dom5 spellbooks!")
        print("This program can also be run from command line, pass -h for info.")
        print("Pressing ENTER without writing anything will accept the option's default value.")
        args = {}
        for opt in opts:
            # opt.optname has a leading hyphen
            args[opt.optname[1:]] = opt.askInConsole()

        print("Beginning generation...")
        try:
            rollspells(**args)
        except:
            sys.stderr.write(fileparser.traceback.format_exc())
            sys.stderr.write("\nErrors during generation. Press ENTER to exit.")
            input()
            return
        print("Complete. Press ENTER to exit.")
        input()


if __name__ == "__main__":
    main()

# These are old functions I used to do some mass edits on my summon data files...

# def editfolder(folder):
#	for f in os.listdir(folder):
#		if not os.path.isdir(os.path.join(folder, f)):
#			with open(os.path.join(folder, f)) as realf:
#				lines = []
#				for line in realf:
#					lines.append(line)
#				insertions = {}
#				foundchance = False
#				for i, line in enumerate(lines):
#					m = re.match("#skipchance (.*)", line)
#					if m is not None:
#						realchance = 100-int(m.groups()[0])
#						realchance = int(realchance/2)
#						newskipchance = 100-realchance
#						lines[i] = f"#skipchance {newskipchance}\n"
#						print(f"{f}: edit skipchance {m.groups()[0]} to {newskipchance}")
#						foundchance = True
#					if line.startswith("#end") and not foundchance:
#						realchance = 100-0
#						realchance = int(realchance/2)
#						newskipchance = 100-realchance
#						insertions[i] = f"#skipchance {newskipchance}\n"
#						print(f"{f}: insert skipchance {newskipchance} at {i}")
#					elif line.startswith("#end"):
#						foundchance = False
#
#
#				for k, v in insertions.items():
#					lines.insert(k, v)
#
#			with open(os.path.join(folder, f), "w") as realf:
#				for line in lines:
#					realf.write(line)
#
# def editfolder2(folder):
#	for f in os.listdir(folder):
#		if not os.path.isdir(os.path.join(folder, f)):
#			with open(os.path.join(folder, f)) as realf:
#				lines = []
#				for line in realf:
#					lines.append(line)
#				insertions = {}
#				foundchance = False
#				for i, line in enumerate(lines):
#					m = re.match("#skipchance (.*)", line)
#					if m is not None:
#						newskipchance = int(int(m.groups()[0])/3)
#						lines[i] = f"#skipchance {newskipchance}\n"
#						print(f"{f}: edit skipchance {m.groups()[0]} to {newskipchance}")
#						foundchance = True
#					if line.startswith("#end") and not foundchance:
#						pass
#					elif line.startswith("#end"):
#						foundchance = False
#
#
#				for k, v in insertions.items():
#					lines.insert(k, v)
#
#			with open(os.path.join(folder, f), "w") as realf:
#				for line in lines:
#					realf.write(line)
