# MagicGen

Inspired by NationGen, this program generates mod files that entirely replace the normal spellbook. There are now options to preserve vanilla generic and/or national spells, previously everything would be eliminated. Magic items are unaffected. Items which could cast spells in vanilla should still be able to cast the same spells, however. Banishment and smite spells however are affected.

It seems important enough to mention that the mod inspector has slight issues with the mods this program generates: it appears to sometimes get numbers and nations for national spells wrong, as well as ignoring a number of more recently added modding commands. The game however displays things fine, and as such it is worth checking spells in-game if the inspector displays something unexpected.

Currently this is still in early stages but should just about be at the point where it is playable. Feedback on existing content as well as suggestions for more things to include are very welcome.

Updates to the csv data files and unit description folder should be obtained from the dom5inspector github repo (which is also under the included GPL v3) and is available at https://github.com/larzm42/dom5inspector - (specifically, check the gamedata folder)

## Thanks

Larz, for continuing to maintain the executable datamining scripts.

PysimpleGUI for enabling the GUI (https://github.com/PySimpleGUI/PySimpleGUI).

Koenradar for cleanups and making the basis for the UI!

The many people who have thrown ideas and feedback my way, and who have been willing to jump in and play with it!
