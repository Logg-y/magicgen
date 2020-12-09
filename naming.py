import random
import re

import spellstructures
from spellstructures import utils


class NameTooLongException(Exception):
    pass


class Pluraliser(object):
    def __init__(self):
        self.exceptions = {}
        with open("./data/naming/plurals.txt") as f:
            for line in f:
                if line.strip() == "": continue
                c = line.split("\t")
                self.exceptions[c[0]] = c[1].strip()

    def pluralise(self, word):
        if word.lower() in self.exceptions:
            return self.exceptions[word.lower()].strip()
        else:
            if word.lower()[-1] == "y":
                word = word[:-1] + "ies"
                return word
            if word.lower()[-1] != "s":
                word = word + "s"
                return word
            return word


class Synonyms(object):
    def __init__(self):
        self.synonyms = {}
        with open("./data/naming/synonyms.txt") as f:
            for line in f:
                if line.strip() == "": continue
                c = line.split("\t")
                if c[0] not in self.synonyms:
                    self.synonyms[c[0]] = []
                self.synonyms[c[0]].append(c[1].strip())

    # print(self.synonyms)
    def get(self, word):
        if word.lower() not in self.synonyms:
            return word
        return random.choice(self.synonyms[word.lower()]).strip()


synonyms = Synonyms()
pluraliser = Pluraliser()


def parsestring(string, plural=False, aoe=0, spelltype=0, titlecase=False, spell=None, isspell=False):
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

    if spelltype & spellstructures.SpellTypes.BUFF:
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
    elif spelltype & spellstructures.SpellTypes.EVOCATION:
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

    if isspell:
        parsedname = adjustnameofspellname(parsedname, spell)

    return parsedname


def adjustnameofspellname(parsedname, spell):
    if len(parsedname) > 35:
        raise NameTooLongException(f"Spell name {parsedname} too long")
    while parsedname in utils.spellnames:
        # Compare current spell to existing names in utils.spellnames[string]
        # Adjust name
        comparespell = utils.spellnames[parsedname]

        if comparespell is None:
            parsedname = parsedname + " "
        else:
            if comparespell.researchlevel > spell.researchlevel:
                attempttomovespellname(comparespell)
                break
            else:
                parsedname = replacecurrentqualifier(parsedname)

        if len(parsedname) > 35:
            raise NameTooLongException(f"Spell name {parsedname} too long")
    print("New spell {}{}{}".format('"', parsedname, '"'))
    utils.spellnames[parsedname] = spell
    return parsedname


def attempttomovespellname(spell):
    tmp = replacecurrentqualifier(spell.name)
    if len(tmp) > 35:
        raise NameTooLongException(f"Spell name {tmp} too long")
    while tmp in utils.spellnames:
        comparespell = utils.spellnames[tmp]
        if comparespell.researchlevel > spell.researchlevel:
            attempttomovespellname(comparespell)
            break
        else:
            tmp = replacecurrentqualifier(tmp)

    if len(tmp) > 35:
        raise NameTooLongException(f"Spell name {tmp} too long")
    spell.name = tmp
    utils.spellnames[spell.name] = spell


def replacecurrentqualifier(parsedname):
    # Find current qualifier
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
    return parsedname


def returnnexthighestqualifier(qualifier):
    curindex = utils.spellqualifiers.index(qualifier)
    if curindex + 1 >= len(utils.spellqualifiers):
        return "Ultra" + qualifier
    return utils.spellqualifiers[curindex + 1]