import re

from Enums.SpellTypes import SpellTypes
from Exceptions.NameTooLongException import NameTooLongException
from Services import utils
from Services.Pluraliser import Pluraliser
from Services.Synonyms import Synonyms

synonyms = Synonyms()
pluraliser = Pluraliser()


def parsestring(string, plural=False, aoe=0, spelltype=0, titlecase=False, spell=None, isspell=False):
    # This is needed for the variable descriptions in modular globals
    if len(string) == 0:
        return string
    aoe = aoe % 1000
    parsedname = string
    # print(f"mode is plural: {plural}")
    if plural:
        parsedname = parsedname.replace("ARTICLE_N", "")
        parsedname = parsedname.replace("ARTICLE", "")
        parsedname = parsedname.replace("PRONOUN_POS", "their")
        parsedname = parsedname.replace("PRONOUN_SUB", "they")
        parsedname = parsedname.replace("PRONOUN", "them")
    else:
        parsedname = parsedname.replace("ARTICLE_N", "an")
        parsedname = parsedname.replace("ARTICLE", "a")
        parsedname = parsedname.replace("PRONOUN_POS", "his")
        parsedname = parsedname.replace("PRONOUN_SUB", "he")
        parsedname = parsedname.replace("PRONOUN", "him")

    if spelltype & SpellTypes.BUFF:
        if aoe == 0:
            parsedname = parsedname.replace("SUBJECT", "the caster")
            parsedname = parsedname.replace("SIZE", "tiny")
        elif aoe < 5:
            parsedname = parsedname.replace("SUBJECT", "a $few$ soldiers")
            parsedname = parsedname.replace("SIZE", "small")
        elif aoe < 20:
            parsedname = parsedname.replace("SUBJECT", "many soldiers")
            parsedname = parsedname.replace("SIZE", "large")
        elif aoe < 50:
            parsedname = parsedname.replace("SUBJECT", "a large group of soldiers")
            parsedname = parsedname.replace("SIZE", "massive")
        else:
            parsedname = parsedname.replace("SUBJECT", "the entire army")
            parsedname = parsedname.replace("SIZE", "massive")
    elif spelltype & SpellTypes.EVOCATION:
        if aoe == 0:
            parsedname = parsedname.replace("SUBJECT", "one enemy")
            parsedname = parsedname.replace("SIZE", "tiny")
        elif aoe < 5:
            parsedname = parsedname.replace("SUBJECT", "a $few$ enemies")
            parsedname = parsedname.replace("SIZE", "small")
        elif aoe < 20:
            parsedname = parsedname.replace("SUBJECT", "many enemies")
            parsedname = parsedname.replace("SIZE", "large")
        elif aoe < 80:
            parsedname = parsedname.replace("SUBJECT", "a massive group of enemies")
            parsedname = parsedname.replace("SIZE", "massive")
        else:
            parsedname = parsedname.replace("SUBJECT", "the entire battlefield")
            parsedname = parsedname.replace("SIZE", "enormous")

    while 1:
        m = re.search("[$](.+?)[$]", parsedname)
        if m is None:
            break
        text = m.groups()[0]
        pluralised = synonyms.get(text)
        # print(string)
        parsedname = re.sub(f"[$]{text}[$]", pluralised, parsedname)
    # print(string)

    while 1:
        m = re.search("%(.+?)%", parsedname)
        if m is None:
            break
        text = m.groups()[0]
        if plural:
            pluralised = pluraliser.pluralise(text)
        else:
            pluralised = text
        parsedname = re.sub(f"%{text}%", pluralised, parsedname)

    # remove double spaces
    parsedname = parsedname.replace("  ", " ")
    parsedname = parsedname.strip()
    parsedname = parsedname[0].upper() + parsedname[1:]

    if titlecase:
        words = parsedname.split(" ")
        out = ""
        for pos, word in enumerate(words):
            if word.lower() not in ["a", "in", "from", "and", "of", "for", "the", "after", "before"] or pos == 0:
                out += word[0].upper() + word[1:]
            else:
                out += word.lower()
            out += " "
        parsedname = out.strip()


    # Don't give prefixes to nextspells, this makes no sense as they tend not to change much
    # ... or to nationals, at least for now
    if isspell and not spell.isnextspell and spell.restricted is None:
        print(f"Beginning naming for {parsedname}...")
        # Vanilla spells need a trailing space to avoid name clashing
        # name clashes are bad: all spells sharing names also share descriptions
        # and sharing with vanilla is ESPECIALLY bad as any items that cast the vanilla named spell seem to always
        # switch to using the modded one instead
        if parsedname in utils.spellnames and (spell.parenteffect not in utils.spellnamesbyeffect or
                                               parsedname not in utils.spellnamesbyeffect[spell.parenteffect]):
            parsedname += " "
            print("Spell seems to be vanilla, add a trailing space")
        parsedname = adjustnameofspell(parsedname, spell)
    elif isspell:
        parsedname = padspellname(parsedname)

    if isspell:
        utils.spellnames.append(parsedname)

    return parsedname

def padspellname(name):
    while name in utils.spellnames:
        name = name + " "
        if len(name) > 35:
            raise NameTooLongException(f"Tried to pad spell name {name} over 35 characters")
    return(name)

def adjustnameofspell(parsedname, spell):
    if len(parsedname) > 35:
        raise NameTooLongException(f"Spell name {parsedname} too long")
    if spell.parenteffect not in utils.spellnamesbyeffect:
        utils.spellnamesbyeffect[spell.parenteffect] = {}
    spelleffectdict = utils.spellnamesbyeffect[spell.parenteffect]
    print(f"There are {len(spelleffectdict)} spells of this effect already...")
    while parsedname in spelleffectdict:
        # Compare current spell to existing names in utils.spellnames[string]
        # Adjust name
        comparespell = spelleffectdict[parsedname]

        if comparespell.researchlevel > spell.researchlevel:
            print(f"existing '{comparespell.name}' is higher research level than this {spell.name}, try moving it")
            attempttomovespellname(comparespell)
            break
        else:
            parsedname = replacecurrentqualifier(parsedname)

        if len(parsedname) > 35:
            raise NameTooLongException(f"Spell name {parsedname} too long")

    parsedname = padspellname(parsedname)
    spelleffectdict[parsedname] = spell
    print("New spell {}{}{}".format('"', parsedname, '"'))
    return parsedname


def attempttomovespellname(spell):
    utils.spellnames.remove(spell.name)
    tmp = replacecurrentqualifier(spell.name)
    if len(tmp) > 35:
        raise NameTooLongException(f"Spell name {tmp} too long")
    spelleffectdict = utils.spellnamesbyeffect[spell.parenteffect]
    print(f"spelleffectdict is {spelleffectdict}")
    del spelleffectdict[spell.name]
    try:
        while tmp in spelleffectdict:
            comparespell = spelleffectdict[tmp]
            if comparespell.researchlevel > spell.researchlevel:
                print(f"'{comparespell.name}' is higher research level than this {spell.name}, try moving it")
                attempttomovespellname(comparespell)
                break
            # should this be checking if research levels are the same and matching names?
            # probably, but doing so would be wonky
            else:
                # Raises NameTooLongException on failure
                tmp = replacecurrentqualifier(tmp)
        tmp = padspellname(tmp)
        if len(tmp) > 35:
            print(f"Error trying to find a new name for {spell.name}: propsed name {tmp} was too long!")
            raise NameTooLongException(f"Proposed name {tmp} too long")
    except NameTooLongException as exc:
        # Put everything back to how it was or weird errors can arise due to fact these were changed
        utils.spellnames.append(spell.name)
        spelleffectdict[spell.name] = spell
        raise exc

    spelleffectdict[tmp] = spell
    spell.name = tmp
    utils.spellnames.append(spell.name)



def replacecurrentqualifier(parsedname):
    # Find current qualifier
    print(f"replace current qualifier for {parsedname}")
    noqualifier = True
    # Search for currently applied qualifier
    for qualifier in utils.spellqualifiers:
        regexp = re.compile("(" + qualifier + ")")
        matches = regexp.match(parsedname)
        if matches:
            # Find next higher qualifier
            # replace current qualifier with next highest
            newqualifier = returnnexthighestqualifier(matches.group())
            parsedname = newqualifier + parsedname[matches.end():]
            noqualifier = False
            break
    if noqualifier:
        parsedname = utils.spellqualifiers[0] + parsedname
    print(f"got {parsedname}")
    if len(parsedname) > 35:
        raise NameTooLongException(f"Qualifier replacement for spell with new name {parsedname} has become too long")
    return parsedname


def returnnexthighestqualifier(qualifier):
    curindex = utils.spellqualifiers.index(qualifier)
    if curindex + 1 >= len(utils.spellqualifiers):
        return "Ultra" + qualifier
    return utils.spellqualifiers[curindex + 1]