# Basics:

The prompts should be fairly self explanatory, but for completeness (and the fact I may yet add more here):

Spells per level: number of spells to make per research level. Sometimes you get more than this because a few effects generate more than one spell, for instance a communion master spell will immediately generate a communion slave spell at the same research level and pathing.
Construction factor: a multiplier to the number of spells per level used for spells going into construction. This is to replicate the fact that vanilla construction has significantly fewer spells than other schools.
National spells: the number of national spells to generate per nation. These are targeted at the paths that each nation gets on its mages.
Modname: The name for the .dm file. It is suggested to pick something sensible like the game name for this.
Modlist: a list of filepaths, separated by commas. This ONLY scans for new nations and tries to guess their mages, and is used solely to add national spells.

Note that Dominions has a limit on the number of modded spells that can be reached quite easily if the number of national spells is turned up too high. The program will complain if this happens.

# Datafile Documentation

This will assume you have a passing knowledge of how Dominions modding (especially that for spells) works. Even if you do, you might want to refer back to the mod manual sometimes. If you don't, you might do well to understand how Dominions spells are put together and what all the important properties do before messing with a program which is designed to churn lots of them out.

## How magicgen works:

First it goes and sets nearly all vanilla spells to unresearchable. This means they still exist so vanilla magic items can cast them, and a few generic divine spells are specifically excluded. The fact they still exist means that #copyspell can also be used to transfer unique unmoddable properties such as soul slaying, twiceborn's X gem cost per size, gifts from heaven's special fly sprites, and so on.

Then it goes and generates a bunch of generic spells.

Then it generates holy spells for each path.

Then it generates national spells.

Spells are generated from spell effects, defined in the data .txt files. One spell effect will be something like "Falling fires", that specifies the basic parameters all variants of that spell should have (damage, aoe, range, path requirements, names, descriptions...), as well as how to scale it as research levels are increased. In the case of the implementation for falling fires used here, the value that scales with research is the AoE value. This means the file needs to contain the amount of aoe gained as research increases: this is not a linear scale, but more on that later.

Spell effects also have "modifiers" that somehow alter their delivery, such as making a damaging spell into a touch ranged spell or making it cast faster or slower. Naturally these modifiers override parameters of the original spell effect and should only be applied to effects meeting certain requirements, which they can specify.

Spell effects additionally have a "secondary effect" that adds something else to the spell. In the case of most spells this is some extra effect such as setting everything within the area of effect on fire. For summons this instead takes the place of some kind of modification of the base summoned creature such as making it explode on death with #deathfire. A these effects then call a "unitmod" which tests eligibility and is responsible for making the alterations to the creature. The unitmod can then call a weaponmod which does much the same to the unit's weapons.

**NOTE that comments on the end of lines are illegal and will cause errors when parsing these files!**

Perhaps to illustrate how things work, it would be worth walking through a spell effect that makes falling fires:


### A broken down example spell effect
```
-- Define a new effect and its name
#neweffect "Fire Evo Instant"
-- These are all basic things that are copied over and should be familiar to anyone who has dealt with dominions modding
#effect 2
#damage 2010
#spec 96
#aoe 1003
-- This sets the minimum research level at which this effect can appear, and it will do so with unscaled numbers (as they are written above)
#power 4

#precision 1
#range 30
-- Nonstandard, but hopefully self explanatory
#pathlevel 2
#fatiguecost 20
#explspr 10011
#sound 123

-- Note that THESE ARE NOT THE PATH CONSTANTS USED IN THE MODDING MANUAL. Instead they are 2^n where n is the normal path id
-- Thus this spell is available to fire (1) and blood (128) with a secondary path of fire (1). Formerly it was available to others too
-- (which is why there are names and descriptions for other paths)
#paths 129
#secondarypaths 1

-- 1: Fire
#name 1 "Falling %$fire$%"
-- 2: Air
#name 2 "Falling %$fire$%"
-- 4: Water
#name 4 "Falling %$fire$%"
-- 8: Earth
#name 8 "%$fire$% from $underground$"
-- 16: Astral
#name 16 "%$fire$% from beyond"
-- 128: Blood
#name 128 "$infernal$ %$fire$%"
#descr 4 "The cold is sucked out of the air above the caster's enemies. A SIZE area is rapidly heated with the potential to badly burn enemies within."
#descr 2 "The latent heat in the air is focused upon the caster's enemies. A SIZE area is rapidly heated with the potential to badly burn enemies within."
#descr 1 "Flames fall onto a SIZE area with the potential to badly burn SUBJECT."
#descr 8 "Heat from the earth is gathered and brought upon a SIZE area of the caster's choosing. The resulting flames may badly burn enemies within."
#descr 16 "Heat from somewhere in time and space is focused into a SIZE area of the caster's choosing. The resulting flames may badly burn enemies within."
#descr 128 "$BLOOD_INTRO$, the caster directs infernal flames upon a group of his enemies. This may badly burn SUBJECT."

-- This is a bitfield which describes what kind of spell it is as well as what part of it to scale
-- in this case it is evo-like, allows conversion to x% of battlefield, and will increase the aoe
#spelltype 42

-- The base scaling rate. This describes how much to increase the parameter we are scaling (in this case aoe) by per extra research level
#scalerate 8

-- As with the paths, this is a field using 2^n of default school ids, 4 meaning it only goes into evocation
-- but importantly this allows a single spell effect to be placed in multiple research schools
#schools 4
#end
```

## Scaling with research levels

As mentioned above, power scaling is nonlinear. The total scaling value which is then added to the defined base values, is given by:

L = number of research levels this spell is generating over the minimum the effect allows. So an effect with \#power 4 generating at research 6 would have a value of 2 here.

```
scalerate*((L(L+1))/2)
```

Essentially this means that a scalerate of 1 produces scaling values that follow the triangular number series. The defined scalerate is simply a flat multiplier to this.


Path level requirement is adjusted by:

P = pathperresearch value (default before modification is 0.66, a value I came up with by messing with numbers)
L = number of research levels over the minimum

```
floor(P*L)
```

Fatigue cost is first modified by:

```
10*(research levels over the minimum)
```

It is next modified by:

```
(total scaling value) * (scalefatiguemult, default value is 0.0)
```

This means that scalefatiguemult is a flat addition per scaling value, which is useful for effects such as summoning.

Next, the fatigue cost is modified by:

```
(total scaling value) ^ (scalefatigueexponent, default 1.6)
```

Which is responsible for making large scaling values of stuff more expensive.

For combat spells only, this is then reduced to 100x the path level of the spell (to make it castable at the level mentioned). For spells with an increased number of effects, the number of effects is reduced proportionally - this stops very expensive modifier summoning spells from desiring >10 gems a cast and being reduced to 2 due to the path level. 

It is then rounded down to various round values to make some nicer looking numbers on the eyes. Specifically this rounds to a multiple of 100 if the spell is over 100 fatigue, or a multiple of 5 if under.

# The boring documentation list

Ideally, once understanding the above, readers can probably copy what is already in existence and just look things up here if are confused about something.

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
\#aicastmod
\#details
 * As the usual, additionally the following strings are replaced in spell details:
	* EFFECTIVENREFF: the base number of effects for the spell cast at the base path level
	* NREFFESCALING: the number of effects the spell gains for each extra path level
	* NREFF: the spell's number of effects
	* EFFECTIVEDAMAGE: the base damage the spell has if cast at the base path level
	* DAMAGESCALING: the extra damage the spell gains for each extra path level
	* DAMAGE: the spell's number of effects
	* EFFECTNUMBER_ADDITIVE: The spells effect number - 599, used for effect numbers 600-699 to show eg how many horror marks a spell adds
	
	Practically these are used for things like gem transmutations and remote summons that list no values ingame.

\#copyspell
	This is done at the start of the spell definition. Use to keep unique traits: EG soul slay, twiceborn's x gems per size, special anims on GfH...
		
### New or nonstandard parameters

\#spelltype
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
		
\#schools
 * Ignore the modmanual values, this is now a bitmask for what research schools things are allowed into. Note that these are 2^(the mod manual values)
	 * -1	(special) unresearchable, use for nextspell stuff
	 * 1	Conj
	 * 2	Alt
	 * 4	Evo
	 * 8	Const
	 * 16	Ench
	 * 32	Thaum
	 * 64	Blood
	 * 128	Holy
			
\#paths
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
	* HOLY = 256
			
\#secondarypaths:
 * As #paths, but allowed paths for the secondary path requirement
			
\#skipchance
 * percentage chance (0-100) to not give a spell of this type when requested and a directive to make something else instead. Note that if not enough spells generate at a given research level, it attempts a second run ignoring skipchances.
	
\#nextspell "<spell effect name>"
 * This is NOT what the mod manual normally uses for nextspell!
	* When this effect is used to create a spell, it will be generated a #nextspell from the given effect name
	
\#extraspell "<spell effect name>"
* When this effect is used to create a spell, a copy of the listed spell effect will also generate with the same pathing at the same research level. This is used to make sure communion spells come in pairs.
			
\#power
 * The "power level" (IE: appropriate research level) of the given numbers. This will be extrapolated to make stronger versions.
	
\#maxpower
 * The highest allowed research level for this spell effect. This can be greater than 9 in which case the effect can be scaled by modifiers that increase spell power.
	
\#fatiguecost
 * Base fatigue, gets increased as power level scales up.
	
\#pathlevel
* The path level suggested to cast this spell at the specified power level. Naturally this might get tweaked or become a crosspath etc etc.
	
\#scalerate N
* The approximate amount of scaling stats per research level of a spell. It adds N if generated with a power level 1 over #power, 3N if generated 2 over, 6N if generated 3 over...
 * This can affect number of effects, aoe, and damage (see #spelltype and the full description above)
	
\#pathperresearch N (default=0.66)
* The amount of extra path requirement to add per extra research level. This is rounded DOWN.
	
\#scalefatigueexponent N (default=1.7)
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
 
\#secondarypathchance X (default=10)
 * X% chance for this spell to generate with a secondary path.
 
\#skipflightspr
 * Using this will not override the flight sprite. This means it will keep special ones such as that from gifts from heaven.
 
\#skipexplspr
 * Using this will not override the explosion sprite. This means it will keep special ones such as that from drain life.
 
 
\#chassisvalue X
 * For summons. This value is used to denote the fatiguecost of the chassis alone without any leadership or magic traits, which is used as the cost scaling value for most unit modifiers. This is to avoid overpricing human mages that get say heat auras. A human mage with a heat aura is hardly worth more than one without, as the thing that makes him useful is his paths and not the fact he has a heat aura.
 
\#unique
 * This effect will only be generated once.
 
\#alwaysgenerate
 * This effect is guaranteed to be generated at the end of the generic spell phase if it was not already. Used for dispel.
 
\#donotsetextraspellpath
 * If set, extraspells will not follow the pathing of the effect that produced them. This is used to make elemental royalty all show up together with their different path requirements.
 
\#scalefatiguemult X (default 0)
 * Adds X fatigue for each total scaling value. Typically used for summoning spells to make their cost scale sensibly.
 
\#noadditionalnextspells (default 0)
 * If greater than zero, secondary effects which confer nextspells are not allowed. This is typically intended for cases where extra nextspells are not desired such as on earthquake (as they will be added after cave collapse and only trigger in caves).
 
\#eventset "eventset name"
 * Applies the given event set to this spell. This should be used to make global or local enchantments or spells that trigger a remote event. See below for more on event sets.
 
\#basescale X
 * For use with globale enchantments with scaling parameters. This should be the base value of the scaling parameters.
 
\#secondaryeffectskipchance X
 * An additional X% chance to skip secondary effects for this spell effect.
  

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
\#maxbounes
\#casttime
\#effect
\#aicastmod
\#scalecost
\#scalerate
\#pathperresearch
\#scalefatigueexponent

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
 
## Secondary Effects

### Simple additions

\#damage
\#power
\#range
\#precision
\#nreff
\#pathlevel
\#fatiguecost
\#maxbounces
\#casttime
\#scalecost
\#scalerate
\#pathperresearch
\#scalefatigueexponent

### Modifier lookalikes

These function the same as the modifiers.

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

### New effects

\#anysummon 1
 * This is shorthand for making summon only secondary effects. Specifically this is a condition which only allows the modifier to apply to spell effects with effect numbers that are one of: 1, 10001, 10050, 10038, 21, 10021

\#fatiguecostpereffect
 * This adds a flat fatigue cost per effect on the final spell. Good for summon effects that should be charged per unit made, for example death explosions or bringer of fortune.

\#nextspell
 * Adds a nextspell to the main spell effect.

\#unitmod
 * Uses a unitmod to modify the summoned unit. The unitmod's requirements are checked and will prevent the secondary effect being used if it is not. Using this on something that is not a summon will cause very strange things to happen.

\#magicpathvaluescaling (default 0.0)
 * This allows certain unit traits to scale cost of magic paths, just as \#chassisvalue on effects causes most of them to be exempt. Essentially, each summoned commander is made of a "chassis value" (determined with the command) and the "magic value" (which is the unit's full cost minus the chassis value). This command adds (\#magicpathvaluescaling \* chassis magic value) to the fatigue cost of the spell. This is useful for things such as immortality which have a value on human mages with an otherwise physically weak chassis.
 
\#offensiveeffect 1
 * If set, this modifier will only apply to spells whose scaling AoE is calculated as less than `3*((L(L+1))/2)` where L is the research level of the spell. This is to stop mass rust getting stronger secondary effects than its primary is!

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
 * This goes to the named weaponmod and applies it to the unit. The weaponmod must be valid on at least one of the unit's weapons for the unitmod to be considered valid, and in turn this means that everything must be satisfied for a secondary effect to be used. For instance, if a weapon mod specifies it only wants to apply to nonmagical weapons, any modifier that indirectly uses that weapon mod cannot apply it to something with only magical weapons.
 
\#set <param> value
 * This works as above, except it expects unit parameters.
 
\#landok 1
 * If set, aquatic creatures are not allowed.
 
\#uwok 1
 * If set, only creatures with any kind of amphibiousness or aquatic are allowed.

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
 * This event requires X codes. These are dynamically assigned. To reference codes used, use CODE1 CODE2 CODE3 in the raw event code and they will be replaced accordingly.
 
\#usefixedunitid X
 * If set, the event will always use X as a base unit ID. Unitmods may still be applied to it.
 
\#desiredmontagsize X
 * If set, a montag will be created with a dummy unit set to firstshape to the montag. X denotes the desired number of things in the montag
 
\#restrictunitstospellpaths 1
 * If set, only units with summoning spells corresponding pathed summoning spells are valid to throw into a montag. The same goes with secondary effects. This is used to make fire globals spawn things that are normally fire summons.
 
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
 
\#scaleparam "param" 1.0
 * This causes the named param to be scaled with the scale factor of the parent spell. The float value after the named param is a multiplier. For instance, \#scaleparam "req_rare 2.0" will increase the value of all req_rares in the event block by 2 multiplied by the spell scaling rate. This command can be used multiple times.
 
		
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
 * PRONOUN_POS	"his" if singular, "their" if plural
 * PRONOUN		"he" if singular, "they" if plural
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