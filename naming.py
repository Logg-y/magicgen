import re
import random
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
		#print(self.synonyms)
	def get(self, word):
		if word.lower() not in self.synonyms:
			return word
		return random.choice(self.synonyms[word.lower()]).strip()
		
synonyms = Synonyms()
pluraliser = Pluraliser()

def parsestring(string, plural=False, aoe=0, spelltype=0, titlecase=False, spell=None, isspell=False):
	aoe = aoe % 1000
	#print(f"mode is plural: {plural}")
	if plural:
		string = string.replace("ARTICLE_N", "")
		string = string.replace("ARTICLE", "")
		string = string.replace("PRONOUN_POS", "their")
		string = string.replace("PRONOUN_SUB", "they")
		string = string.replace("PRONOUN", "them")
	else:
		string = string.replace("ARTICLE_N", "an")
		string = string.replace("ARTICLE", "a")
		string = string.replace("PRONOUN_POS", "his")
		string = string.replace("PRONOUN_SUB", "he")
		string = string.replace("PRONOUN", "him")
		
		
	if spelltype & spellstructures.SpellTypes.BUFF:
		if aoe == 0:
			string = string.replace("SUBJECT", "the caster")
			string = string.replace("SIZE", "tiny")
		elif aoe < 5:
			string = string.replace("SUBJECT", "a $few$ soldiers")
			string = string.replace("SIZE", "small")
		elif aoe < 20:
			string = string.replace("SUBJECT", "many soldiers")
			string = string.replace("SIZE", "large")
		elif aoe < 50:
			string = string.replace("SUBJECT", "a large group of soldiers")
			string = string.replace("SIZE", "massive")
		else:
			string = string.replace("SUBJECT", "the entire army")
			string = string.replace("SIZE", "massive")
	elif spelltype & spellstructures.SpellTypes.EVOCATION:
		if aoe == 0:
			string = string.replace("SUBJECT", "one enemy")
			string = string.replace("SIZE", "tiny")
		elif aoe < 5:
			string = string.replace("SUBJECT", "a $few$ enemies")
			string = string.replace("SIZE", "small")
		elif aoe < 20:
			string = string.replace("SUBJECT", "many enemies")
			string = string.replace("SIZE", "large")
		elif aoe < 80:
			string = string.replace("SUBJECT", "a massive group of enemies")
			string = string.replace("SIZE", "massive")
		else:
			string = string.replace("SUBJECT", "the entire battlefield")
			string = string.replace("SIZE", "enormous")
					
	while 1:
		m = re.search("[$](.+?)[$]", string)
		if m is None:
			break
		text = m.groups()[0]
		pluralised = synonyms.get(text)
		#print(string)
		string = re.sub(f"[$]{text}[$]", pluralised, string)
		#print(string)
		
	while 1:
		m = re.search("%(.+?)%", string)
		if m is None:
			break
		text = m.groups()[0]
		if plural:
			pluralised = pluraliser.pluralise(text)
		else:
			pluralised = text
		#print(string)
		#print(text, pluralised)
		string = re.sub(f"%{text}%", pluralised, string)
		#print(string)
		
	# remove double spaces
	string = string.replace("  ", " ")
	string = string.strip()
	string = string[0].upper() + string[1:]
	
	if titlecase:
		words = string.split(" ")
		out = ""
		for pos, word in enumerate(words):
			if word.lower() not in ["a", "in", "from", "and", "of", "for", "the", "after", "before"] or pos == 0:
				out += word[0].upper() + word[1:]
			else:
				out += word.lower()
			out += " "
		string = out.strip()
	
	if isspell:
		while string in utils.spellnames:
			string = string + " "
			if len(string) > 35:
				raise NameTooLongException(f"Spell name {string} too long")
		print("New spell {}{}{}".format('"', string, '"'))
		utils.spellnames.append(string)
	
	return(string)