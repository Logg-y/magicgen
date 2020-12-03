import subprocess
import sys
import threading

sys.path.append("PySimpleGUI/PySimpleGUI.py")
import PySimpleGUI as sg


def process_thread(spellsperlevel, constructionfactor, modlist, nationalspells, modname):
    global proc

    proc = subprocess.run(
        ['magicgen', '-run', '-spellsperlevel ' + spellsperlevel, '-constructionfactor ' + constructionfactor,
         '-modlist ' + modlist, '-nationalspells ' + nationalspells, '-modname ' + modname], shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT)


def main():
    sg.theme("DarkBrown")
    layout = [[sg.Text('Welcome to the magicgen GUI please fill all relevant fields and press submit.', size=(55, 1),
                       relief="groove")],
              [sg.Text('')],
              [sg.Text('Name of the mod. If left blank a rather unhelpful number will be generated at random.',
                       size=(50, 2), relief="ridge"),
               sg.InputText(key='-modname-', size=(50, 1))],
              [sg.Text('Number of spells to try generating at each research level (14)', size=(50, 1), relief="ridge"),
               sg.InputText(key='-spellsPerLevel-', size=(4, 1), default_text=14)],
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
              [sg.Button('Generate', size=(7, 1)), sg.Button('Cancel', size=(7, 1)),
               sg.Text("While generating your os might alert you of non-responsiveness please wait.",
                       relief="groove", key="-genHelp-", visible=True)]]

    window = sg.Window('magicgenGui', layout, location=(145, 390))
    # Event Loop to process "events" and get the "values" of the inputs
    while True:
        event, values = window.read()

        if event == sg.WIN_CLOSED or event == 'Quit':
            break

        if event == 'Generate':
            thread = threading.Thread(
                target=process_thread(values['-spellsPerLevel-'], values['-constructionfactor-'], values['-modlist-'],
                                      values['-nationalspells-'], values['-modname-']),
                daemon=True)
            thread.start()

            while True:
                thread.join(timeout=.1)
                if not thread.is_alive():
                    break

            output = proc.__str__().replace('\\r\\n', '\n')
            sg.popup_scrolled(output, font='Courier 10', size=(100, 20), location=(960, 390),
                              title='magicgen console log')

    window.close()


if __name__ == "__main__":
    main()
