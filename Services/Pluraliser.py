class Pluraliser(object):
    def __init__(self):
        self.exceptions = {}
        with open("data/naming/plurals.txt") as f:
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