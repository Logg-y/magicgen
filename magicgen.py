import argparse
import copy
import csv
import random
import sys
import os

import fileparser
import nationals
from spellstructures import utils

# List of spells to not push to uncastable: these are only divine spells
spellstokeep = [150, 167, 166, 165, 168, 169, 189, 190]

START_ID = 1300
ver = "1.0.0"

ALL_PATH_FLAGS = [utils.PathFlags(2 ** x) for x in range(0, 8)]

def _writetoconsole(line):
    """Because PyInstaller and PySimpleGUI don't play nice unless specifying STDIN as well, I had to make
    this be converted to exe with --window to avoid the console coming up.
    For some reason after doing that, sys.stderr has to be flushed after every line to allow the GUI process
    to pick it up"""
    sys.stderr.write(line)
    sys.stderr.flush()


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

        outputfolder = options.get("outputfolder", "./output")

        outfp = os.path.join(outputfolder, f"magicgen-{modname}.dm")

        with open(outfp, "w") as f:
            l = []
            _writetoconsole("Parsing data files...\n")
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

            researchmod = options.get("researchmodifier", 0)

            for school in [1, 2, 4, 8, 16, 32, 64]:
                schoolname = utils.SchoolFlags(school).name
                spellsperlevel = options.get("spellsperlevel", 14)
                if school == 8:
                    spellsperlevel = int(spellsperlevel * options.get("constructionfactor", 0.33))
                for research in range(0+researchmod, 10+researchmod):
                    if school == 8 and research in [2, 4, 6, 8]:
                        # construction crafting levels don't get spells
                        continue
                    _writetoconsole(
                        f"Generating {spellsperlevel} spells at research {research} for school {schoolname}...\n")
                    sys.stderr.flush()
                    effectpool = copy.copy(s)
                    for x in range(0, spellsperlevel):
                        while 1:
                            spell = None
                            if len(effectpool) == 0:
                                print(
                                    f"WARNING: no valid spells at research {research} for school {schoolname}, generated {x}/{spellsperlevel} successfully")
                                _writetoconsole(
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
            _writetoconsole("holyspell")
            holy = fileparser.readEffectsFromDir(r".\data\spells\holy")
            for spelltype in ["banishment", "smite"]:
                for path in [1, 2, 4, 8, 16, 32, 64, 128, 256]:
                    effectpool = copy.copy(holy)
                    effectlist = list(effectpool.keys())
                    random.shuffle(effectlist)
                    # Make a list of effects, go through them in sequence
                    # skipchance not passing just means throwing it to the end
                    while 1:
                        effectname = effectlist.pop(0)
                        _writetoconsole("holyspell try\n")
                        spelleff = holy[effectname]
                        if spelleff.secondarypaths & path and (getattr(spelleff, spelltype) > 0):
                            _writetoconsole("effect valid\n")
                            if random.random() * 100 < spelleff.skipchance:
                                # failed skipchance, go to the end
                                effectlist.append(effectname)
                            else:

                                # force secondary effect on themed spells that don't have a next spell
                                # these specmasks are extra effect and extra effect on damage
                                _writetoconsole(f"len is {len(spelleff.nextspell)} ")
                                _writetoconsole(f"effname is {effectname}, path is {path}\n")
                                if len(spelleff.nextspell) == 0 and (
                                        (spelleff.spec & 576460752303423488) or (spelleff.spec & 1152921504606846976)):
                                    l.append(spelleff.rollSpell(spelleff.power, forcesecondaryeff=path,
                                                                blockmodifier=True,
                                                                allowskipchance=False, **options))
                                    _writetoconsole(f"holyspell made something with a nextspell {l[-1].name} with {effectname}\n")
                                else:  # block secondaries on things that DO have a nextspell built in
                                    l.append(
                                        spelleff.rollSpell(spelleff.power, blocksecondary=True,
                                                           blockmodifier=True,
                                                           allowskipchance=False, **options))
                                    _writetoconsole(f"holyspell made something without nextspell {l[-1].name} with {effectname}\n")
                                break


            _writetoconsole("Generating national spells...\n")

            # Generate some national spells
            nationals.readVanilla()
            nationals.readMods(options.get("modlist", ""))
            nationcount = len(list(nationals.nationals.keys()))
            for index, nation in enumerate(list(nationals.nationals.keys())):
                if (index + 1) % 20 == 0:
                    _writetoconsole(f"Progress: Beginning nation {index + 1} of {nationcount}...\n")
                successfuleffectnames = []
                print(f"Generating spells for nation {nation}")
                for x in range(0, options.get("nationalspells", 12)):
                    chosencomm = random.choice(nationals.nationals[nation])
                    # researchlevel = random.randint(1, 9)
                    effectpool = copy.copy(s)
                    researchlevelstotry = list(range(1+researchmod, 10+researchmod))
                    random.shuffle(researchlevelstotry)
                    researchlevel = researchlevelstotry.pop(0)
                    while 1:
                        succeeded = False
                        choseneffect = effectpool[random.choice(list(effectpool.keys()))]

                        # avoid duplicates, either in this national set or with stuff in the generic set
                        if (choseneffect.name not in successfuleffectnames) and (
                                researchlevel in generatedeffectsatlevels) and (
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

            _writetoconsole(f"Writing output {outfp}...\n")
            f.write('#modname "MagicGen-{}"{}'.format(modname, "\n"))
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
            _writetoconsole(f"Finished writing magicgen-{modname}.dm!\n")
    sys.stdout = sys.stderr


# Stuff to make this usable on a non-CL basis
class Option(object):
    def __init__(self, optname, help="", type=None, default=None):
        self.optname = optname
        self.type = type
        self.help = help
        self.default = default

    def toArgparse(self, parser):
        if self.type is not None:
            parser.add_argument(self.optname, help=self.help, type=self.type, default=self.default)
        else:
            parser.add_argument(self.optname, help=self.help, default=self.default)

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
        Option("-spellsperlevel", help="Number of spells to try generating at each research level", type=int,
               default=14))
    opts.append(Option("-constructionfactor",
                       help="Construction will get only this proportion of the normal number of spells. This is intended to be less than 1.0.",
                       type=float, default=0.33))
    opts.append(Option("-modlist",
                       help="A list of .dm file paths, separated by commas. Files in the list will be scanned and nations defined in them will get national spells.",
                       type=str, default=""))
    opts.append(Option("-nationalspells",
                       help="Number of national spells to try to make per nation. These spells will be directed towards the paths the nation has access to.",
                       type=int, default=12))
    opts.append(Option("-secondarychance",
                       help="Percentage chance of spells generating with a secondary effect. Does not apply to summoning spells.",
                       type=int, default=20))
    opts.append(Option("-summonsecondarychance",
                       help="Percentage chance of summoning spells generating with a secondary effect. Does not apply to other spells.",
                       type=int, default=20))

    opts.append(Option("-researchmodifier",
                       help="Research modifier: Subtracts this value from the research level of spells generated. Large values will make strong spells available at lower research than normal.",
                       type=int, default=0))

    opts.append(Option("-pathlevelmodflat",
                       help="Path level modifier: Adds this value to the path level requirement of all spells generated (to a minimum of 1). Negative values will make spells easier to cast.",
                       type=int, default=0))

    opts.append(Option("-pathlevelmodmult",
                       help="Path level modifier: Multiplies the level requirement of all spells generated by this value. Values less than 1 will make spells easier to cast.",
                       type=float, default=1.0))

    opts.append(Option("-fatiguemodflat",
                       help="Fatigue modifier: Adds this value to the fatigue cost of all spells generated (to a minimum of 0). Negative values will make spells easier to cast.",
                       type=int, default=0))

    opts.append(Option("-fatiguemodmult",
                       help="Path level modifier: Multiplies the fatigue cost of all spells generated by this value. Values less than 1 will make spells easier to cast.",
                       type=float, default=1.0))

    opts.append(Option("-outputfolder",
                       help="Folder to put the created .dm in",
                       type=str, default="./output"))

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
                            help="Pass this if you want to run command line mode and not be forced into guided interactive!",
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
            _writetoconsole(fileparser.traceback.format_exc())
            return
        print("Complete. Press ENTER to exit.")
        input()


if __name__ == "__main__":
    print(sys.argv)
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
