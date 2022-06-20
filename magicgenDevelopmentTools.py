import os
import sys
import traceback
import magicgen
import time
import re

import PySimpleGUI as sg

OUTPUT_AREA_SIZE = 20

def scalingToolEffectLookup(text):
    layout = [[sg.Text("Search: "), sg.InputText(text, k="-effectlookuptext-")],
        [sg.Listbox([], sg.LISTBOX_SELECT_MODE_SINGLE, k="-effectlookuplist-", size=(50, 20))],
        [sg.Button("OK")]
    ]
    window = sg.Window("Effect Lookup", layout)
    lasttime = 0
    laststring = ""
    updatedlistbox = False
    while 1:
        event, values = window.read(timeout=100)


        if event == sg.WIN_CLOSED or event == 'Quit':
            break

        if values["-effectlookuptext-"] != laststring:
            lasttime = time.time()
            laststring = values["-effectlookuptext-"]
            updatedlistbox = False
        elif updatedlistbox == False and time.time() - lasttime > 0.5:
            possibleeffects = []
            text = values["-effectlookuptext-"]
            for effect in magicgen.utils.spelleffects:
                if text.lower() in effect.lower():
                    possibleeffects.append(effect)
            possibleeffects = sorted(possibleeffects)
            print(f"Updated with {len(possibleeffects)}")
            window["-effectlookuplist-"].update(values=possibleeffects)
            updatedlistbox = True

        if event == "OK":
            retval = window["-effectlookuplist-"].get()
            if len(retval) == 0:
                retval = ""
            else:
                retval = retval[0]
            window.close()
            print(f"Return {retval}")
            return retval
    return ""


def bulkEditConfigWindow(selectedAttributes):

    rows = []
    for attrib, default in selectedAttributes.items():
        rows.append([sg.Checkbox(attrib, k=f"{attrib}Checkbox", default=default)])

    layout = [[sg.Text("Attributes to match/update: ")],
        *rows,
        [sg.Button("OK")]
    ]
    window = sg.Window("Bulk Edit Config", layout)

    while 1:
        event, values = window.read(timeout=100)

        if event == sg.WIN_CLOSED:
            return selectedAttributes

        for attribute in selectedAttributes:
            selectedAttributes[attribute] = values[f"{attribute}Checkbox"]

        if event == "OK":
            window.close()
            print(selectedAttributes)
            return selectedAttributes

def overwriteSpellData(attribs_to_copy, fakespell, spelleffect, giveconfirm=True):
    if not giveconfirm:
        response = "ok"
    else:
        response = sg.popup_ok_cancel(f"Are you sure you want to overwrite the data of {spelleffect.name}"
                                  f" with the values currently shown?")

    if fakespell is None:
        return
    if response.lower() == "ok":
        tochange = {}
        changecount = {}
        for attrib in attribs_to_copy:
            if getattr(fakespell, attrib) != getattr(spelleffect, attrib):
                setattr(spelleffect, attrib, getattr(fakespell, attrib))
                tochange[attrib] = getattr(fakespell, attrib)
        with open(spelleffect.fp, "r") as datafile:
            content = datafile.read().split("\n")
        effstartlineindex = None
        effendlineindex = None
        lineindex = -1
        while True:
            lineindex += 1
            line = content[lineindex]
            if line.strip().startswith("--"):
                continue
            if line.strip() == "":
                continue
            line = line.strip()
            # Locate the start of this spell effect.
            if effstartlineindex is None:
                if not line.startswith("#neweffect"):
                    continue
                m = re.match(f'#neweffect\\W*"{spelleffect.name}"', line)
                if m is not None:
                    effstartlineindex = lineindex
                    continue
            else:
                # Check to see if this line contains one of the attribs we want to change
                # Importantly, this will change ALL instances of an attribute, as there is nothing illegal
                # about having two values for the same one, the second will take precedence
                for attrib in tochange:
                    if line.startswith(f"#{attrib}"):
                        print(f"Change value for line: {line}")
                        newline = f"#{attrib} {getattr(fakespell, attrib)}"
                        content[lineindex] = newline
                        changecount[attrib] = changecount.get(attrib, 0) + 1
                        break

                if line == "#end":
                    # Insert all the attributes that we haven't changed yet
                    for attrib in tochange:
                        if changecount.get(attrib, 0) == 0:
                            content.insert(lineindex, f"#{attrib} {getattr(fakespell, attrib)}")
                            print(f"Inserted new line for attrib {attrib}")
                    break
        with open(spelleffect.fp, "w") as datafile:
            for line in content:
                datafile.write(line.strip() + "\n")

def scalingTool():
    sg.theme("DarkBrown")

    lookuprow = [sg.Text("Lookup Effect Name: ", size=(15, 1)),
         sg.InputText("", k="-lookupspelleffect-", size=(40, 1)),
         sg.Button("Find", k="-lookupspellfind-"),
         sg.Button("Load", k="-lookupspellload-"),
         sg.Button("Save", k="-overwritespelldata-")]

    basicattrib_col = [
        [sg.Text("aoe: ", size=(10, 1)),
         sg.InputText("", k="-aoe-", size=(7, 1))],
        [sg.Text("damage: ", size=(10, 1)),
         sg.InputText("", k="-damage-", size=(7, 1))],
        [sg.Text("nreff: ", size=(10, 1)),
         sg.InputText("", k="-nreff-", size=(7, 1))],
        [sg.Text("effectnum: ", size=(10, 1)),
         sg.InputText("", k="-effect-", size=(7, 1))],
        [sg.Text("maxbounces: ", size=(10, 1)),
         sg.InputText("", k="-maxbounces-", size=(7, 1))],
        [sg.Text("pathlevel: ", size=(10, 1)),
         sg.InputText("", k="-pathlevel-", size=(7, 1))],
        [sg.Text("fatiguecost: ", size=(10, 1)),
         sg.InputText("", k="-fatiguecost-", size=(7, 1))],
    ]

    scalebool_col = [
        [sg.Text("Scale aoe: ", size=(12, 1)),
         sg.InputText("", k="-scaleaoe-", size=(1, 1))],
        [sg.Text("Scale damage: ", size=(12, 1)),
         sg.InputText("", k="-scaledamage-", size=(1, 1))],
        [sg.Text("Scale nreff: ", size=(12, 1)),
         sg.InputText("", k="-scalenreff-", size=(1, 1))],
        [sg.Text("Scale effectnum: ", size=(12, 1)),
         sg.InputText("", k="-scaleeffect-", size=(1, 1))],
        [sg.Text("Scale maxbounces: ", size=(12, 1)),
         sg.InputText("", k="-scalemaxbounces-", size=(1, 1))],
    ]

    scaleparam_col = [
        [sg.Text("scalerate: ", size=(15, 1)),
         sg.InputText("", k="-scalerate-", size=(7, 1))],
        [sg.Text("minpower: ", size=(15, 1)),
         sg.InputText("", k="-power-", size=(7, 1))],
        [sg.Text("maxpower: ", size=(15, 1)),
         sg.InputText("", k="-maxpower-", size=(7, 1))],
        [sg.Text("scalecost: ", size=(15, 1)),
         sg.InputText("", k="-scalecost-", size=(7, 1))],
        [sg.Text("pathperresearch: ", size=(15, 1)),
         sg.InputText("", k="-pathperresearch-", size=(7, 1))],
        [sg.Text("scalefatigueexponent: ", size=(15, 1)),
         sg.InputText("", k="-scalefatigueexponent-", size=(7, 1))],
        [sg.Text("scalefatiguemult: ", size=(15, 1)),
         sg.InputText("", k="-scalefatiguemult-", size=(7, 1))],
        [sg.Text("fatigueperresearch: ", size=(15, 1)),
         sg.InputText("", k="-fatigueperresearch-", size=(7, 1))]
    ]

    outputarea = []
    for x in range(0, OUTPUT_AREA_SIZE):
        outputarea.append([sg.Text("", k=f"-output{x}-", visible=False, size=(50, 1))])

    mainlayout = [ lookuprow,
              [sg.Column(basicattrib_col), sg.Column(scalebool_col), sg.Column(scaleparam_col)],
              [sg.HorizontalSeparator()],
              [sg.Column(outputarea, k="-outputarea-")]
            ]

    bulkedit = [[sg.Button("Find Analogous", k="-bulkeditfindanalogous-"),
                 sg.Button("Save Selected", k="-bulkeditsave-")],
                [sg.Button("Select All", k="-bulkeditselall-"),
                 sg.Button("Select None", k="-bulkeditselnone-"),
                 sg.Button("Config", k="-bulkeditconfig-")],
                [sg.Column([], k="-bulkeditlist-", scrollable=True, expand_y=True, expand_x=False, vertical_scroll_only=True)]]


    layout = [sg.vtop([sg.Column(mainlayout, k="-main-"),
              sg.Frame("Bulk Edit", bulkedit, k="-bulkedit-", size=(300, 500))])]


    window = sg.Window(f"MagicGen Scaling Tool", layout)
    window.finalize()

    #window["-main-"].expand(False, False, False)
    #window["-bulkedit-"].expand(True, True, True)
    #window["-bulkeditlist-"].expand(True, False, False)

    attribs_to_copy = ["aoe", "damage", "nreff", "effect", "maxbounces", "pathlevel", "fatiguecost",
                       "scalerate", "power", "maxpower", "scalecost", "pathperresearch", "scalefatigueexponent", "scalefatiguemult", "fatigueperresearch"]
    flags = {"aoe":32, "damage":64, "maxbounces":128, "effect":256, "nreff":16}

    lastflags = -1
    lastattribs = {}
    for attrib in attribs_to_copy:
        lastattribs[attrib] = -1

    lowercaseSpellLookups = {}
    for spellname in magicgen.utils.spelleffects:
        lowercaseSpellLookups[spellname.lower()] = spellname

    updated = False
    lastupdate = -1
    fakespell = None
    bulkEditSelectedAttributes = {"damage":False, "effect":True, "spec":False, "power":False, "maxpower":False,
                                  "fatiguecost":True, "scalerate":True, "nreff":True, "pathlevel":False, "scalecost":True,
                                  "scalefatigueexponent":True, "scalefatiguemult":True, "schools":False, "scalerate":True,
                                  "aoe":False}
    bulkEditCheckboxIndexesToEffectNames = {}
    while True:
        event, values = window.read(timeout=100)
        if event == sg.WIN_CLOSED or event == 'Quit':
            break

        if event == "-bulkeditfindanalogous-":
            selectedeffect = magicgen.utils.spelleffects.get(values["-lookupspelleffect-"], None)
            print(f"Sel: {selectedeffect}")
            if selectedeffect is not None and bulkEditSelectedAttributes is not None:
                similar = []
                for name, eff in magicgen.utils.spelleffects.items():
                    isSimilar = True
                    for param, matched in bulkEditSelectedAttributes.items():
                        if not matched:
                            continue
                        if getattr(selectedeffect, param) != getattr(eff, param):
                            isSimilar = False
                            break
                    if isSimilar:
                        similar.append(eff.name)
                i = 0
                bulkEditCheckboxIndexesToEffectNames = {}
                while 1:
                    key = f"Checkbox{i}"
                    if key not in values:
                        break
                    window[key].update(False, text="", visible=False)
                    i += 1
                newlayout = []
                similar = sorted(similar)
                for i, similarEffName in enumerate(similar):
                    key = f"Checkbox{i}"
                    if key in values:
                        window[key].update(text=similarEffName, visible=True)
                        window[key].update(True)
                    else:
                        row = [sg.Checkbox(similarEffName, default=True, k=key)]
                        newlayout.append(row)
                    bulkEditCheckboxIndexesToEffectNames[key] = similarEffName
                scroll = i >= 10
                window["-bulkeditlist-"].expand(True, True, True)
                window.extend_layout(window["-bulkeditlist-"], newlayout)
                window["-bulkeditlist-"].contents_changed()
                print(f"There are {len(similar)} matches!")

        if event in ["-bulkeditselall-", "-bulkeditselnone-"]:
            val = "all" in event
            i = 0
            while 1:
                key = f"Checkbox{i}"
                if key not in values:
                    break
                window[key].update(val)
                i += 1
            window["-bulkeditlist-"].contents_changed()

        if event == "-bulkeditsave-":
            if bulkEditSelectedAttributes is not None:
                response = sg.popup_ok_cancel(f"Are you sure you want to overwrite the data of all ticked effects"
                                          f" with the values currently shown?")

                if response.lower() == "ok":
                    i = 0
                    bulkEditAttribs = []
                    for attrib, shouldcopy in bulkEditSelectedAttributes.items():
                        if shouldcopy:
                            bulkEditAttribs.append(attrib)
                    while 1:
                        key = f"Checkbox{i}"
                        if key not in values:
                            break
                        i += 1
                        if not values[key]:
                            continue
                        if key not in bulkEditCheckboxIndexesToEffectNames:
                            print(f"Checkbox {key} doesn't have a corresponding effect, skipped")
                            continue
                        spelleffect = magicgen.utils.spelleffects.get(bulkEditCheckboxIndexesToEffectNames[key], None)
                        if spelleffect is not None:
                            print(f"Set {bulkEditAttribs} for {spelleffect.name}")
                            overwriteSpellData(bulkEditAttribs, fakespell, spelleffect, giveconfirm=False)

        if event == "-bulkeditconfig-":
            bulkEditSelectedAttributes = bulkEditConfigWindow(bulkEditSelectedAttributes)

        if event == "-lookupspellfind-":
            val = scalingToolEffectLookup(values["-lookupspelleffect-"])
            window["-lookupspelleffect-"].update(val)

        if event == "-lookupspellload-":
            spelleffect = magicgen.utils.spelleffects.get(values["-lookupspelleffect-"], None)
            if spelleffect is None:
                realeffname = lowercaseSpellLookups.get(values["-lookupspelleffect-"].lower(), None)
                if realeffname is not None:
                    spelleffect = magicgen.utils.spelleffects.get(realeffname, None)
                    window["-lookupspelleffect-"].update(realeffname)
            if spelleffect is not None:
                for attrib in attribs_to_copy:
                    window[f"-{attrib}-"].update(getattr(spelleffect, attrib))
                for flagname, flagvalue in flags.items():
                    if spelleffect.spelltype & flagvalue:
                        window[f"-scale{flagname}-"].update("1")
                    else:
                        window[f"-scale{flagname}-"].update("0")
                updated = False
                lastupdate = 0.0

        if event == "-overwritespelldata-":
            spelleffect = magicgen.utils.spelleffects.get(values["-lookupspelleffect-"], None)
            if spelleffect is None:
                sg.popup(f"Spell effect {values['-lookupspelleffect-']} not found.")
            else:
                overwriteSpellData(attribs_to_copy, fakespell, spelleffect, giveconfirm=True)


        haschanged = False
        currflags = 0
        for flagname, flagvalue in flags.items():
            val = values[f"-scale{flagname}-"]
            if val != "0":
                currflags += flagvalue

        if currflags != lastflags:
            haschanged = True
            lastflags = currflags

        for attrib in attribs_to_copy:
            if lastattribs[attrib] != values[f"-{attrib}-"]:
                lastattribs[attrib] = values[f"-{attrib}-"]
                haschanged = True

        if haschanged:
            updated = False

        if not updated and time.time() - lastupdate > 0.5:
            lastupdate = time.time()
            updated = True
            print("HAS CHANGED")
            outputdata = []
            try:
                minresearch = int(values["-power-"])
                maxresearch = int(values["-maxpower-"])
                fakespell = magicgen.SpellEffect()
                fakespell.name = "Fake Spell for Scaling Testing"
                fakespell.spelltype = currflags
                fakespell.secondarypathchance = 0.0
                effno = int(values["-effect-"])
                # need to set ritual flag
                if effno > 10000:
                    fakespell.spelltype |= 4

                for attrib in attribs_to_copy:
                    attribstring = values[f"-{attrib}-"]
                    if "." in attribstring:
                        setattr(fakespell, attrib, float(attribstring))
                    else:
                        setattr(fakespell, attrib, int(attribstring))
                for rl in range(minresearch, maxresearch+1):
                    try:
                        s = fakespell.rollSpell(researchlevel=rl, allowskipchance=False, allowblood=False, blockmodifier=True,
                                                blocksecondary=True)
                        print("Generated spell")
                        if s is not None:
                            text = f"RL {rl}, x{s.path1level}:"
                            if currflags & flags["aoe"] or s.aoe != int(values["-aoe-"]):
                                text += f" aoe {s.aoe}"
                                if s.aoe >= 1000:
                                    real = (s.aoe % 1000) + (s.path1level * (s.aoe // 1000))
                                    text += f" ({real})"

                            if currflags & flags["damage"] or s.damage != int(values["-damage-"]):
                                text += f" damage {s.damage}"
                                if s.damage >= 1000:
                                    real = (s.damage % 1000) + (s.path1level * (s.damage // 1000))
                                    text += f" ({real})"

                            if currflags & flags["nreff"] or s.nreff != int(values["-nreff-"]):
                                text += f" nreff {s.nreff}"
                                if s.nreff >= 1000:
                                    real = (s.nreff % 1000) + (s.path1level * (s.nreff // 1000))
                                    text += f" ({real})"

                            if currflags & flags["effect"] or s.effect != int(values["-effect-"]):
                                text += f" effect {s.effect}"

                            if currflags & flags["maxbounces"] or s.maxbounces != int(values["-maxbounces-"]):
                                text += f" maxbounces {s.maxbounces}"

                            text += f" fatiguecost {s.fatiguecost}"

                            if s.nreff > 1:
                                real = (s.nreff % 1000) + (s.path1level * (s.nreff // 1000))
                                ratio = round(s.fatiguecost/real, 3)
                                text += f" ({ratio} per effect)"

                        else:
                            text = f"RL{rl}: <spell failed to generate>"
                    except:
                        print(f"Failed to generate spell: {traceback.print_exc()}")
                        text = f"RL{rl}: <exception while generating spell, consider restarting this utility>"
                    outputdata.append(text)
            except ValueError:
                # likely a conversion from the string fields into some kind of number failed
                outputdata.append("Probably failed to convert text above to a numeric value")

            for x in range(0, OUTPUT_AREA_SIZE):
                window[f"-output{x}-"].update(visible=False)

            for i, text in enumerate(outputdata):
                if i == (OUTPUT_AREA_SIZE-1) and len(outputdata) > (i+1):
                    text = f"<{len(outputdata) + 1 - OUTPUT_AREA_SIZE} more rows not shown>"
                print(text)
                window[f"-output{i}-"].update(text)
                window[f"-output{i}-"].update(visible=True)


                if i == (OUTPUT_AREA_SIZE-1):
                    break

            print("done with change")
            print(outputdata)







    window.close()


if __name__ == "__main__":
    magicgen._parseDataFiles()
    try:
        scalingTool()
    except Exception as e:
        with open("magicgenGUIerror.txt", "w") as f:
            f.write(traceback.format_exc())
        raise e