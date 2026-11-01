# Generation IX battles for the SoulSilver roster

The user selected Generation IX and, on 2026-11-01, explicitly approved adding
modern moves and updating abilities for the existing Pokémon. The original
SoulSilver story, roster, encounter progression and native single-screen app
remain the base. The installed four-feature QoL build stays playable while the
modern ruleset is developed and tested.

Port established behavior from hg-engine where compatible, pinned to
61b510cfb6cf7d77c3b083150fad3499f82fd326, retaining its credits and reuse terms.
Its HeartGold patch addresses and expanded data structures are not interchangeable
with this source-built SoulSilver. Each adopted algorithm and data table needs
an explicit source integration and tests.

The work has four connected parts:
1. Fairy typing for the 20 existing species, the modern shared type chart,
   move-type changes and all UI names/icons. Damage, AI and previews agree.
2. Modern move data/effects and later-generation moves learned by the existing
   roster, including Fairy attacks such as Moonblast. Preserve existing move IDs
   and saved moves; expand the name/description/script/learnset consumers together.
3. Updated species ability slots, later-generation ability behavior and modern
   ordinary battle rules. Audit storage widths and packets before expanding IDs.
   Existing saves load without losing Pokémon or progress. Hidden-ability data
   does not imply replacing original encounter/story scripts with new rewards.
4. Rebuild the ROM and matching native executable, validate on copied saves,
   then back up and replace the installed artifact pair. Keep the original ROM,
   previous save and installation recoverable.

Mega Evolution, Z-Moves, Dynamax, Terastallization and additional Pokémon are
separate additions. The Gen IX target refers to ordinary move/ability, status,
critical-hit, type and turn rules; generation-exclusive battle gimmicks are not
part of this port.

Development flags must permit testing pieces independently. Do not call an
intermediate type-only or numeric-data-only build a complete Gen IX conversion.
All source transformations must be reproducible and reversible: ignored SDK,
ROM data, generated native code and local assets do not become source commits.
Maintain a coverage list for differences that hg-engine itself has not finished.
