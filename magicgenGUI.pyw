import os
import queue
import subprocess
import sys
import threading
import nationals
import csv
import re

import PySimpleGUI as sg

CLARGS = ["spellsperlevel", "constructionfactor", "modlist", "nationalspells", "modname", "secondarychance",
          "summonsecondarychance", "researchmodifier", "fatiguemodflat", "fatiguemodmult", "pathlevelmodflat",
          "pathlevelmodmult", "outputfolder", "unitidstart", "spellidstart", "weaponidstart", "montagidstart",
          "eventcodestart", "montagscale"]

ERA_PREFIXES = {1: "EA", 2: "MA", 3: "LA"}

proc = None
nationselection = None
outputqueue = queue.Queue()

ver = "v2.0.0"


def output_polling_thread(timeout=0.1):
    """
    Readline blocks, which means it can't be used in the main thread without making the interface periodically
    unresponsive.
    This gets around the issue by having a thread do it and write the values to a queue. The queue can be polled
    without blocking in the main thread safely.
    """
    global proc
    while 1:
        if proc.poll() is None:
            # Magicgen's console output is, because I was weird, to stderr and not stdout
            # it redirects its stdout to a file instead
            # this blocks until there is a new output line
            content = proc.stderr.readline()
            if len(content) > 0:
                outputqueue.put(content)
        else:
            break


def spawn_worker_process(**kwargs):
    global proc, nationselection
    # Should double for release and testing
    # and hopefully also work on unix...
    tmp = os.path.join(os.getcwd(), "magicgen.exe")
    if os.path.isfile(tmp) and sys.platform.startswith("win"):
        paramlist = [tmp]
    else:
        paramlist = ["python", "magicgen.py"]

    paramlist += ["-run", "1"]

    if nationselection is not None:
        paramlist += ["-nationlist", ",".join(map(str, nationselection)).strip()]

    for key, paramval in kwargs.items():
        paramlist.append(f"-{key}")
        paramlist.append(f"{paramval}")
    path = os.path.join(os.getcwd(), "magicgen")
    outputqueue.put(f"Passing parameters: {paramlist}\n")

    proc = subprocess.Popen(
        paramlist, shell=False, cwd=os.getcwd(), bufsize=1,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        stdin=subprocess.PIPE,  # PyInstaller needs this or attempting the call throws "failed to execute script"
        universal_newlines=True)
    return proc


UP_ARROW = "˄"
DOWN_ARROW = "˅"

defaultfolder = os.path.join(os.getcwd(), "output")

NATIONS_PER_ROW = 3


def display_nationchoice(modstring):
    global nationselection
    # Reparse mod nations
    nationals.nationinfo = {}
    nationals.readVanilla()
    nationals.readMods(modstring)
    # Build layout
    elementlists = {1: [], 2: [], 3: []}
    # Keep the element keys for each category to enable the select/deselect buttons
    categorykeys = {1: [], 2: [], 3: []}
    # vanilla nations
    with open("nations.csv", "r", encoding="u8") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for line in reader:
            eraint = int(line["era"])
            if nationselection is None:
                ticked = True
            elif int(line["id"]) in nationselection:
                ticked = True
            else:
                ticked = False
            # Store as lambda to actually instantiate later
            # This seems to evaluate format strings when called, so fix them now
            text = f"{ERA_PREFIXES.get(eraint, '???')} {line['name']}"
            key = f"-NationPick{line['id']}-"
            box = lambda a=text, b=key, c=ticked: sg.Checkbox(a, k=b, default=c)
            if eraint not in elementlists:
                elementlists[eraint] = []
            elementlists[eraint].append(box)
            categorykeys[eraint].append(key)
    # mod nations
    for natid, modnation in nationals.nationinfo.items():
        uirow = []
        text = f"{ERA_PREFIXES.get(modnation.era, '???')} {modnation.name}"
        key = f"-NationPick{modnation.id}-"
        if nationselection is None:
            ticked = True
        elif modnation.id in nationselection:
            ticked = True
        else:
            ticked = False
        boxbuilder = lambda a=text, b=key, c=ticked: sg.Checkbox(a, k=b, default=c)
        elementlists[modnation.era].append(boxbuilder)
        categorykeys[modnation.era].append(key)

    # Make columns of these, otherwise the horizontal alignment is nonexistent
    categories = {}
    for eraint, elementlist in elementlists.items():
        categories[eraint] = []
        allcolumns = []
        for colindex in range(0, NATIONS_PER_ROW):
            columncontents = []
            elementindex = colindex
            while True:
                if elementindex >= len(elementlist):
                    break
                # Instantiate the lambdas prepared earlier
                columncontents.append([elementlist[elementindex]()])
                elementindex += NATIONS_PER_ROW
            allcolumns.append(
                sg.Column(columncontents, k=f"-Era{eraint}NationColumn{colindex}-", vertical_alignment="top"))
        categories[eraint].append(allcolumns)

    layout = [
        [sg.Text("Select the nations to generate national spells for.", k="-NationPickIntroLabel-")],
        [sg.Button("Select All"), sg.Button("Deselect All")],
    ]

    for eraid in categories:
        eraname = ERA_PREFIXES.get(eraid, "???")
        layout += [[sg.Text(DOWN_ARROW, k=f"-ToggleEra{eraid}Arrow-", enable_events=True),
                    sg.Text(f"{eraname} Nations", enable_events=True, k=f"-ToggleEra{eraid}Text-", font=("arial", 20))]]
        categories[eraid].insert(0, [sg.Button(f"Select All {eraname}", k=f"-SelectAllEra{eraid}-"),
                                     sg.Button(f"Deselect All {eraname}", k=f"-DeselectAllEra{eraid}-")])
        layout += [[sg.pin(sg.Column(categories[eraid], k=f"-Era{eraid}Category-", visible=False))]]

    layout += [[sg.Button("Close")]]

    visibility = {}

    window = sg.Window(f"Select Nations", layout)
    while True:
        event, values = window.read(timeout=100)
        if event is None:
            break

        # Update selections
        nationselection = []
        for era in range(1, 4):
            boxkeys = categorykeys[era]
            for key in boxkeys:
                if values[key]:
                    m = re.match("-NationPick([0-9]*)-", key)
                    nationid = int(m.groups()[0])
                    nationselection.append(nationid)

        if event == "Close":
            break
        if event.startswith("-ToggleEra"):
            eratoggled = int(event[10])
            newvis = not visibility.get(eratoggled, False)
            visibility[eratoggled] = newvis
            window[f"-Era{eratoggled}Category-"].update(visible=newvis)
            window[f"-ToggleEra{eratoggled}Arrow-"].update(UP_ARROW if newvis else DOWN_ARROW)
        if event in ["Select All", "Deselect All"]:
            selectionstate = event == "Select All"
            for era in range(1, 4):
                keys = categorykeys[era]
                for key in keys:
                    window[key].update(value=selectionstate)
        if event.startswith("-SelectAllEra") or event.startswith("-DeselectAllEra"):
            selectionstate = event.startswith("-SelectAllEra")
            # last character is another dash, so -2 is the era id
            era = int(event[-2])
            keys = categorykeys[era]
            for key in keys:
                window[key].update(value=selectionstate)
    window.close()

def detectids(window, modlist):
    "Detect sensible starting IDs based on the mods."
    nationals.readMods(modlist)
    startunitid = max(nationals.monsterids) + 1
    startweaponid = max(nationals.weaponids) + 1
    startspellid = max(nationals.spellids) + 1
    starteventid = min(nationals.eventcodes) - 1
    startmontagid = max(nationals.montagids) + 1
    window["-spellidstart-"].update(value=str(startspellid))
    window["-weaponidstart-"].update(value=str(startweaponid))
    window["-unitidstart-"].update(value=str(startunitid))
    window["-eventcodestart-"].update(value=str(starteventid))
    window["-montagidstart-"].update(value=str(startmontagid))


def main():
    global proc
    sg.theme("DarkBrown")

    output_left_col = [[
        sg.Text("Output Folder: ", k="-OutputFolderLabel-", pad=(7, 5), size=(10, 1)),
        sg.InputText(os.path.join(os.getcwd(), "output"), k="-outputfolder-", pad=(0, 0), size=(43, 1))
    ]]

    basic_category = [
        [sg.Text('Name of the mod. If left blank a rather unhelpful number will be generated at random.',
                 size=(50, 2), relief="ridge"),
         sg.InputText(key='-modname-', size=(50, 1))],
        [sg.Column(output_left_col),
         sg.FolderBrowse(initial_folder=defaultfolder, k="-FolderBrowser-")],
        [sg.Text('Number of spells to generate at each research level (14)', size=(50, 1), relief="ridge"),
         sg.InputText(key='-spellsperlevel-', size=(4, 1), default_text=14)],
        [sg.Text(
            'Construction will get only this proportion of the normal number of spells. This is intended to be '
            'less than 1.0. (0.33)',
            size=(50, 2), relief="ridge"),
            sg.InputText(key='-constructionfactor-', size=(4, 1), default_text=0.33)],
        [sg.Text(
            'Number of national spells to try to make per nation. These spells will be directed towards the '
            'paths the nation has access to. (12)',
            size=(50, 2), relief="ridge"), sg.InputText(key='-nationalspells-', size=(4, 1), default_text=12)],
        [sg.Text(
            'A list of .dm file paths, separated by commas. Files in the list will be scanned and nations '
            'defined in them will get national spells.'
            ' For example: C:/Users/[User]/AppData/Roaming/Dominions5/mods/magicgen.dm',

            size=(50, 4), relief="ridge"), sg.Multiline(key='-modlist-', size=(50, 5))],
        [sg.Button("Select Nations for National Spells")],

    ]

    adv_category = [
        [sg.Text('What percentage of non-summoning spells will generate with a secondary effect. (20)', size=(50, 2),
                 relief="ridge"),
         sg.InputText(key='-secondarychance-', size=(4, 1), default_text=20)],
        [sg.Text(
            'What percentage of summoning spells will generate with a secondary effect. (50)',
            size=(50, 2), relief="ridge"),
            sg.InputText(key='-summonsecondarychance-', size=(4, 1), default_text=50)],
        [sg.Text(
            'Research modifier: This number is subtracted from the research level of all spells, making more powerful '
            'spells appear at lower research. A value of 5 will make spells that are normally research 9 appear at '
            'research 4 instead. A value of -1 here will make spells normally research 9 inaccessible, and level 9 '
            'will instead be filled by spells that would normally generate at research 8. (0)',
            size=(50, 6), relief="ridge"),
            sg.InputText(key='-researchmodifier-', size=(4, 1), default_text=0)],

        [sg.Text(
            'Path level modifier: This number is added to the path level requirement of all spells. A value of 1'
            ' will make all spells harder to cast by requring a path level 1 higher than normal. Negative numbers '
            'are accepted to make spells easier to cast. Path requirements cannot be lowered below 1.'
            '(to a minimum of 1). Negative values will make spells easier to cast. (0)',
            size=(50, 6), relief="ridge"),
            sg.InputText(key='-pathlevelmodflat-', size=(4, 1), default_text=0)],

        [sg.Text(
            'Path level multiplier: The path level requirement of all spells is multiplied by this value. Leave at '
            '1.0 for no change. Values over 1.0 will increase the level required to cast spells, and less than 1.0 '
            'will lower the levels. Spells with higher level requirements will be affected more by this. (1.0)',
            size=(50, 5), relief="ridge"),
            sg.InputText(key='-pathlevelmodmult-', size=(4, 1), default_text=1.0)],

        [sg.Text(
            'Fatigue modifier: Adds this number to the fatigue requirement of all spells. Negative values are allowed.'
            ' Negative values will make spells easier to cast, but the fatigue for casting '
            'a spell will never go below 0. (0)',
            size=(50, 4), relief="ridge"),
            sg.InputText(key='-fatiguemodflat-', size=(4, 1), default_text=0)],

        [sg.Text(
            'Fatigue multiplier: Multiplies the fatigue cost of all spells by this value. Leave at 1.0 for no change.'
            ' Values over 1.0 will increase the fatigue required to cast spells, and less than 1.0 will lower the'
            ' fatigue. Spells with higher fatigue costs will be affected more by this. (1.0)'
            ,
            size=(50, 5), relief="ridge"),
            sg.InputText(key='-fatiguemodmult-', size=(4, 1), default_text=1.0)],

    ]

    id_category = [
        [sg.Text('These settings change the starting ID used for each of the listed moddable objects. Change these'
                 ' only when using MagicGen in combination with other mods. They should be set to ranges outside of '
                 'those used by the other mods in the game.', size=(100, 2))],
        [sg.Text('Starting Spell ID. (Allowed range for modded spells is 1300-3999)', size=(50, 2),
                 relief="ridge"),
         sg.InputText(key='-spellidstart-', size=(4, 1), default_text=1300)],
        [sg.Text('Starting Monster ID. (Allowed range for modded units is 3500-8999)', size=(50, 2),
                 relief="ridge"),
         sg.InputText(key='-unitidstart-', size=(4, 1), default_text=3500)],
        [sg.Text('Starting Weapon ID. (Allowed range for modded weapons is 800-1999)', size=(50, 2),
                 relief="ridge"),
         sg.InputText(key='-weaponidstart-', size=(4, 1), default_text=800)],
        [sg.Text('Starting Montag ID. (Allowed range for modded weapons is 1000-100000)', size=(50, 2),
                 relief="ridge"),
         sg.InputText(key='-montagidstart-', size=(4, 1), default_text=1000)],
        [sg.Text('Starting Event Code. (Allowed range for these is -300 to -5000)', size=(50, 2),
                 relief="ridge"),
         sg.InputText(key='-eventcodestart-', size=(4, 1), default_text=-300)],
        [sg.Button("Autodetect Good Starting IDs")],
        [sg.Text('Scale the number of units in montags. Lower this if experiencing "monster ID too high" errors. '
                 'Increase to make random unit pools larger.', size=(50, 3),
                 relief="ridge"),
         sg.InputText(key='-montagscale-', size=(4, 1), default_text=1.0)],
    ]

    layout = [[sg.Text("Welcome to MagicGen!", k="-welcome-", font=("arial", 40))],
              [sg.Text(UP_ARROW, k="-ToggleBasicOptionsArrow-", enable_events=True),
               sg.Text("Basic Options", enable_events=True, k="-ToggleBasicOptionsLabel-", font=("arial", 20))],
              [sg.pin(sg.Column(basic_category, k="-BasicOptions-"))],
              [sg.Text(DOWN_ARROW, k="-ToggleAdvOptionsArrow-", enable_events=True),
               sg.Text("Advanced Options", enable_events=True, k="-ToggleAdvOptionsLabel-", font=("arial", 20))],
              [sg.pin(sg.Column(adv_category, k="-AdvOptions-", visible=False))],
              [sg.Text(DOWN_ARROW, k="-ToggleIDOptionsArrow-", enable_events=True),
               sg.Text("Configure IDs", enable_events=True, k="-ToggleIDOptionsLabel-", font=("arial", 20))],
              [sg.pin(sg.Column(id_category, k="-IDOptions-", visible=False))],
              [sg.Button('Generate', size=(7, 1)), sg.Button('Quit', size=(7, 1))],
              [sg.Multiline("", autoscroll=True, size=(100, 7), key="-OUTPUT-")]]


    visibility = {"BasicOptions": True, "AdvOptions": False, "IDOptions":False}
    window = sg.Window(f"MagicGen {ver}: Generating New Spellbooks Since 1986!", layout)

    # Event Loop to process "events" and get the "values" of the inputs
    generating = False
    while True:
        event, values = window.read(timeout=100)
        if event == sg.WIN_CLOSED or event == 'Quit':
            break

        if generating:
            if proc is not None:
                while 1:
                    try:
                        new = outputqueue.get_nowait().strip()
                        old = window["-OUTPUT-"].Get()
                        window["-OUTPUT-"].update(old + new)
                    except queue.Empty:
                        break

                if proc.poll() is not None:
                    generating = False

        if event == 'Generate':
            if generating:
                continue
            generating = True
            clargdict = {}
            for argname in CLARGS:
                argval = values[f"-{argname}-"]
                if argval.strip() != "":
                    clargdict[argname] = argval
            spawn_worker_process(**clargdict)
            outputthread = threading.Thread(target=output_polling_thread)
            outputthread.start()

        if event == "Select Nations for National Spells":
            display_nationchoice(values["-modlist-"])

        for section in ["AdvOptions", "BasicOptions", "IDOptions"]:
            if event.startswith(f"-Toggle{section}"):
                newvis = not visibility[section]
                visibility[section] = newvis
                window[f"-Toggle{section}Arrow-"].update(UP_ARROW if newvis else DOWN_ARROW)
                window[f"-{section}-"].update(visible=newvis)
                break

        if event == "Autodetect Good Starting IDs":
            detectids(window, values["-modlist-"]);

    window.close()


if __name__ == "__main__":
    main()
