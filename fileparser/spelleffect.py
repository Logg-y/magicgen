import os
import re

from Entities.SpellEffect import SpellEffect
from Entities.namecond import NameCond
from Exceptions.ParseError import ParseError
from Services import utils

simple_params_int = ["effect", "damage", "spec", "schools", "paths", "spelltype", "aoe", "power", "range", "precision", "nreff", "pathlevel", "fatiguecost", "flightspr", "explspr", "paths", "secondarypaths","maxpower","sound","maxbounces","casttime", "provrange", "secondarypathchance", "nogeodst", "onlygeodst", "ainocast", "onlyfriendlydst", "nolandtrace", "onlygeosrc", "skipflightspr", "skipexplspr", "chassisvalue", "unique", "alwaysgenerate", "donotsetextraspellpath", "aispellmod", "banishment", "holyword", "smitedemon", "smite", "noadditionalnextspells", "basescale", "secondaryeffectskipchance", "permanentslotusage", "friendlyench", "hiddenench", "badaispell"]
simple_params_str = ["nextspell", "details","copyspell", "extraspell", "eventset", "newunit"]
simple_params_float = ["scalecost", "scalerate", "pathperresearch", "scalefatigueexponent", "scalefatiguemult", "skipchance"]


def readEffectFile(fp):
	"Read one file and return all the spell effects within."
	try:
		lineno = None
		out = {}
		curreff = None
		with open(fp, "r") as f:
			for lineno, line in enumerate(f):
				line = line.strip()
				if line == "": continue
				if line.startswith("--"): continue

				if line.startswith("#neweffect"):
					if curreff is not None:
						raise ParseError(
							f"{fp} line {lineno}: Unexpected #neweffect (still parsing previous effect)")
					m = re.match("#neweffect\W+\"(.*)\"\W*$", line)
					if m is None:
						raise ParseError(f"{fp} line {lineno}: Expected an effect name, none was found")
					curreff = SpellEffect(fp)
					curreff.name = m.groups()[0]
					currPriority = 0

				else:
					if curreff is None:
						raise ParseError(f"{fp} line {lineno}: Expected a #neweffect line")

					sorted = False

					# Params to simply copy
					for simple in simple_params_int:
						m = re.match(f"#{simple}\\W+?([-0-9]*)\\W*$", line)
						if m is not None:
							pval = int(m.groups()[0])
							setattr(curreff, simple, pval)
							sorted = True
							break

					if sorted: continue

					for simple in simple_params_str:
						m = re.match(f"#{simple}" + "\\W+?\"(.*)\"\\W*", line)
						if m is not None:
							pval = m.groups()[0]
							setattr(curreff, simple, pval)
							sorted = True
							continue

					if sorted: continue

					for simple in simple_params_float:
						m = re.match(f"#{simple}\W+?([-.0-9]*)\W*$", line)
						if m is not None:
							pval = float(m.groups()[0])
							setattr(curreff, simple, pval)
							sorted = True
							continue

					if sorted: continue

					if line.startswith("#priority"):
						m = re.match("#priority\\W+?([-0-9]*)\\W*$", line)
						if m is not None:
							currPriority = int(m.groups()[0])
							continue

					if line.startswith("#namecond"):
						m = re.match(
							'#namecond2\\W+([0-9]*)[ \t]([<>=!]+)\\W+(.+)[ \t]+([<>&=!]+)\\W*([0-9]*)\\W+([0-9]*)\\W+"(.*)"',
							line)
						if m is not None:
							cond = NameCond()
							cond.val2 = m.groups()[0]
							cond.op2 = m.groups()[1]
							cond.param = m.groups()[2]
							cond.op = m.groups()[3]
							cond.val = m.groups()[4]
							cond.path = int(m.groups()[5])
							cond.text = m.groups()[6]

							if cond.path not in curreff.nameconds:
								curreff.nameconds[cond.path] = {}
							if currPriority not in curreff.nameconds[cond.path]:
								curreff.nameconds[cond.path][currPriority] = []
							curreff.nameconds[cond.path][currPriority].append(cond)
							continue

						m = re.match('#namecond\\W+(.+)[ \t]+([<>=&!]+)\\W*([0-9]*)\\W+([0-9]*)\\W+"(.*)"', line)
						if m is None:
							raise ParseError(f"{fp} line {lineno}: bad #namecond or #namecond2")
						cond = NameCond()
						cond.param = m.groups()[0]
						cond.op = m.groups()[1]
						cond.val = m.groups()[2]
						cond.path = int(m.groups()[3])
						cond.text = m.groups()[4]

						if cond.path not in curreff.nameconds:
							curreff.nameconds[cond.path] = {}
						if currPriority not in curreff.nameconds[cond.path]:
							curreff.nameconds[cond.path][currPriority] = []
						curreff.nameconds[cond.path][currPriority].append(cond)
						continue

					if line.startswith("#descrcond"):
						m = re.match(
							'#descrcond2\\W+([0-9]*)[ \t]([<>=!]+)\\W+(.+)[ \t]+([<>&=!]+)\\W*([0-9]*)\\W+([0-9]*)\\W+"(.*)"',
							line)
						if m is not None:
							cond = NameCond()
							cond.val2 = m.groups()[0]
							cond.op2 = m.groups()[1]
							cond.param = m.groups()[2]
							cond.op = m.groups()[3]
							cond.val = m.groups()[4]
							cond.path = int(m.groups()[5])
							cond.text = m.groups()[6]
							if cond.path not in curreff.descrconds:
								curreff.descrconds[cond.path] = {}
							if currPriority not in curreff.descrconds[cond.path]:
								curreff.descrconds[cond.path][currPriority] = []
							curreff.descrconds[cond.path][currPriority].append(cond)
							continue

						m = re.match('#descrcond\\W+(.+)[ \t]+([<>&=!]+)\\W*([0-9]*)\\W+([0-9]*)\\W+"(.*)"', line)
						if m is None:
							raise ParseError(f"{fp} line {lineno}: bad #descrcond")
						cond = NameCond()
						cond.param = m.groups()[0]
						cond.op = m.groups()[1]
						cond.val = m.groups()[2]
						cond.path = int(m.groups()[3])
						cond.text = m.groups()[4]
						if cond.path not in curreff.descrconds:
							curreff.descrconds[cond.path] = {}
						if currPriority not in curreff.descrconds[cond.path]:
							curreff.descrconds[cond.path][currPriority] = []
						curreff.descrconds[cond.path][currPriority].append(cond)
						continue

					if line.startswith("#descr"):
						m = re.match('#descr\\W+([0-9]*)\\W+"(.*)"', line)
						if m is None:
							raise ParseError(f"{fp} line {lineno}: bad #descr")
						curreff.descriptions[int(m.groups()[0])] = m.groups()[1]
						continue

					if line.startswith("#pathskipchance"):
						m = re.match('#pathskipchance\\W+([0-9]*)\\W+([0-9]*)', line)
						if m is None:
							raise ParseError(f"{fp} line {lineno}: bad #pathskipchance")
						path = int(m.groups()[0])
						skipchance = int(m.groups()[1])
						curreff.pathskipchances[path] = skipchance
						continue

					if line.startswith("#name"):
						m = re.match('#name\\W+([0-9]*)\\W+"(.*)"', line)
						if m is None:
							raise ParseError(f"{fp} line {lineno}: bad #name")
						path = int(m.groups()[0])
						if path not in curreff.names:
							curreff.names[path] = []
						curreff.names[path].append(m.groups()[1])
						continue

					if line.startswith("#end"):
						out[curreff.name] = curreff
						curreff = None
						continue

					raise ParseError(f"{fp} line {lineno}: Unrecognised content: {line}")
		return out
	except:
		if lineno is not None:
			raise ParseError(f"Failed to read {fp}, failed at line {lineno}")
		else:
			raise ParseError(f"Failed to read {fp}, undetermined line")


def readEffectsFromDir(dir):
	out = utils.spelleffects
	new = []
	for f in os.listdir(dir):
		if f.endswith(".txt"):
			c = readEffectFile(os.path.join(dir, f))
			for key in c:
				if key in out:
					raise ParseError(f"Spell named {key} already exists and was redefined in {f}")
				out[key] = c[key]
				if c[key].spelltype == -1:
					raise ParseError(f"{f}: Spell Effect {key} was given no spell type")
				new.append(key)
	o = {}
	for key in new:
		o[key] = out[key]
	return o
