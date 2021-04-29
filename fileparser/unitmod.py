import os
import re
from typing import Union

from Entities.UnitMod import UnitMod
from Entities.namecond import NameCond
from Exceptions.ParseError import ParseError
from Services.utils import unitmods

secondary_params_int = ["wpn1", "wpn2", "wpn3", "wpn4", "wpn5", "wpn6", "wpn7", "armor1", "armor2", "armor3", "armor4", "rt", "reclimit", "basecost", "rcost", "size", "ressize", "hp", "prot", "mr", "mor", "str", "att", "def", "prec", "enc", "mapmove", "ap", "ambidextrous", "mounted", "reinvigoration", "leader", "undeadleader", "magicleader", "startage", "maxage", "hand", "head", "body", "foot", "misc", "crownonly", "pathcost", "startdom", "bonusspells", "F", "A", "W", "E", "S", "D", "N", "B", "H", "rand1", "nbr1", "link1", "mask1", "rand2", "nbr2", "link2", "mask2", "rand3", "nbr3", "link3", "mask3", "rand4", "nbr4", "link4", "mask4", "holy", "inquisitor", "mind", "inanimate", "undead", "demon", "magicbeing", "stonebeing", "animal", "coldblood", "female", "forestsurvival", "mountainsurvival", "wastesurvival", "swampsurvival", "cavesurvival", "aquatic", "amphibian", "pooramphibian", "float", "flying", "stormimmune", "teleport", "immobile", "noriverpass", "sailingshipsize", "sailingmaxunitsize", "stealthy", "illusion", "spy", "assassin", "patience", "seduce", "succubus", "corrupt", "heal", "immortal", "domimmortal", "reinc", "noheal", "neednoteat", "homesick", "undisciplined", "formationfighter", "slave", "standard", "inspirational", "taskmaster", "beastmaster", "bodyguard", "waterbreathing", "iceprot", "invulnerable", "slashres", "bluntres", "pierceres", "shockres", "fireres", "coldres", "poisonres", "voidsanity", "darkvision", "blind", "animalawe", "awe", "haltheretic", "fear", "berserk", "cold", "heat", "fireshield", "banefireshield", "damagerev", "poisoncloud", "diseasecloud", "slimer", "mindslime", "reform", "regeneration", "reanimator", "poisonarmor", "petrify", "eyeloss", "ethereal", "ethtrue", "deathcurse", "trample", "trampswallow", "stormpower", "firepower", "coldpower", "darkpower", "chaospower", "magicpower", "winterpower", "springpower", "summerpower", "fallpower", "forgebonus", "fixforgebonus", "mastersmith", "resources", "autohealer", "autodishealer", "alch", "nobadevents", "event", "insane", "shatteredsoul", "leper", "taxcollector", "gem", "gemprod", "chaosrec", "pillagebonus", "patrolbonus", "castledef", "siegebonus", "incprovdef", "supplybonus", "incunrest", "popkill", "researchbonus", "drainimmune", "inspiringres", "douse", "adeptsacr", "crossbreeder", "makepearls", "pathboost", "allrange", "voidsum", "heretic", "elegist", "shapechange", "firstshape", "secondshape", "secondtmpshape", "landshape", "watershape", "forestshape", "plainshape", "xpshape", "unique", "fixedname", "special", "nametype", "summon", "n_summon", "autosum", "n_autosum", "batstartsum1", "batstartsum2", "domsummon", "domsummon20", "raredomsummon", "bloodvengeance", "bringeroffortune", "realm1", "realm2", "realm3", "batstartsum3", "batstartsum4", "batstartsum5", "batstartsum1d6", "batstartsum2d6", "batstartsum3d6", "batstartsum4d6", "batstartsum5d6", "batstartsum6d6", "turmoilsummon", "coldsummon", "scalewalls", "deathfire", "uwregen", "shrinkhp", "growhp", "transformation", "startingaff", "fixedresearch", "divineins", "lamialord", "preanimator", "dreanimator", "mummify", "onebattlespell", "fireattuned", "airattuned", "waterattuned", "earthattuned", "astralattuned", "deathattuned", "natureattuned", "bloodattuned", "magicboostF", "magicboostA", "magicboostW", "magicboostE", "magicboostS", "magicboostD", "magicboostN", "magicboostALL", "eyes", "heatrec", "coldrec", "spreadchaos", "spreaddeath", "corpseeater", "poisonskin", "bug", "uwbug", "spreadorder", "spreadgrowth", "startitem", "spreaddom", "battlesum5", "acidshield", "drake", "prophetshape", "horror", "enchrebate50p", "latehero", "sailsize", "uwdamage", "landdamage", "rpcost", "buffer", "rand5", "nbr5", "link5", "mask5", "rand6", "nbr6", "link6", "mask6", "mummification", "diseaseres", "raiseonkill", "raiseshape", "sendlesserhorrormult", "xploss", "theftofthesunawe", "incorporate", "hpoverslow", "blessbers", "dragonlord", "curseattacker", "uwheat", "slothresearch", "horrordeserter", "mindvessel", "elementrange", "sorceryrange", "older", "disbelieve", "firerange", "astralrange", "landreinvigoration", "naturerange", "beartattoo", "horsetattoo", "reincarnation", "wolftattoo", "boartattoo", "sleepaura", "snaketattoo", "appetite", "astralfetters", "foreignmagicboost", "templetrainer", "infernoret", "kokytosret", "addrandomage", "unsurr", "combatcaster", "homeshape", "speciallook", "aisinglerec", "nowish", "bugreform", "mason", "onisummon", "sunawe", "spiritsight", "defenceorganiser", "invisible", "startaff", "ivylord", "spellsinger", "magicstudy", "triplegod", "triplegodmag", "unify", "triple3mon", "yearturn", "fortkill", "thronekill", "digest", "indepmove", "unteleportable", "reanimpriest", "stunimmunity", "entangle", "alchemy", "woundfend", "singlebattle", "falsearmy", "summon5", "ainorec", "researchwithoutmagic", "slaver", "autocompete", "deathparalyze", "adventurers", "cleanshape", "reqlab", "reqtemple", "horrormarked", "changetargetgenderforseductionandseductionimmune", "corpseconstruct", "guardianspiritmodifier", "isashah", "iceforging", "isayazad", "isadaeva", "blessfly", "plant", "clockworklord", "commaster", "comslave", "minsizeleader", "snowmove", "swimming", "stupid", "skirmisher", "ironvul", "heathensummon", "unseen", "illusionary", "reformtime", "immortalrespawn", "nomovepen", "wolf", "dungeon", "graphicsize", "twiceborn", "aboleth", "tmpastralgems", "localsun", "tmpfiregems", "defiler", "mountedbeserk", "lanceok", "startheroab", "minprison", "uwfireshield", "saltvul", "landenc", "plaguedoctor", "curseluckshield", "pathboostuw", "pathboostland", "noarmormapmovepenalty", "farthronekill", "hpoverflow", "indepstay", "polyimmune", "horrormark", "deathdisease", "allret", "percentpathreduction", "aciddigest", "beckon", "slaverbonus", "carcasscollector", "mindcollar", "labpromotion", "mountainrec", "indepspells", "enchrebate50", "summon1", "randomspell", "deathpower", "deathrec", "norange", "insanify", "reanimator", "defector", "nohof", "batstartsum1d3", "enchrebate10"]
secondary_params_int += ["reqmage", "landok", "uwok"]
secondary_params_str = ["descr", "weaponmod", "nameprefix"]
secondary_params_float = []


def readUnitMod(fp):
	"Read one file and return all the spell modifiers within."
	out = {}
	curreff: Union[UnitMod, None] = None
	with open(fp, "r") as f:
		for lineno, line in enumerate(f):
			line = line.strip()
			if line == "": continue
			if line.startswith("--"): continue

			if line.startswith("#newunitmod"):
				if curreff is not None:
					raise ParseError(f"{fp} line {lineno}: Unexpected #newunitmod (still parsing previous effect)")
				m = re.match("#newunitmod\W+\"(.*)\"\W*$", line)
				if m is None:
					raise ParseError(f"{fp} line {lineno}: Expected an effect name, none was found")
				curreff = UnitMod()
				curreff.name = m.groups()[0]

			else:
				if curreff is None:
					raise ParseError(f"{fp} line {lineno}: Expected a #newunitmod line")

				sorted = False

				# Params to simply copy
				for simple in secondary_params_int:
					m = re.match(f"#{simple}\\W+?([-0-9]*)\\W*$", line)
					if m is not None:
						pval = int(m.groups()[0])
						setattr(curreff, simple, pval)
						sorted = True
						break

				if sorted: continue

				for simple in secondary_params_str:
					m = re.match(f"#{simple}" + "\\W+?\"(.*)\"\\W*", line)
					if m is not None:
						pval = m.groups()[0]
						setattr(curreff, simple, pval)
						sorted = True
						continue

				if sorted: continue

				for simple in secondary_params_float:
					m = re.match(f"#{simple}\W+?([-.0-9]*)\W*$", line)
					if m is not None:
						pval = float(m.groups()[0])
						setattr(curreff, simple, pval)
						sorted = True
						continue

				if sorted: continue

				if line.startswith("#descrcond"):
					m = re.match('#descrcond2\\W+([0-9]*)[ \t]([<>=!]+)\\W+(.+)[ \t]+([<>=!]+)\\W*([0-9]*)\\W+"(.*)"', line)
					if m is not None:
						cond: NameCond = NameCond()
						cond.val2 = m.groups()[0]
						cond.op2 = m.groups()[1]
						cond.param = m.groups()[2]
						cond.op = m.groups()[3]
						cond.val = m.groups()[4]
						cond.text = m.groups()[5]
						curreff.descrconds.append(cond)
						continue

					m = re.match('#descrcond\\W+(.+)[ \t]+([<>&=!]+)\\W*([0-9]*)\\W+"(.*)"', line)
					if m is None:
						raise ParseError(f"{fp} line {lineno}: bad #descrcond")
					cond = NameCond()
					cond.param = m.groups()[0]
					cond.op = m.groups()[1]
					cond.val = m.groups()[2]
					cond.text = m.groups()[3]
					curreff.descrconds.append(cond)
					continue

				if line.startswith("#descr"):
					m = re.match('#descr\\W+"(.*)"', line)
					if m is None:
						raise ParseError(f"{fp} line {lineno}: bad #descr")
					curreff.descrs.append(m.groups()[0])
					continue

				if line.startswith("#req"):
					m = re.match('#req2\\W+([0-9-]*)[ \t]([<>=!]+)\\W+(.+)[ \t]+([<>=!]+)\\W*([0-9-]+)', line)
					if m is not None:
						cond = NameCond()
						cond.val2 = m.groups()[0]
						cond.op2 = m.groups()[1]
						cond.param = m.groups()[2]
						cond.op = m.groups()[3]
						cond.val = m.groups()[4]
						cond.text = ""
						curreff.reqs.append(cond)
						continue

					m = re.match('#req\\W+(.+)[ \t]+([<>&=!]+)\\W*?([0-9-]+)', line)
					if m is None:
						raise ParseError(f"{fp} line {lineno}: bad #req")
					cond = NameCond()
					cond.param = m.groups()[0]
					cond.op = m.groups()[1]
					cond.val = m.groups()[2]
					cond.text = ""
					curreff.reqs.append(cond)
					continue

				if line.startswith("#mult"):
					m = re.match('#mult\\W+(.*?)\\W*?([-0-9-.]+)', line)
					if m is not None:
						param = m.groups()[0]
						val = float(m.groups()[1])
						curreff.multcommands.append([param, val])
						continue
					raise ParseError(f"{fp} line {lineno}: bad #mult")

				if line.startswith("#setstr"):
					m = re.match('#setstr\\W+(.*?)\\W*?"(.*)"', line)
					if m is None:
						raise ParseError(f"{fp} line {lineno}: bad #setstr")
					param = m.groups()[0]
					val = m.groups()[1]
					curreff.setcommands.append([param, val])
					continue

				if line.startswith("#set"):
					m = re.match('#set\\W+(.*?)\\W*?([-0-9-]+)', line)
					if m is not None:
						param = m.groups()[0]
						val = int(m.groups()[1])
						curreff.setcommands.append([param, val])
						continue
					raise ParseError(f"{fp} line {lineno}: bad #set")



				if line.startswith("#end"):
					out[curreff.name] = curreff
					curreff = None
					continue

				raise ParseError(f"{fp} line {lineno}: Unrecognised content: {line}")
	return out


def readUnitModsFromDir(dir):
	out = unitmods
	for f in os.listdir(dir):
		if f.endswith(".txt"):
			c = readUnitMod(os.path.join(dir, f))
			for key in c:
				if key in out:
					raise ParseError(f"UnitMod named {key} already exists and was redefined in {f}")
				out[key] = c[key]
