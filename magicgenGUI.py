import sys

sys.path.append("PySimpleGUI/PySimpleGUI.py")
import PySimpleGUI as sg


def main():
    layout = [[sg.Text('Welcome to the magicgen GUI please full all fields and press submit')],
              [sg.Text('amount of spells on each level'), sg.InputText(key='-spellsPerLevel-')],
              [sg.Button('Submit'), sg.Button('Cancel')]]

    window = sg.Window('magicgenGui', layout)
    # Event Loop to process "events" and get the "values" of the inputs
    while True:
        event, values = window.read()

        if event == sg.WIN_CLOSED or event == 'Quit':
            break

        if event == 'Submit':
            print('The events was ', event, 'You input', values['-spellsPerLevel-'])

    window.close()


if __name__ == "__main__":
    main()
