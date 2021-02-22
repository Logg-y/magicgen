import random


class Synonyms(object):
    def __init__(self):
        self.synonyms = {}
        with open("data/naming/synonyms.txt") as f:
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