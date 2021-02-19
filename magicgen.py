import argparse
import copy
import csv
import os
import pprint
import random
import binascii
import sys
from typing import Dict, List, Union


import fileparser
import nationals
from nation import Nation
from nationalmage import NationalMage
from spellstructures import utils, SpellEffect, Spell

# List of spells to not push to uncastable: these are only divine spells
spellstokeep = [150, 167, 166, 165, 168, 169, 189, 190]

# All spells below this ID get moved to unresearchable
START_ID = 1300
ver = "2.1.4"

ALL_PATH_FLAGS = [utils.PathFlags(2 ** x) for x in range(0, 8)]


def _writetoconsole(line):
    """Because PyInstaller and PySimpleGUI don't play nice unless specifying STDIN as well, I had to make
    this be converted to exe with --window to avoid the console coming up.
    For some reason after doing that, sys.stderr has to be flushed after every line to allow the GUI process
    to pick it up"""
    sys.stderr.write(line)
    sys.stderr.flush()


def rollspells(**options):
    global spellstokeep
    utils.WEAPON_ID = options.get("weaponidstart", 800)
    utils.MONSTER_ID = options.get("unitidstart", 3500)
    utils.SPELL_ID = options.get("spellidstart", 1300)
    utils.EVENT_CODE = options.get("eventcodestart", -300)
    utils.MONTAG_ID = options.get("montagidstart", 1001)
    utils.MONTAG_SCALE = options.get("montagscale", 1.0)

    if options.get("nationlist", "") == "":
        options["nationlist"] = None
    else:
        options["nationlist"] = options["nationlist"].split(",")
        options["nationlist"] = list(map(lambda x: int(x.strip()), options["nationlist"]))

    with open("log.txt", "w") as logfile:
        sys.stdout = logfile
        with open("spells.csv", "r") as f:
            r = csv.DictReader(f, delimiter="\t")
            for line in r:
                utils.spellnames.append(line["name"])

        modname = options.get("modname", None)
        if modname is None:
            modname = random.random()

        if not os.path.isdir("./output"):
            os.mkdir("./output")
        outputfolder = options.get("outputfolder", "./output")

        outfp = os.path.join(outputfolder, f"magicgen-{modname}.dm")

        with open(outfp, "w") as f:
            l: List[Spell] = []
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
            s = {**s, **fileparser.readEffectsFromDir(r".\data\spells\rituals\globals")}
            fileparser.readEventSetsFromDir(r".\data\spells\rituals\globals\events")
            fileparser.readUnitModsFromDir(r".\data\spells\rituals\globals\unitmods")

            s: Dict[str, SpellEffect] = {**s, **fileparser.readEffectsFromDir(r".\data\spells")}

            # Keep track of which effects have been done at which research levels
            # this is because we don't want to duplicate any with national spells
            generatedeffectsatlevels: Dict[int, List[str]] = {}

            researchmod = options.get("researchmodifier", 0)

            for school in [1, 2, 4, 8, 16, 32, 64]:
                schoolname = utils.SchoolFlags(school).name
                spellsperlevel = options.get("spellsperlevel", 14)
                if school == 8:
                    spellsperlevel = int(spellsperlevel * options.get("constructionfactor", 0.33))
                for research in range(0 + researchmod, 10 + researchmod):
                    if school == 8 and research in [2, 4, 6, 8]:
                        # construction crafting levels don't get spells
                        continue
                    _writetoconsole(
                        f"Generating {spellsperlevel} spells at research {research} for school {schoolname}...\n")
                    sys.stderr.flush()
                    effectpool = copy.copy(s)
                    # First do everything with skipchances, if that fails to make all the spells
                    # do a second run ignoring them
                    allowskipchance = True
                    for x in range(0, spellsperlevel):
                        while 1:
                            spell = None
                            if len(effectpool) == 0:
                                if allowskipchance:
                                    allowskipchance = False
                                    effectpool = copy.copy(s)
                                    continue
                                print(
                                    f"WARNING: no valid spells at research {research} for school {schoolname}, generated {x}/{spellsperlevel} successfully")
                                _writetoconsole(
                                    f"No more valid spells at research {research} for school {schoolname}, generated {x}/{spellsperlevel} successfully\n")
                                break
                            sp = effectpool[random.choice(list(effectpool.keys()))]
                            del effectpool[sp.name]
                            # Prevent duplicartes in the second round of ignoreing skipchances
                            if research in generatedeffectsatlevels and sp.name in generatedeffectsatlevels[research]:
                                continue

                            # These are the things used to denote things that should be nextspell ONLY
                            if sp.paths > 0 and sp.schools > 0:
                                # Special rules for blood
                                if school == 64:
                                    if sp.paths & 128:
                                        spell = sp.rollSpell(research, forcepath=128, allowblood=True,
                                                             allowskipchance=allowskipchance, **options)

                                elif sp.schools & school:
                                    spell = sp.rollSpell(research, forceschool=school, allowblood=False,
                                                         allowskipchance=allowskipchance, **options)

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
            _writetoconsole("Generating holyspells \n")
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
                        spelleff = holy[effectname]
                        if spelleff.secondarypaths & path and (getattr(spelleff, spelltype) > 0):
                            if random.random() * 100 < spelleff.skipchance:
                                # failed skipchance, go to the end
                                effectlist.append(effectname)
                            else:

                                # force secondary effect on themed spells that don't have a next spell
                                # these specmasks are extra effect and extra effect on damage
                                if len(spelleff.nextspell) == 0 and (
                                        (spelleff.spec & 576460752303423488) or (spelleff.spec & 1152921504606846976)):
                                    l.append(spelleff.rollSpell(spelleff.power, forcesecondaryeff=path,
                                                                blockmodifier=True,
                                                                allowskipchance=False, **options))
                                else:  # block secondaries on things that DO have a nextspell built in
                                    l.append(
                                        spelleff.rollSpell(spelleff.power, blocksecondary=True,
                                                           blockmodifier=True,
                                                           allowskipchance=False, **options))
                                break

            _writetoconsole("Generating national spells...\n")

            # Generate some national spells
            nationals.readVanilla()
            nationals.readMods(options.get("modlist", ""))
            if "nationlist" not in options:
                options["nationlist"] = list(nationals.nations.keys())
            elif options["nationlist"] is None:
                options["nationlist"] = list(nationals.nations.keys())
            nationstogeneratefor = options["nationlist"]
            generateNationalSpells(
                modlist=options.get("modlist", ""),
                targetnumberofnationalspells=options.get("nationalspells", 12),
                spelleffects=s,
                researchmod=researchmod,
                options=options,
                generatedeffectsatlevels=generatedeffectsatlevels,
                generatedspells=l,
                nationstogeneratefor=nationstogeneratefor,
            )

            _writetoconsole(f"Beginning to write output {outfp}...\n")
            f.write('#modname "MagicGen-{}"{}'.format(modname, "\n"))
            f.write(
                "#description {}A MagicGen pack, generated with version {}. This pack contains {} spells.{}\n".format(
                    '"', ver, len(l), '"')
            )

            nationalspells = []

            with open("Dom5-natspells-list.txt", "r") as natspells:
                foundheader = False
                for line in natspells:
                    if not foundheader:
                        if line.startswith("--"):
                            foundheader = True
                        continue
                    if line.strip() == "":
                        continue
                    nationalspells.append(int(line.strip()))


            if not bool(options.get("clearvanillanationalspells", 1)):
                spellstokeep += nationalspells

            _writetoconsole(f"Hiding vanilla spells...\n")
            for x in range(1, 3501):
                removespell = x not in spellstokeep
                if removespell and bool(options.get("clearvanillagenericspells")) == False:
                    if x not in nationalspells:
                        removespell = False
                if removespell:
                    f.write(f"#selectspell {x}\n")
                    f.write(f"#school -1\n")
                    f.write(f"#researchlevel -1\n")
                    f.write(f"#end\n")


            # add #indepspells to casters
            if bool(options.get("clearvanillagenericspells")):
                # Check crc32 for saved BaseU.csv
                crcokay = False
                with open("indepspells.dm", "r") as indepspells:
                    indepspellscontent = indepspells.read()
                    crc = indepspellscontent.split("\n")[0][2:].strip()
                    with open("BaseU.csv", "rb") as baseu:
                        baseucontent = baseu.read()
                        baseucrc = str(binascii.crc32(baseucontent))
                    if crc == baseucrc:
                        crcokay = True
                        indepspells.seek(0)
                        for line in indepspells:
                            f.write(line)

                if not crcokay:
                    _writetoconsole(f"BaseU CRC {baseucrc} did not match precalced CRC {crc}!"
                                    f" Regenerating indepspells.dm...\n")
                    indepspellscontent = f"--{baseucrc}\n-- This file (indepspells.dm) is transcluded into generated " \
                                         f"mod files when magicgen clears vanilla generic spells.\n" \
                                         f"-- The above is the CRC of the BaseU.csv file used to generate this file " \
                                         f"- this is saved as generating this from scratch takes several minutes\n"
                    for unitid in range(0, 3500):
                        if unitid % 100 == 0:
                            _writetoconsole(f"Beginning indepspells for unit {unitid}...\n")
                        try:
                            unitobj = unit.get(unitid)
                        except Exception:
                            pass
                        # leave illwinter-set values intact
                        if hasattr(unitobj, "indepspells"):
                            if int(getattr(unitobj, "indepspells")) > 0:
                                continue
                        indeplevel = None

                        if hasattr(unitobj, "startdom"):
                            if int(getattr(unitobj, "startdom")) > 0:
                                indeplevel = 7

                        if indeplevel is None:
                            totalmagiclevel = 0
                            for path in ["F", "A", "W", "E", "S", "D", "N", "B"]:
                                if getattr(unitobj, path, "") <= 0:
                                    continue
                                pathval = int(getattr(unitobj, path, 0))
                                if pathval > 0:
                                    totalmagiclevel += pathval

                            for n in range(1, 5):
                                mask = f"mask{n}"

                                if getattr(unitobj, mask, "") == "":
                                    break
                                mask = int(getattr(unitobj, mask, 0))
                                nbr = int(getattr(unitobj, f"nbr{n}"))
                                # This assumes you get ALL of your randoms, no matter how rare
                                totalmagiclevel += nbr

                            if totalmagiclevel >= 3:
                                indeplevel = 5
                            elif totalmagiclevel == 2:
                                indeplevel = 4
                            elif totalmagiclevel == 1:
                                indeplevel = 3

                        if indeplevel is not None:
                            indepspellscontent += f"#selectmonster {unitid}\n"
                            indepspellscontent += f"#indepspells {indeplevel}\n"
                            indepspellscontent += f"#end\n"
                    with open("indepspells.dm", "w") as indepspells:
                        indepspells.write(indepspellscontent)
                        f.write(indepspellscontent)


            print(f"There are {len(l)} spells to write!")
            for spell in l:
                if spell is not None:
                    f.write(spell.output())
            f.flush()
            f.close()
            _writetoconsole(f"Finished writing magicgen-{modname}.dm!\n")
    sys.stdout = sys.stderr


class NationalSpellGenerationInfoCollector:
    effectschecked: int = 0
    effectsdiscarded: int = 0
    spellrollsrepeated: int = 0
    numberofgeneratedspells: int = 0

    @staticmethod
    def print():
        _writetoconsole(f"{NationalSpellGenerationInfoCollector.numberofgeneratedspells} were generated successfully.\n"
                        f"{NationalSpellGenerationInfoCollector.effectschecked} effects were checked. "
                        f"{NationalSpellGenerationInfoCollector.effectsdiscarded} effects were discarded.\n"
                        f"{NationalSpellGenerationInfoCollector.spellrollsrepeated} spellrolls were unsuccessfull\n")


def _rollpathfornationalspell(nation: Nation) -> int:
    pathweights = nation.getpathweights()
    totalweights = 0
    for i, weight in pathweights.items():
        totalweights += weight
    if totalweights == 0:
        _writetoconsole(f"Failed calculating national spell path weights.\n"
                        f"Nation: {nation.totext()}\n"
                        f"Weights: {pprint.pformat(pathweights)}\n"
                        f"Total Weight: {totalweights}")
        raise ValueError
    initialroll = roll = random.randrange(0, totalweights, 1)
    for path, weight in pathweights.items():
        if roll < weight:
            return path
        roll -= weight
    _writetoconsole(f"Attempted and failed to roll for weighted path\n  Rolled {initialroll}\n  Total weight: "
                    f"{totalweights}\n  Weights: {pprint.pformat(pathweights)}\n")
    raise ValueError


def _selectresearchlevel(researchlevelstotry: List[int], generatedeffectsatlevels: Dict[int, List[str]]) -> int:
    while len(researchlevelstotry) > 0:
        researchlevel = researchlevelstotry.pop(0)
        if researchlevel in generatedeffectsatlevels:
            return researchlevel


def generateNationalSpells(modlist: str, targetnumberofnationalspells: int, spelleffects: Dict[str, SpellEffect],
                           researchmod: int,
                           generatedeffectsatlevels: Dict[int, List[str]], generatedspells: List[Spell],
                           nationstogeneratefor: List[int], options: Dict[str, str]):
    _writetoconsole("Generating national spells...\n")

    # Initialize national mage map
    nationcount = len(nationstogeneratefor)
    index = 0  # used for progress report
    numberofgeneratedspells: Dict[int, int] = {}
    # for i in nationals.nations:
    #    nationals.nations[i].printmages()
    for nationid, nation in nationals.nations.items():
        if nationid not in nationstogeneratefor:
            continue
        if index % 20 == 0:
            _writetoconsole(f"Progress: Beginning nation {index} of {nationcount}...\n")
        index += 1
        if not nation.hasmages():
            _writetoconsole(f"Skipping nation {nation.totext()} because no national mages were found")
            continue
        effectpool = copy.copy(spelleffects)
        numberofgeneratedspells[nationid] = 0

        while numberofgeneratedspells[nationid] < targetnumberofnationalspells:
            primarypath = _rollpathfornationalspell(nation)
            # _writetoconsole(f"Attempting to generate for primary path {utils.pathstotext(primarypath)}\n")

            # choose researchlevel
            researchlevelstotry: List[int] = list(range(1 + researchmod, 10 + researchmod))
            random.shuffle(researchlevelstotry)
            researchlevel = _selectresearchlevel(researchlevelstotry, generatedeffectsatlevels)

            # Select a commander to generate this spell for
            commander: NationalMage = nation.getcommanderwithpath(primarypath)

            # calculate if blood shall be allowed as path in the spell
            allowblood = commander.canhaveblood()

            # Select effect for spell
            choseneffect: Union[SpellEffect, None] = None
            # _writetoconsole(f"Selecting national spell effect\n")
            while choseneffect is None:
                NationalSpellGenerationInfoCollector.effectschecked += 1
                choseneffect = effectpool[random.choice(list(effectpool.keys()))]
                # Check that effect is available
                if ((primarypath & choseneffect.paths) == 0) or (  # Wrong path
                        choseneffect.name in generatedeffectsatlevels[
                    researchlevel]):  # effect incompatible for this level
                    # _writetoconsole(f"Discarding current effect: {choseneffect.name}\n")
                    choseneffect = None
                    NationalSpellGenerationInfoCollector.effectsdiscarded += 1
            # _writetoconsole(f"Selected effect: {choseneffect.name}\n")

            # Roll for spell
            # _writetoconsole(
            #    f"Try generating national spell for nation {nation.id} with effect {choseneffect.name}, "
            #    f"primarypath={utils.pathstotext(primarypath)}, secondaries={commander.getpossiblepaths()}, there are "
            #    f"{len(effectpool)} effects available\n")
            spell: Union[Spell, None] = None
            for attempt in range(0, 2):
                if attempt == 0:
                    spell = choseneffect.rollSpell(researchlevel, forcepath=primarypath,
                                                   forcesecondaryeff=commander.getpossiblepathsmask(),
                                                   allowblood=allowblood, allowskipchance=False,
                                                   setparams={"restricted": nation}, **options)
                else:
                    spell = choseneffect.rollSpell(researchlevel, forcepath=primarypath,
                                                   blocksecondary=True, allowblood=allowblood,
                                                   allowskipchance=False,
                                                   setparams={"restricted": nation}, **options)
                    NationalSpellGenerationInfoCollector.spellrollsrepeated += 1
                if spell is not None:
                    NationalSpellGenerationInfoCollector.numberofgeneratedspells += 1
                    generatedspells.append(spell)
                    numberofgeneratedspells[nationid] += 1
                    # _writetoconsole("Spell successfully generated\n")
                    break

            # Only one national spell per effect
            del effectpool[choseneffect.name]

            if (len(effectpool) == 0) and (spell is None):
                raise ValueError(
                    f"Couldn't make a national spell for nation {nation}, guaranteed={commander.pathlevels}, "
                    f"randoms={commander.getrandompathpossibles()}")
    _writetoconsole(
        f"Attempted to generated {targetnumberofnationalspells} national spells for {nationcount} nations.\n")
    NationalSpellGenerationInfoCollector.print()


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

    opts.append(Option("-nationlist",
                       help="A list of nation IDs, separated by commas. If provided, national spells will only be generated for these nations.",
                       type=str, default=""))

    opts.append(Option("-spellidstart",
                       help="Starting Spell ID. (Allowed range for modded spells is 1300-3999)",
                       type=int, default=1300))

    opts.append(Option("-unitidstart",
                       help="Starting Monster ID. (Allowed range for modded units is 3500-8999)",
                       type=int, default=3500))

    opts.append(Option("-weaponidstart",
                       help="Starting Weapon ID. (Allowed range for modded weapons is 800+)",
                       type=int, default=800))

    opts.append(Option("-eventcodestart",
                       help="Starting Event Code. (Allowed range for these is -300 to -5000)",
                       type=int, default=800))

    opts.append(Option("-montagidstart",
                       help="Starting Montag ID. (Allowed range for modded weapons is 1000-100000)",
                       type=int, default=800))

    opts.append(Option("-montagscale",
                       help='Scale the number of units in montags. '
                            'Lower this if experiencing "monster ID too high" errors.',
                       type=float, default=1.0))

    opts.append(Option("-bloodcostscale",
                       help='Blood ritual spell costs are multiplied by this value. '
                            'Set to a value greater than 1.0 if you believe MagicGen blood is too strong.',
                       type=float, default=1.0))

    opts.append(Option("-clearvanillanationalspells",
                       help='If set to 1, vanilla national spells will all be removed. ',
                       type=int, default=1))

    opts.append(Option("-clearvanillagenericspells",
                       help='If set to 1, vanilla national spells will all be removed. ',
                       type=int, default=1))

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
