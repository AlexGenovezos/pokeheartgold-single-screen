# Ordinary modern move batch

Extend the first five Fairy attacks with twelve ordinary attacks needed by the
original roster's pinned Generation IX profile: Fairy Wind, Leafage, High
Horsepower, Brutal Swing, Drill Run, Smart Strike, Aqua Cutter, Precipice Blades,
Origin Pulse, Petal Blizzard, Boomburst and Tera Blast.

- [x] Use shared literal metadata and native plain/high-critical/never-miss
  effects; retain original move IDs and the embedded 468-entry battle table.
- [x] Translate item-flinch flags explicitly; alias only existing move scripts
  containing the plain GoToEffectScript command. Register Boomburst as sound.
- [x] Preserve original archive members and all existing messages. Append
  private bank829 for compact battle-card labels, keeping full names in750/751.
- [x] Allow full names up to31 glyphs in private name buffers. Precipice Blades
  needs17 slots including its terminator; both GetMoveName and the battle party
  name destination allocate32 only when modern moves are enabled.
- [x] Generate106 base-form level entries for the17 implemented IDs. The
  maximum number of additions for one species is4, within the existing bound5.
  Original moves, alternate forms, battle/save layouts and daycare capacity stay
  intact. Do not invent level-up access for Brutal Swing or Tera Blast when the
  pinned profile contains none; machine/tutor access is separate work.
- [x] Run source/resource/font/learnset regressions and spec/quality review.
  The full120-test host suite passed, including original behavior and the real
  string concatenation bounds regression for Precipice Blades.
- [x] Verify the final matching native build, compact cards, long full names,
  summary/party screens and an ordinary attack in interpreter lockstep.
- [x] Commit and push the source-only milestone.

The final source/ROM/native rebuild passed after the capacity fix. Native
lockstep passed1700 battle frames using Precipice Blades and600 frames opening
the battle Check Moves page; both had zero fallbacks and guard failures. That
page rendered the full16-glyph Precipice Blades alongside Aqua Cutter, Petal
Blizzard and Boomburst. Compact cards read bank829 and showed their correct
types, PP and effectiveness. This used an isolated edited save with --no-save;
the installed app and real save were untouched.

Tera Blast implements its ordinary non-Terastallized Normal special attack.
Terastallization remains outside the approved scope. Wind Rider/Sharpness and
other newer abilities still need their own handlers; shared numeric effects do
not imply the entire Generation IX port is finished.

Upcoming classifiers from the pinned profile: Fairy Wind/Petal Blizzard for
wind abilities, Aqua Cutter for Sharpness, Origin Pulse for Mega Launcher, and
Boomburst for Punk Rock. Its sound classification is already integrated.
