# Basics:

The prompts should be fairly self explanatory, but for completeness (and the fact I may yet add more here):

Spells per level: number of spells to make per research level. Sometimes you get more than this because a few effects generate more than one spell, for instance a communion master spell will immediately generate a communion slave spell at the same research level and pathing.
Construction factor: a multiplier to the number of spells per level used for spells going into construction. This is to replicate the fact that vanilla construction has significantly fewer spells than other schools.
National spells: the number of national spells to generate per nation. These are targeted at the paths that each nation gets on its mages.
Modname: The name for the .dm file. It is suggested to pick something sensible like the game name for this.
Modlist: a list of filepaths, separated by commas. This ONLY scans for new nations and tries to guess their mages, and is used solely to add national spells.

Note that Dominions has a limit on the number of modded spells that can be reached quite easily if the number of national spells is turned up too high. The program will complain if this happens.

# Datafile Tutorial

This will assume you have a passing knowledge of how Dominions modding (especially that for spells) works. Even if you do, you might want to refer back to the mod manual sometimes. If you don't, you might do well to understand how Dominions spells are put together and what all the important properties do before messing with a program which is designed to churn lots of them out.

This is intended to be a relatively quick tour through topics that may not be obvious at a first glance. It is an attempt to give a reader an indication of how the whole thing fits together, without getting too caught up on the finer details. The need to actually write anything from scratch should be unnecessary for most - simply copying and editing an existing similar effect should suffice for most applications. Copying is very much encouraged, and this quick guide will assume a certain level of copying and editing files that already exist.

## Spell Effects

MagicGen runs off "spell effects", which are essentially templates for spell effects. One spell effect can be used to create spells across a range of spell levels (or just 1 if you so wanted), and describes how all aspects of the spell should change as research level is increased. The syntax used in these (and all other MagicGen structures) is deliberately kept similar to that of Illwinter's .dm format.

A spell is made up of a spell effect, a modifier (which alters the "delivery" of a spell, such as making it touch ranged, higher research but easier to cast, into a cloud effect...), and a secondary effect (such as a fireball that petrifies people it hits). These other things are discussed in further detail later, but being aware that they exist is useful in understanding several aspects of spells.

### A broken down example spell effect (Falling Fires)
```

-- All effects need a unique name
#neweffect "Fire Evo Instant"
-- These are simply set as you would if modding a spell in a typical .dm
#effect 2
#damage 2016
#spec 96
#aoe 1
#precision 1
#range 30
#fatiguecost 20
#explspr 10011
#sound 123
-- "power" here is used to mean "research level". In this case, the spell effect can generate at research level 2-14 inclusive
#power 2
#maxpower 14
-- The path level used to cast the spell
#pathlevel 2

-- Paths that the spell can generate for. Unlike Illwinter's system, these are bitflags: 129 is made up of 1 (fire) and 128 (blood).
-- The value of any given constant is simply 2^(Illwinter's path value), so:
-- F=1, A=2, W=4, E=8, S=16, D=32, N=64, B=128
#paths 129
-- Paths that the spell can have as a secondary (cross) path. So Blood/Fire is a possible combination
#secondarypaths 1

-- Names and descriptions for the spell. The number indicates the path it is for, hence the need for both 1 (fire) and 128 (blood).
-- The symbols and words in capitals are variable and are discussed later.
#name 1 "NAMEPREFIX Falling %$fire$%"
#name 128 "NAMEPREFIX $infernal$ %$fire$%"
#descr 1 "Flames fall onto a SIZE area with the potential to badly burn SUBJECT."
#descr 128 "$BLOOD_INTRO$, the caster directs infernal flames upon a group of his enemies. This may badly burn SUBJECT."

-- This is a bit field that lists flags for the spells. In this case: evo-like, battlefield allowed, scale aoe with research level
#spelltype 42
-- The rate at which spells are scaled, discussed later
#scalerate 1
-- #scalecost 0.3
-- The research schools this spell can go in. This is similar to the paths in that it is a bitflag with values of 2^(Illwinter's constants). These are:
-- Conj=1, Alt=2, Evo=4, Constr=8, Ench=16, Thaum=32, Blood=64
#schools 4

-- Priority 1 means that any of these will be used in preference to the names and descriptions above if their conditions are met.
-- This is used to make "touch" range versions of this spell (which is implemented as a Modifier) get a different name and description to the normal ranged version
#priority 1
#namecond range < 10 1 "NAMEPREFIX Burst of Flames"
#namecond range < 10 128 "NAMEPREFIX Burst of Infernal Flames"
#descrcond range < 10 1 "The caster causes searing flames to erupt around him, harming anyone nearby."
#descrcond range < 10 128 "$BLOOD_INTRO$, the caster causes the searing flames of Inferno to erupt around him, harming anyone nearby."
#end
```

### Scaling

This is quite a mathematical topic which isn't very easy to explain, so I made a program that allows you to mess with the various parameters and see what they would produce, allowing more careful control of spell scaling than simply picking numbers and hoping for the best. The following explanation is intended as a supplement to this, without it these values would be very difficult for an interested reader to follow. Importantly, the scaling utility uses the actual generation code, which means that other features are displayed - such as how it designates dynamic scaling.

It was intended that playing around with the tool should go with this section.

There are various parts of spells that scale. These can be split into fatigue, path level, and other attributes (defined as #spelltype flags, these are currently damage, number of effects, aoe, effect number, maxbounces). Other attributes scale quadratically (the amount added per research level over the base goes up at a graph of x^2 would) with #scalerate determining the steepness of the curve. This is used to calculate a final "scaling amount" which is added to the appropriate attribute(s).

In the case of the Falling Fires spell above, generating at research 5 has a research difference of 3 (5-2 = 3). The total scale amount with a #scalerate of 1 = 6. Therefore, this scale amount of 6 is added to the effect's base AoE of 1, meaning at research 5 it has a final AoE of 1+6 = 7. The actual calculation of scale amount is below in the more formal documentation, but the details of it are not important at this stage. What is important is to realise that it grows at an increasing rate: the falling fires spell (at the time of writing) AoE as research levels increase becomes 1, 2, 4, 7, 16 (here it jumps to costing a gem), 22, 29, 37, 44, 57, 67, 79...

Path level is flat, and is governed by #pathperresearch. The default value for this (which is not overwritten) in falling fires is 0.66. As the name hopefully implies, each extra research level adds this to the path level, and the result is rounded down at the end.

Fatigue is more complex than the others and hinges on a variety of factors. It will seemingly increase on its own - each extra research level adds 10 fatigue, and (scale amount^#scalefatigueexponent) is then added to the cost. #scalefatigueexponent can be negative, which will instead SUBTRACT the result from the fatigue cost (as opposed to the usual mathematical meaning of negative exponents). #scalefatiguemult (not used in falling fires) can be thought of as "fatigue cost per additional effect".

In an attempt to make the jump to gem costing spells better/make more sense, scaling parameters for non-blood combat spells that are not nextspells that cost a gem generate as if they were 1 research level higher, but only if the base effect did not cost a gem. This increase in scale amount is NOT used in the fatigue calculations.

Ultimately, understanding all these factors is quite difficult. This is why the scaling utility was made - in an attempt to make understanding and selecting values easier, by making an instant method of seeing all the non-modified results of setting them.

(After quite a lot of use this utility will start refusing to create any spells. This is because of the way it sits on top of the normal generation code, causing issues with naming and ID usage that cause it to break after a while. Simply restart it when this happens.)


### Other attributes of spell effects

There are many other attributes of spell effects. As this is an attempt to be a guide through how things work, it will not cover most of these. Refer to the documentation component for a complete list.

One important attribute is #nextspell. This expects the name of another Spell Effect, and will cause spells generated with the first spell effect to be assigned a nextspell of the given spell effect, generated with the same path requirements and modifiers. This allows chaining effects together such as a fireball into an area heat fatigue effect, and many more combinations.

Another important attribute is #skipchance. This can be used to make spell effects rarer, and is used extensively. A notable use of this is that most summoning spells have a very high skipchance, so that the huge number of ritual and battlesummon spell effects does not swamp other effects such as conjuration globals.

### Modifiers

All spell effects must generate with a modifier, which is intended to alter parameters affecting the delivery of the spell. This could be casting time, fatigue cost, path levels, research level modifiers, spec values, and more. The aim when setting these up is to make them unobtrusive: spell effects should not have to work around possible modifiers. The only reference to them is typically altered names and descriptions if they are being turned into clouds, made into touch range, or similar properties.

As with spell effects, refer to the later section of this document for a list of allowed commands.


#### Example Modifier

```
#newmodifier "Touch Range Damage"

-- can apply to evocation only
#spelltype 2

-- increases effective research level by 1
#power 1
-- reduces one of the fatigue scaling parameters
#scalefatigueexponent -0.5
-- multiplies the whole spell's fatigue, at the end, by 0.3
#mult fatiguecost 0.3
-- causes path levels to progress at a lesser rate
#pathperresearch -0.23
-- sets range to 3, for a touch spell
#set range 3
-- set precision to 100, so it won't miss
#set precision 100
-- flat -75% cast time
#casttime -75
-- require a nonscaling range (ignores scaling from 1000+ values) between 10 and 100
#req2 10 <= nonscalingrange <= 100
-- not ritual
#req spelltype !& 4
-- apply to damage only
#req effect == 2
-- do not allow x% battlefield effects
#nobattlefield
-- add to aispellmod, to make the AI like to cast this
#aispellmod 200

-- chance to be skipped, otherwise touch spells would be very common
#skipchance 85

-- must not affect enemies only
#req spec !& 262144
-- add enemies only spec
#spec 262144

-- adds to spell's description
#descr "Despite its lethality, the caster is able to shield himself and his allies from its short range effects."

#end
```

### Secondary effects

Much like modifiers, all spells must come with exactly one secondary effect (including the Do Nothing secondary effect). For in battle spells this is typically some kind of nextspell, for instance a mind burn spell that sets its victims on fire. For summons, this is the myriad of modifications that can go on them. I am hopeful that readers can understand these upon reading them in their respective files.

### Network of Objects

After the above explanation, I hope that a more thorough "how does everything fit together" can now be written, along with introducing yet more file types. Listed here are examples of spell effects which perform the listed functions for ease of locating and copying existing examples.

```
Spell: output, always generated from the combination of SpellEffect + SecondaryEffect + Modifier

SpellEffect:
	Can call another SpellEffects for nextspells (numerous, eg: fireball)
	Can call one EventSet (provides access to writing event code, and pulling together montags)
		Can assemble montags of creature + UnitMod combos (eg: portal globals)
		Can call one MagicSite (provides access to adding new magic sites) (eg: adventure site spell)
			Can also assemble their own montags of creature + UnitMod combos (eg: wall defender spell)
		Supports modular events, allowing a mix and match system for event components (this is complicated, see offensive globals)
	Can call one NewUnit (provides definitions for new unit types for summon spells, such as nonsacred void critters)
	
SecondaryEffect:
	Can call UnitMods (unit modifiers, for editing the summoned creature)
		Can call WeaponMods (weapon modifiers, for editing the weapons of the summoned creature)	
```

The above will probably sound daunting, but most of these substructures are only required to do certain very specific things:

 * If a ritual needs events, it needs an EventSet.
 * If events need to make a new magic site, they need a MagicSite.
 * If a summoning spell is for a unit not in the base game, it needs a NewUnit.
 * If a secondary effect is going to edit a summoned creature, it needs a UnitMod, which in turn may need a WeaponMod if it edits or needs to check for certain weapon types.

An exception to this are random creature pools, which are more involved and further explanation is warranted.

### Random Creature Pools

Random creature pools are available through MagicSites and EventSets only. Counterintuitively, a ritual that transforms its caster into a random creature therefore requires an EventSet, even though no event code is required.

\#selectunitmod defines a "Selector UnitMod" for the creature pool. That is to say, any creature must be ALLOWED to have this applied to it in order to be allowed into the pool. This UnitMod is never actually applied to the units in the pool, ONLY used to decide if they are allowed in or not. Weapon requirements (for instance, ensuring that each creature in the pool has a ranged weapon before they get used as a fort wall defender) can also be checked with a linked WeaponMod.

\#allowedunitmod can be used multiple times, to add the UnitMods that can actually be applied to the units in the pool. For instance, a global that sends assassins after commanders does not want summon secondary effects such as Bringer of Fortune or Inspirational, because those would be pointless. Due to the large amount of reundancy here with very long lists of unitmods that needed to be updated in many different places, #unitmodlist was made to keep lists of modifiers for common purposes.

Creatures themselves are lifted from SpellEffects. #effectnumberforunits (can be used multiple times) picks which effect numbers are allowed to be considered for this. The strength of creatures is determined with #mincreaturepower and #maxcreaturepower. Each research level over the minimum increases these by 1, as an example:

A spell with #power 4 calling an EventSet with #mincreaturepower 0, generating at research 4, would pull research 0 spell effect creatures. It would however pull research level 2 spell effect creatures at research 6, and so on.

	

# The boring documentation list

Ideally, once understanding the above, readers can probably copy what is already in existence and just look things up here if confused about something.

END OF LINE COMMENTS ARE NOT SUPPORTED and may cause weirdness.

## Spell effects

\#neweffect "Name" should be used to start these.

### Simple copied over parameters

Refer to the modmanual for details on these, unles otherwise noted.

\#effect
\#damage
\#aoe
\#spec
\#range
\#precision
\#fatiguecost
\#nreff
\#flightspr
\#explspr
\#details
\#maxbounces
\#sound
\#casttime
\#provrange
\#nogeodst
\#onlygeodst
\#ainocast
\#onlyfriendlydst
\#nolandtrace
\#onlygeosrc
\#aispellmod
\#hiddenench
\#friendlyench
\#details
 * As the usual, additionally the following strings are replaced in spell details:
	* EFFECTIVENREFF: the base number of effects for the spell cast at the base path level
	* NREFFESCALING: the number of effects the spell gains for each extra path level
	* NREFF: the spell's number of effects
	* EFFECTIVEDAMAGE: the base damage the spell has if cast at the base path level
	* DAMAGESCALING: the extra damage the spell gains for each extra path level
	* DAMAGE: the spell's number of effects
	* EFFECTNUMBER_ADDITIVE: The spell's effect number - 599, used for effect numbers 600-699 to show eg how many horror marks a spell adds
	* EFFECTNUMBER_5XX: The spell's effect number - 499, used for effect numbers 500-599 to show eg how many extra arms a ritual is giving you
	* NEXTSPELL_EFFECTNUMBER_5XX: The effectnumber of the spell's nextspell - 499. This is used for the permanent effect spells that rely on using a dummy spell to allow targeting another commander. This is very likely the only use for this string.
	
	Practically these are used for spells with scaling effects not displayed on the ingame UI, such as gem transmutation, seeking arrow, remote summons, horror marks...

\#copyspell "Spell"
	This is done at the start of the spell definition. Use to keep unique and unmoddable traits, such as twiceborn's x gems per size, GfH's inaccurate modifier...
		
### New or nonstandard parameters

\#spelltype <int>
 * A bitmask with the following:
	* 1	effect is a buff
	* 2	effect is an evocation
	* 4	effect is a ritual
	* 8	battlefield wide variants will be automatically generated from high AoE values
		* For buffs, this becomes 100% of the field at AoE > 25. For evocations, this becomes 100% of the field if >=120, 50% of the field if >= 100, and 25% of the field if AoE >= 80.
	* 16	number of effects scales with research level (note that "regular" scaling should be done using the normal illwinter stuff above)
	* 32	aoe scales with research level
	* 64	damage scales with research level
	* 128	maxbounces scales with research level
	* 256	effect number scales with research level
	* 512	effect is a battle summon
	* 1024	unused, formerly a marker to not force blood spells to cost slaves
	* 2048	battlefield enchantment
	* 4096	research scales aispellmod, the spell's aispellmod is added for each additional research level
		
\#schools <int>
 * Ignore the modmanual values, this is now a bitmask for what research schools things are allowed into. Note that these are 2^(the mod manual values)
	 * -1	(special) unresearchable, use for nextspell or other effects that should never generate as standalones
	 * 1	Conj
	 * 2	Alt
	 * 4	Evo
	 * 8	Const
	 * 16	Ench
	 * 32	Thaum
	 * 64	Blood
	 * 128	Holy
			
\#paths <int>
 * The paths this spell can be assigned to. As with research schools these are 2^(the mod manual values).
	* NONE = -1
	* FIRE = 1
	* AIR = 2
	* WATER = 4
	* EARTH = 8
	* ASTRAL = 16
	* DEATH = 32
	* NATURE = 64
	* BLOOD = 128
	* HOLY = 256 [special, may not act as expected]
	
\#pathskipchance <path> <chance>
 * There is is x% chance that this effect will not generate with the listed primary path. This is used to do things like making Lightning Bolt rarely have an Astral casting requirement.
			
\#secondarypaths <int>:
 * As #paths, but allowed paths for the secondary path requirement
 
\#secondarypathchance <int> (default=10)
 * X% chance for this spell to generate with a secondary path.
			
\#skipchance <float>
 * percentage chance (0-100) to not give a spell of this type when requested and a directive to make something else instead. Note that if not enough spells generate at a given research level, it attempts a second run ignoring skipchances.
	
\#nextspell "<spell effect name>"
 * This is NOT what the mod manual normally uses for nextspell!
	* When this effect is used to create a spell, it will be generated a #nextspell from the given effect name
	
\#extraspell "<spell effect name>"
* When this effect is used to create a spell, a copy of the listed spell effect will also generate with the same pathing at the same research level. This is used to make sure communion spells come in pairs, and all the elemental royalty come together, and similar uses.
			
\#power <int>
 * The "power level" (IE: appropriate research level) of the given numbers. This will be extrapolated to make stronger versions.
	
\#maxpower <int>
 * The highest allowed research level for this spell effect. This can be greater than 9 in which case the effect can be scaled by modifiers that increase spell power.
	
\#pathlevel <int>
* The path level suggested to cast this spell at the specified power level. This may be diverted into secondary paths or otherwise messed with.
	
\#scalerate <float>
* The approximate amount of scaling stats per research level of a spell. It adds N if generated with a power level 1 over #power, 3N if generated 2 over, 6N if generated 3 over...
 * This can affect number of effects, aoe, and damage (see #spelltype and the full description above)
	
\#pathperresearch <float> (default=0.66)
* The amount of extra path requirement to add per extra research level. This is rounded DOWN.
	
\#scalefatigueexponent <float> (default=1.7)
* Additional fatigue (added to base) is added equal to (#scalerate total)^this.
	
\#scalecost <float>
* This multiplies the calculated scale rate for the purposes of calculating fatigue (and gem counts) and path level. Use <1 if spells come out too high path and expensive, or >1 if they are too low. This option is a bit more of a sledgehammer and I preferred using the other things if at all possible.
	
\#descr <pathflag> "description"
* Set the description for when the primary path is as specified. This can (and should) be used multiple times, one for each path.
	
\#name <pathflag> "name"
 * Set a possible name for specified primary path. Unlike #descr this can be used multiple times on one path to create a list of names to draw from.
	
\#namecond <attrib> <comparison> <comparison value> <pathflag> "name"
* Like #name, but sets a possible name only when some conditions are met. <attrib> should be a spell parameter. Comparison should be a comparison operator such as < > <= >=. Value is the value to test against.
 * Example:
 * #namecond aoe < 1 2 "mistform"
 * #namecond aoe > 0 2 "fog warriors"
 * This combination will give the name "mistform" when the effect is aoe 0 (IE: self) and "fog warriors" if the aoe is larger. Both are set to the air path (2).
	
\#namecond2 <val1> <op1> <spell value> <op2> <val2> <pathflag> "name"
 * Like #namecond, except it is only true for things within a range.
 * #namecond2 1 < aoe < 10 2 "fog warriors"
 * This condition is only true if the spell aoe is between 1 and 10, and only applies to the air path.
	
\#descrcond
 * Like #namecond but for descriptions instead.
 
\#descrcond2
 * Like #namecond2 but for descriptions instead.
 
\#skipflightspr
 * Using this will not override the flight sprite. This means it will keep special ones such as that from gifts from heaven.
 
\#skipexplspr
 * Using this will not override the explosion sprite. This means it will keep special ones such as that from drain life.
 
 
\#chassisvalue X
 * For summons. This value is used to denote the fatiguecost of the chassis alone without any leadership or magic traits, which is used as the cost scaling value for most unit modifiers. This is to avoid overpricing human mages that get say heat auras. A human mage with a heat aura is hardly worth more than one without, as the thing that makes him useful is his paths and not the fact he has a heat aura.
 
\#unique
 * This effect will only be used to generate one spell effect.
 
\#alwaysgenerate
 * This effect is guaranteed to be generated at the end of the generic spell phase if it was not already. Used for dispel, bishop fish, and other things that are more or less essential to any spellbook.
 
\#donotsetextraspellpath
 * If set, extraspells will not follow the pathing of the effect that produced them. This is used to make elemental royalty all show up together with their different path requirements.
 
\#scalefatiguemult X (default 0)
 * Adds X fatigue for each total scaling value. Typically used for summoning spells to make their cost scale sensibly.
 
\#noadditionalnextspells (default 0)
 * If greater than zero, secondary effects which confer nextspells are not allowed. This is typically intended for cases where extra nextspells are not desired such as on earthquake (as they will be added after cave collapse and only trigger in caves).
 
\#basescale X
 * For use with globale enchantments with scaling parameters. This should be the base value of the scaling parameters. For instance, a global enchantment that has a (2% + Scale Amount) chance per candle to do something should have this set at 2.
 
\#secondaryeffectskipchance X
 * An additional X% chance to skip secondary effects for this spell effect.
 
\#banishment 1
 * This spell is a custom banishment and can be used to replace a generic one. #secondarypaths is used to designate which path(s) it can be used for.
 
\#smite 1
 * This spell is a custom smite and can be used to replace a generic one. #secondarypaths is used to designate which path(s) it can be used for.
 
\#holyword 1
 * This spell is a custom holyword and can be used to replace a generic one. #secondarypaths is used to designate which path(s) it can be used for.
 
\#smitedemon 1
 * This spell is a custom smitedemon and can be used to replace a generic one. #secondarypaths is used to designate which path(s) it can be used for.
 
\#permanentslotusage 1
 * This spell adds an "unnatural" effect to a unit's six effect slots. This should be used for rituals that add arbitrary effects that are not obtained through other ways. Spells such as horror mark that are found in the base game should not use this. It exists to prevent too many of these spells from being generated.
  
\#eventset "Event Set Name"
 * This spell will call the named EventSet, causing whatever additional output it generates to be included with this spell. Used to introduce events or random creature pools to spells.

\#newunit "New Unit Name"
 * This spell will call the named NewUnit, generating a new unit entry and updating the spell's damage value accordingly. Because of this, the damage value of summoning spells using this does not matter as it will be overwritten at generation.
 
\#badaispell 1
 * Tag rituals which the AI will have no idea how to cast with this. This is for the single player people out there who want to play vs AI but don't want them wasting gems on rituals that do nothing, such as event driven spells that need to be cast in specific places like capitals.
 
\#noresearchdifferenceskip 1
 * Ordinarily, spells are less likely to generate the further they are away from their base research level. This command prevents that occuring for the spell effect it is used on.
 
\#siegepatrolchaff 1
 * Used to mark ritual summoning spells that generate chaff whose intended purpose is not fighting. This can be patrolling, bringer of fortune, sieging, or other roles: it is used to prevent them getting secondary effects.
 
\#priority <int>
 * All naming and description commands after this line are at the given priority. Default priority is 0. Possible names are always considered from the highest priorities first - this is to allow modified spells such as touch range spells to always get their special names and descriptions if such a modifier is applied to them.

## Modifiers

### Simple Additions

These parameters are just flatly added to the values on the parent spelleffect.

\#damage
\#aoe
\#power
\#range
\#precision
\#nreff
\#pathlevel
\#fatiguecost
\#maxpower
\#maxbounces
\#casttime
\#effect
\#aispellmod
\#scalecost
\#scalerate
\#pathperresearch
\#scalefatigueexponent

\#details - Is appended to the end of the spell details

### Others

\#skipchance
 * X% chance to skip using this modifier.
\#spelltype
 * Required spelltype flags for this modifier to be valid
\#descr
\#desrcond
\#desrcond2
 * Both function similarly to the effects of the same name on spell effects. The exception is that this is appended to the end of the normal description.

\#req <param> <op> <value>

\#req2 <val2> <op1> <param> <op2> <val2>
 * Functions in much the same way as \#descrcond and similar functions. All requirements must be satisfied for a modifier to be considered valid.

\#set <param> <value>
 * Sets the specified parameter on the FINAL SPELL to the given value. For instance, \#set range 1 would give the spell a range of 1, regardless of whatever range or range scaling the original effect had.

\#mult <param> <value>
 * Multiplies the specified parameter on the final spell by the given value. \#mult range 1.5 would increase range by 1.5 times.

\#nobattlefield
 * This becomes an invalid modifier for spells with an aoe of X% of the battlefield.

\#givecloudsfx
 * Changes the explosion sfx of the spell to something appropriate for a cloud of that path. Intended to go with modifiers that change a spell into a cloud spell (and increase effect number appropriately).

\#reqdamaging
 * If 0, the spell cannot have a damaging effect number. If any value greater than zero, the spell must have a damaging effect number. If left untouched or set to -1, no limit is imposed.
 
\#minfinalfatiguecost
 * If set, the spell's final fatigue cost should end up being equal to or higher than this value.

\#maxfinalfatiguecost
 * If set, the spell's final fatigue cost should end up being less than this value.

## Secondary Effects

### Simple additions

\#damage
\#power
\#range
\#aoe
\#precision
\#nreff
\#pathlevel
\#fatiguecost
\#maxbounces
\#casttime
\#scalecost
\#scalerate
\#aispellmod
\#pathperresearch
\#scalefatigueexponent

### Modifier lookalikes

These function the same as they do when used in modifiers.

\#skipchance
\#spelltype
\#descr
\#details
\#descrcond
\#descrcond2
\#req
\#req2
\#set
\#mult
\#nobattlefield
\#minfinalfatiguecost
\#maxfinalfatiguecost

### New effects

\#anysummon 1
 * This is shorthand for making summon only secondary effects. Specifically this is a condition which only allows the modifier to apply to spell effects with effect numbers that are one of: 1, 10001, 10050, 10038, 21, 10021

\#fatiguecostpereffect
 * This adds a flat fatigue cost per effect on the final spell. Good for summon effects that should be charged per unit made, for example death explosions or bringer of fortune.

\#fatiguepersquare
 * This adds a flat fatigue cost per square the spell affects. Good for adding appropriate costs to secondary battle spell effects.

\#nextspell
 * Adds a nextspell to the main spell effect.

\#unitmod
 * Uses a unitmod to modify the summoned unit. The unitmod's requirements are checked and will prevent the secondary effect being used if it is not. Using this on something that is not a summon will cause very strange things to happen.

\#magicpathvaluescaling (default 0.0)
 * This allows certain unit traits to scale cost of magic paths, just as \#chassisvalue on effects causes most of them to be exempt. Essentially, each summoned commander is made of a "chassis value" (determined with the command) and the "magic value" (which is the unit's full cost minus the chassis value). This command adds (\#magicpathvaluescaling \* chassis magic value) to the fatigue cost of the spell. This is useful for things such as immortality which have a value on human mages with an otherwise physically weak chassis.
 
\#offensiveeffect 1
 * If set, this modifier will only apply to spells whose scaling AoE is calculated as less than `3*((L(L+1))/2)` where L is the research level of the spell. This is to stop mass rust getting stronger secondary effects than its primary is!
 
\#scalingaoelimit 1.0
 * If set, this modifier will only apply to spells whose scaling AoE is calculated as less than `X*((L(L+1))/2)` where L is the research level of the spell. This is to limit the effectiveness of secondary effects at lower research levels. Useful values: 2.5: battlefield at RL6+, 2.0: battlefield at RL7+, 1.5: battlefield at RL8+, 1.2: battlefield at RL9
 
\#ondamage 1
 * If set, the nextspell conferred by this secondary effect will be set to be on damage. This also makes the secondary effect not allowed on spells that already have an ondamage effect.
 
\#requiredresearchelevel <int>
 * If set, the research level of the final spell must be this number or higher.
 
\#anysummon 1
 * If set, the secondary effect can be applied to any kind of summon spell. This can be further limited with #req.
 
\#minfinalaoe <int>
 * If set, the resulting AoE of the spell must be this value or higher. This can be used to prevent very weak secondary effects, for instance MRNE capped damage, from being applied to spells that hit very small areas.

## Unit Modifiers

These accept inspector tags. For instance:

\#leper 5

would add +5 to the reaper value of the unit.

Additionally, the following are supported:

\#descr "String"

\#descrcond <param> <op> <value> "String"

\#descrcond2 <val1> <op> <param> <op2> <val2> "String"
 * This appends to the modified unit's description. Note that path identifiers need not be used here.
 
\#nameprefix "string"
 * This is used as a name prefix for the unit.

\#weaponmod "string"
 * This goes to the named weaponmod and applies it to the unit. The weaponmod must be valid on at least one of the unit's weapons for the unitmod to be considered valid, and in turn this means that everything must be satisfied for a secondary effect to be used. For instance, if a weapon mod specifies it only wants to apply to nonmagical weapons, any unitmod that uses the weapon mod cannot apply it to something with only magical weapons.
 
\#set <param> value
 * This works as above, except it expects unit parameters.
 
\#landok 1
 * If set, aquatic creatures are not allowed.
 
\#uwok 1
 * If set, only creatures with any kind of amphibiousness or aquatic are allowed.
 
\#eventset "Event Set Name"
 * If set, loads the named event set. Probably only useful in combination with the below #attributeforrandomunit
 
\#attributeforrandomunit "attributename"
 * If set, sets attributename to the unit id output from the unitmod's eventset. For instance, having an eventset build a montag and using #attributeforrandomunit "raiseshape" would cause the modified units to raise killed creatures as whatever random magicgen creatures the event set's montag output was.
 
\#addweapon <id>
 * Creatures modified with this weapon mod gain the weapon ID as an additional weapon.

## Weapon Modifiers

### Mod Manual stuff
\#att
\#def
\#len
\#nratt
\#ammo
\#secondaryeffectid
\#secondaryeffectalwaysid
\#damage

### Similar commands

\#set
\#mult
\#nameprefix
\#req
\#req2

### New commands

\#spec
 * The Dom modding interface does not support modding the specmask for weapons directly, but magicgen does and it should be used to modify things such as the damage types and magicalness of weapons by adding the appropriate spec flags. This will be interpreted and converted to the correct commands automatically.
 
\#extracommand "string"
 * Adds the given strings as extra raw mod commands. I cannot remember what I used this for but something needed it!
 
\#setweaponmagic 1
 * If present, the weapon will be set to magical if it wasn't already. Useful to avoid needing two different weaponmods (one for magic, one for nonmagic that adds to spec) if you want to make a weapon magical...
 
## Event Sets

These files should begin \#neweventset "name". Commands listed below should be used here. Then \#end should be used, followed by the raw event mod code. This means each file can at most contain one event set.

Each event set can have at most one unitid associated with it. This can be specified with \#usefixedunitid, \#selectunitmod, or just omitted.

\#requiredcodes X (default 0)
 * This event requires X event codes. These are dynamically assigned. To reference codes used, use CODE1 CODE2 CODE3 etc in the raw event code and they will be replaced accordingly.
 
\#usefixedunitid X
 * If set, the event will always use X as a base unit ID. Unitmods may still be applied to it.
 
\#desiredmontagsize X
 * If set, a montag will be created with a dummy unit set to firstshape to the montag. X denotes the desired number of things in the montag
 
\#restrictunitstospellpaths 1
 * If set, only units with summoning spells corresponding pathed summoning spells are valid to throw into a montag. The same goes with secondary effects. This is used to make fire globals spawn things that are normally fire summons.
 
\#effectnumberforunits X
 * Can be used multiple times. Determines which spell effect numbers can be used when building montags.
 
\#mincreaturepower X
 * Set the minimum research level to take summoned units from. This is increased by 1 for every level over the minimum level the parent spell generated. For instance, a research 5 global with a mincreaturepower of 1 would draw from summoning spells with a research level of 4 when it generates at research 9.
 
\#maxcreaturepower X
 * As mincreaturepower, except it's the upper bound.
 
\#secondaryeffectchance X
 * Has a X% chance to apply an eligible secondary effect to a unit created in the montag.
 
\#selectunitmod "Unit Mod"
 * The name of a unit mod to use to pick summons. This is not actually applied, it is rather used as an eligibility test. This does for instance allow only units with <10 hp or that can survive underwater to be picked for a summoning global.
 
\#allowedunitmod "Unit Mod"
 * The named unit mod can be applied to monsters generated by this event set. This can be used multiple times, and only unitmods included AND that have a corresponding secondary effect can be used.

\#unitmodlist "Unit Mod List"
 * Adds all unitmods in the named unitmod list as an allowed unit mod.
 
\#scaleparam "param" 1.0
 * This causes the named param to be scaled with the scale factor of the parent spell. The float value after the named param is a multiplier. For instance, \#scaleparam "req_rare 2.0" will increase the value of all req_rares in the event block by 2 multiplied by the spell scaling rate. This command can be used multiple times.
 
\#scaleparam_mult "param" 1.0
 * This causes all instances of the named param to have an amount added to them based on the base value of the parameter. Specifically, the amount added is (<base value> * scale amount x <value of this command>). For instance, \#scaleparam_mult "req_rare 0.2" will add (20% * <the spell scaling rate>) to the value of all req_rares in the event block. This command can be used multiple times.
 
\#makedummymonster 0
 * If set, a firstshape dummy will not be made by the montag builder.
 
\#makebattledummymonster 1
 * If set, a dummy monster suitable for battles (that will transform into a random creature after one round) will be made by the montag builder.
 
\#dummymonstername <path> "Name"
 * Can be used multiple times per path. Gives the given name to dummy monsters. Which names are used depends on the primary spell's path: for instance the blood wall defender spells use #dummymonstername 128 "Infernal Creature"
 
### Module Commands

It is strongly advisable to be familiar with regular event sets and to look at an example of this, such as the beneficial or offensive globals. To annotate this:

#### Example

This is the event set that is called by the spell effect.

```
#neweventset "Beneficial Global"

#module "CONDITION" "Beneficial Global Condition"
#module "EFFECT" "Beneficial Global Effect"

#end

#newevent
CONDITION
EFFECT
#end
```

It asks for a random Beneficial Global Condition, and replaces the text CONDITION with its output, and does the same for effects.

A sample Beneficial Global Condition is the following:

```
#neweventset "Beneficial Global cond winter"
-- This describes what power level range this effect can have. The sum of these across all modules must equal (current research - minimum research) of the original spell effect
#minpowerlevel -2
#maxpowerlevel 2

-- scaling
#scaleparam "req_domchance" 2
#modulebasescale 2

-- allocate this eventset to the group
#modulegroup "Beneficial Global Condition"

-- The final spell name is made up of two parts: the verb and the noun in that order.
#noun "Winter"
#verb "Winterbound"

-- like #skipchance, but for modules only
#moduleskipchance 50

-- text to replace, this applies to the effects
#textrepl "SUBJECT" "The common populace"

-- Add to description and detail
#moduledescr "In winter, this enchantment affects all friendly provinces with the caster's dominion."
#moduledetails "Every turn in the three months of winter, each friendly province has a SCALEAMT percent chance to be affected per point of friendly dominion in the province."

-- Raw event code follows. Note the missing #newevent and #end - these are supplied by the eventset that is calling the module group
#end


#rarity 5
#req_pop0ok
#nation -2
#req_friendlyench ENCHANTID
#req_enchdom ENCHANTID
#req_season 3
#req_domchance 2
```

... and a corresponding Beneficial Global Effect...

```
#neweventset "Beneficial Global action gold fire"
-- this half also provides power level values
#minpowerlevel -2
#maxpowerlevel 10

-- only allowed if the spell is fire path
#req path1 == 1

-- scaling
#scaleparam "gold" 10
#modulebasescale 20

#modulegroup "Beneficial Global Effect"

-- the other half of the name components
#noun "Midas Touch"
#verb "Goldtouch"

-- the other half of description components
#moduledescr "SUBJECT may find that metal objects they touch occasionally become converted to solid gold."
#moduledetails "Grants SCALEAMT gold."

-- as before, no #newevent or #end
#end

#gold 20
#msg "With a mere touch, some mundane metal has been turned to gold!"
#nolog
```

Combined, these effects would result in a global called Winterbound Midas Touch or Goldtouch Winter, which generated gold in the winter.

Offensive globals are currently a more complex example - they make use of the SUBJECT replacement in the effect event set, as well as using multiple events with multiple replacements. As an example of this, a condition can use the EFFECT replacement itself to make multiple checks all with the same randomised effect:

```
#rarity 5
#req_pop0ok
#req_ench ENCHANTID
#req_rare 5
#req_targorder 14
EFFECT
#end

#newevent
#rarity 5
#req_pop0ok
#req_ench ENCHANTID
#req_rare 5
#req_targorder 14
EFFECT
#end

#newevent
#rarity 5
#req_pop0ok
#req_ench ENCHANTID
#req_rare 5
#req_targorder 14
EFFECT
#end

#newevent
#rarity 5
#req_pop0ok
#req_ench ENCHANTID
#req_rare 5
#req_targorder 14
EFFECT
#end

#newevent
#rarity 5
#req_pop0ok
#req_ench ENCHANTID
#req_rare 5
#req_targorder 14
```

#### Documentation

\#module "text to replace" "module group name"
 * Picks a random legal module from the listed module group, and substitutes "text to replace" with its event code. Can be used multiple times. This is used to make modular globals with mix and match conditions and effects, by having one module group provide conditions such as #req_researcher, and another to provide actions such as #banished -11. Note that "text to replace" occurs even in the module code themselves.
 
\#modulegroup "name"
 * Adds the current event set to the named module group.
 
\#noun "name"
\#verb "name"
 * Together, form parts of a spell's name. The verb comes first, and then the noun.
 
\#textrepl "symbol" "replacement"
 * Replaces all cases of symbol with replacement in the resulting event code, even if the code is from another module group.
 
\#moduledescr
\#moduledetails
 * Adds to the appropriate text of the main spell.
 
\#minpowerlevel
\#maxpowerlevel
 * Act similarly to creaturepower for montag builders. Minpowerlevel is the base "research cost" of the module, more may be added for scaling. The total of the "research costs" across all modules must equal (research level spell is generated at - min research level for the spell).
 
## New Units

TODO

## Magic Sites

All mod commands that add site effects may be used.

Additionally, the following work in the same way as the eventset equivalent:

\#effectnumberforunits
\#usefixedunitid
\#desiredmontagsize
\#restrictunitstospellpaths
\#mincreaturepower
\#maxcreaturepower
\#secondaryeffectchance
\#makedummymonster
\#makebattledummymonster
\#dummymonstername
\#unitmodlist
\#allowedunitmod
\#selectunitmod

\#name <path> <name>
 * Gives a name for the site when the associated spell effect has the given path.

 
		
# Strings

This program contains a convoluted string processor for names and descriptions.
Each spell is evaluated for plural effects. This is the case when:

```
	number of effects > 1
OR
	spell is an evocation AND aoe > 1
	spell is a buff AND aoe > 0
```
	
The plural-ness has some bearing on the replacements described below.

The following have special meaning and will be replaced:
 * ARTICLE		"a" if singular, removed if plural
 * ARTICLE_N	"an" if singular, removed if plural
 * PRONOUN_POS	"his" if singular, "their" if plural
 * PRONOUN_SUB	"he" if singular, "they" if plural
 * PRONOUN		"him" if singular, "them" if plural
 * SUBJECT		Strings such as "one person", "one enemy", "many enemies", "the entire army", "the entire battlefield". The replacement chosen depends on the spell aoe.
 * SIZE		Strings such as "tiny", "small", "moderate", "huge", "massive": single words that describe the spell aoe.
 
(Note that the choice to default to male pronouns is based on the fact that the base game does so)
	
Words can also be autopluralised and replaced with a defined list of synonyms. These are in /data/naming. Each line should be in the format:

<Word to Replace><tab><Replacement>

The replacement can be omitted, but the tab is always required.

Surrounding a word or phrase with $dollar signs$ will replace it with a random synonym, defined in synonyms.txt.
Surrounding a word with %percentage signs% will pluralise it if the spell warrants plural text. Overrides for irregular plurals can be defined in plurals.txt

Note that synonyms are evaluated first. This means that they can be combined as such:

%$word$%

First, a synonym for "word" will be looked up and a replacement made. Then, that replacement will be made plural.

Spell names are passed through a rather basic method that capitalises words.