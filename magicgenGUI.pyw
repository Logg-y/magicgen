import os
import queue
import subprocess
import sys
import threading

import PySimpleGUI as sg

CLARGS = ["spellsperlevel", "constructionfactor", "modlist", "nationalspells", "modname", "secondarychance",
          "summonsecondarychance", "researchmodifier", "fatiguemodflat", "fatiguemodmult", "pathlevelmodflat",
          "pathlevelmodmult", "outputfolder"]
proc = None
outputqueue = queue.Queue()

ver = "v1.1.2"


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
    global proc
    # Should double for release and testing
    # and hopefully also work on unix...
    tmp = os.path.join(os.getcwd(), "magicgen.exe")
    if os.path.isfile(tmp) and sys.platform.startswith("win"):
        paramlist = [tmp]
    else:
        paramlist = ["python", "magicgen.py"]

    paramlist += ["-run", "1"]
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
            'research 5 instead. A value of -1 here will make spells normally research 9 inaccessible, and level 9 '
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

    layout = [[sg.Text("Welcome to MagicGen!", k="-welcome-", font=("arial", 40))],
              [sg.Text(UP_ARROW, k="-ToggleBasicOptionsArrow-", enable_events=True),
               sg.Text("Basic Options", enable_events=True, k="-ToggleBasicOptionsLabel-", font=("arial", 20))],
              [sg.pin(sg.Column(basic_category, k="-BasicOptions-"))],
              [sg.Text(DOWN_ARROW, k="-ToggleAdvOptionsArrow-", enable_events=True),
               sg.Text("Advanced Options", enable_events=True, k="-ToggleAdvOptionsLabel-", font=("arial", 20))],
              [sg.pin(sg.Column(adv_category, k="-AdvOptions-", visible=False))],
              [sg.Button('Generate', size=(7, 1)), sg.Button('Quit', size=(7, 1))],
              [sg.Multiline("", autoscroll=True, size=(100, 7), key="-OUTPUT-")]]

    visibility = {"BasicOptions": True, "AdvOptions": False}
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

        for section in ["AdvOptions", "BasicOptions"]:
            if event.startswith(f"-Toggle{section}"):
                newvis = not visibility[section]
                visibility[section] = newvis
                window[f"-Toggle{section}Arrow-"].update(UP_ARROW if newvis else DOWN_ARROW)
                window[f"-{section}-"].update(visible=newvis)
                break

    window.close()


if __name__ == "__main__":
    main()
