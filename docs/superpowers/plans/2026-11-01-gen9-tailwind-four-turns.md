# Gen IX Tailwind: four turns

This bounded change gives successful Tailwind four turns, including its casting
turn, only with `QOL_MODERN_BATTLE=1`. Battle-off retains the original three-turn
behavior. Types and moves remain independently default-off. This change adds no
moves, abilities, species, events, story changes, opcodes, context fields, save
fields, or mid-turn speed reordering. Support remains 72 extended moves, 336
learning rows and 237 species. Wind Rider and Neutralizing Gas remain separate
unfinished scope.

## References and accepted baseline

- [Showdown 82f129e0, moves.ts](https://github.com/smogon/pokemon-showdown/blob/82f129e0b847bf23395d552f9bb48eb82e53a0ec/data/moves.ts#L18871): duration four, Speed doubled, residual order 26/suborder 5. Its custom Persistent modifier is outside this scope.
- [Expansion c460a866, battle_script_commands.c](https://github.com/rh-hideout/pokeemerald-expansion/blob/c460a8661dfa0598ae25d42a968c690ecbf489c6/src/battle_script_commands.c#L6346): Gen V+ duration four.
- [hg-engine 61b510cf](https://github.com/BluRosie/hg-engine/tree/61b510cfb6cf7d77c3b083150fad3499f82fd326): separate Tailwind count is behavioral reference only; its layout is not imported.
- Accepted source baseline: `b385edc340e6ba7fbeeda29a9216d69c20a107fa` (Sharpness/Soul Dew).

## Timer representation and lifecycle

The public `SIDE_CONDITION_TAILWIND` presence mask stays `0x300`. Bit 11 was
unused between Toxic Spikes bit 10 and Lucky Chant bits 12–14; private
`QOL_TAILWIND_FOURTH_TURN=0x800` and `QOL_TAILWIND_STORAGE_MASK=0xB00` use it
without widening any public presence consumer. C89 negative-array checks prove
the exact masks and disjointness from every other allocated side condition.

| Turns | Storage |
| --- | --- |
| 4 | `0xB00` |
| 3 | `0x300` |
| 2 | `0x200` |
| 1 | `0x100` |
| 0 | `0` |

Private controller helpers decode these states and set a canonical count while
preserving all bits outside `0xB00`. Setter values 5–255 clamp to four. Malformed
`0x900`/`0xA00` decode as four and normalize to `0x300` on the next residual;
orphan `0x800` is inactive and clears without an expiry message.

Only the Tailwind subtraction in `BattleControllerPlayer_UpdateFieldCondition`
changes. Battle-off keeps the original branch verbatim. The existing side
iterator still advances before yielding, and subscript 233 runs once on the
fourth modern residual. Lucky Chant's subtraction is untouched. An active cast
fails; expiry permits a fresh four-turn cast. The side variable alias resolves
the current attacker after Snatch.

## Resource ownership and order

`tools/qol/tailwind_resources.py` owns both transforms. It pins the entire
original subscript 160 source to SHA-256
`c8457cc7a3ae9e1d6bc291e70c96e6a58fdcec979abfb1ea64c2a95ef98662b7` and requires
unchanged-source SDK binary parity before compiling the transformed source.
Only the successful OR operand changes from `0x300` to `0xB00`; the original
compare mask, failure branch, presentation, instruction count and jumps remain.
The owner requires exactly 299 incoming subscripts after Competitive/Simple and
preserves every other member and archive name.

The description is bank 749/row 366 (`MOVE_TAILWIND`), independently of subscript
160 and name bank 750. The original GMM SHA-256 is
`f0763a0583c68cae0c4ec967c202ccae643700147887389c194ffc509670c796`; the original
encoded bank SHA-256 is
`2dd75559a6057016bc5fb3d577b9eaaeb5541d2ac15cc6774750668458f31f77`.
The owner validates the full original source, exact original row, 468 rows and
key 27800, then requires the entire incoming bank to equal that original plus
Snow's row 258. It rejects pre-Snow, duplicate, extended-first, count/key/source
and encoded-bank drift. Snow's original-bank guard is unchanged.

Only row 366 changes to:

```text
The user whips up a
turbulent whirlwind
that ups the Speed
of all party Pokémon
for four turns.
```

Font 00000000 measures the lines at 103/102/102/109/83 pixels, all within 149.
The encoded text fits the actual summary buffer allocated with 128 characters;
the summary reads descriptions from bank 749. Other banks, archive names, keys,
Snow row 258, Soul Dew bank 221/row 225 and move names remain unchanged.

The battle-only script owner follows `modern_simple_resources`. Message order
is abilities → Simple → Snow → Soul Dew → Tailwind → move extension. With moves
enabled, banks 749/750/751 grow from 468 to 899 while retaining their incoming
prefixes, and bank 829 is added. Battle-off never calls either Tailwind owner.
Ability banks 720/721/722 remain 243 rows in battle-on mode and 124 otherwise;
unsupported 240/241 and Sharpness 242 retain their existing treatment.

## Side-word and layout audit

The audit covered every `fieldSideConditionFlags` and `SIDE_CONDITION_TAILWIND`
owner in `src`/`include` and every script `BSCRIPT_VAR_SIDE_CONDITION_*` use.
Both `CheckSortSpeed` operands continue to test only `0x300`. Positive/inverse AI
side checks also use the original mask. The 42,428-byte AI table has one aligned
`0x300` operand, at byte 7328 in the instruction at 7320; it stays unchanged.
Snow's independent changed word 5747 stays separate. Named AI speed comparisons
and speed-order loading still call `CheckSortSpeed`; Gyro Ball consumes its
`effectiveSpeed` result.

Actual script variable aliases 11/12/13, immediate/from-variable updates and
BattleContext Get/Set var 0 retain full words. Guard Spec's read/OR/write adds
Mist without dropping the marker. Reflect, Light Screen, Mist, Safeguard,
Spikes, Toxic Spikes, Stealth Rock, Rapid Spin, Brick Break and Defog use disjoint
masks. Lucky Chant's script OR preserves Tailwind.

Actual allocation clears the entire context; Init, turn reset, switch, faint
and Transform preserve side words. Whole-context copy includes them, and a
freed/new context starts inactive. No extra reset or sidecar was added. The
full context header is byte-identical to the accepted baseline. ARM-target
compilation checks 32-bit pointers, eight-byte side words, their adjacency to
side data, eight-byte side data and the unchanged 56-byte MoveEffectData.
Host pointer sizes are not used as evidence of ARM layout.

## Focused verification and limits

The initial actual-C RED compiled across all eight flag combinations. Each of
the four battle-on combinations reported `duration: actual 3 expected 4`.
The second regression exposed raw `0xB00` subtraction producing `0xA00` rather
than canonical `0x300`. All battle-off combinations passed. RED evidence is
`.local-tools/validation/tailwind-red.log` (exit 1, two methods/eight expected
modern subtest failures). Separate resource/routing RED logs record the missing
owner before integration.

The focused host methods extract real C functions with
`test_game_logic.function_source`, and retain the real Tailwind controller case,
iterator, expiry body and resume behavior inside a small SDK-edge fixture.
They cover all eight flags, all 4,096 combinations of other allocated bits,
each/all high bits 15–31, all eight storage patterns, setter values 0–255,
Toxic Spikes layers 0/1/2, Lucky Chant 0/1/5/7, all battler slots, independent
sides and malformed/orphan states. Speed checks cover both operands,
singles/doubles, 100→200 versus 150, other-side timers, Trick Room,
paralysis/Quick Feet, raw positive/inverse AI, named comparisons/order loading
and actual Gyro Ball power. Fixtures avoid tied speeds to verify zero RNG
calls; side-condition reads preserve the words. Actual Snatch selection and
archived script 146 resolve the attacker before the original cast executes.

All eight message pipelines use real Fairy, Pokédex, ability, Simple, Snow,
Soul Dew, Tailwind and move-resource owners, with script compiler edges
isolated. Neighboring routing tests were updated without weakening owners.
Battle-off controller tokens match accepted b385 under all four types/moves
pairs after preprocessing; the speed, command, AI, context header and original
public side-condition definitions are unchanged.

ASan/UBSan uses `ASAN_OPTIONS=detect_leaks=0` because macOS LeakSanitizer is
unsupported. No leak-detection claim is made. The new actual Snatch extraction
exposed an existing `MOVE_STATUS_NO_MORE_WORK=(1 << 31)` signed-shift issue.
Only that Snatch host fixture normalizes the literal to `(1u << 31)` and asserts
its exact `0x80000000u` pattern. Production stays unchanged, all sanitizers stay
enabled, and this does not claim to sanitize the original signed literal.
The failed run is retained as
`tailwind-sanitizers-legacy-signed-flag.log` (exit 1, 11 methods/eight failures).

Final focused command results are recorded below and in
`.local-tools/validation/tailwind-frozen-hashes.json`:

| Command (from repository root) | Result |
| --- | --- |
| `PYTHONPATH=tools/qol python3 -m unittest test_modern_tailwind.TailwindNativeTests test_modern_tailwind.TailwindResourceTests -v` | exit 0; 17 methods; 36.510 seconds |
| `ASAN_OPTIONS=detect_leaks=0 UBSAN_OPTIONS=halt_on_error=1 TAILWIND_SANITIZE=1 PYTHONPATH=tools/qol python3 -m unittest test_modern_tailwind.TailwindNativeTests -v` | exit 0; 11 methods; 23.028 seconds |
| `PYTHONPATH=tools/qol python3 -m unittest test_modern_tailwind.TailwindSdkTests -v` | exit 0; 2 methods; 25.212 seconds |
| Nine affected ability/absorption/status/weather/next14/Snow/moves/Soul Dew routing methods | exit 0; 9 methods; 11.225 seconds |
| `git diff --check` | exit 0 |

The SDK gate verifies original member 160 byte parity and the sole changed word
17 (`0x300`→`0xB00`) in an unchanged 96-byte script, preserved archives and
actual-C VM compare/update/failure/aliases. Archived effect 225 executes through
the actual move-status route 121→160; expiry runs 233. Cast, failed/expired
recast and the resolved Snatch side are checked across the eight host flags.
Presentation/Call edges are stubs in this VM gate.

These are focused host and script SDK results. No full eight-mode ROM/native
rebuild matrix has been run or claimed. Root owns fresh specification and
quality reviews, the complete affected/full host/SDK suite, a matching
all-three-enabled SDK/native build, native modern-four versus accepted-legacy-
three duration/speed controls, summary UI and frozen save/source/artifact hash
acceptance. Those integration gates are pending at this source release. No
standard build, app install, staging, commit or push was performed by this
worker. The installed app, real ROM/save and other ignored artifacts remain
untouched.


## Root integration acceptance

Fresh specification review passed17 guarded host/resource methods in31.108s.
Fresh quality review passed17 in30.827s plus9 routing checks in10.785s and an
additional actual BtlCmd_CalcGyroBallPower eight-flag check in1.846s. All frozen
source/evidence hashes matched. The matching all-three-enabled SDK ROM,
resources, layout and native build passed. Built resources retain899 move
members/scripts,304 subscripts,284 effects,830 message banks,243 ability rows
and1285 battle messages. Original160 remains96 bytes with only operand word17
changed300→B00;749/366 says four turns and Snow/Soul Dew/Sharpness remain intact.

The first broad run exposed Me First's historical whole-controller source
equality guard rejecting this intentional field-timer change. That run was
interrupted with exit130 and retained as `tailwind-full-suite-first-interrupted.log`;
it is not passing evidence. The isolated failure was reproduced before changing
only that test: its75 original function inventory now permits exactly two
private Tailwind helpers, protecting74 byte-identical bodies while excluding
the field-timer owner. Column-zero function boundaries accommodate existing
preprocessor arms. File-scope text is outside this narrowed guard; public ABI,
worker, command, trainer AI and opponent guards remain. Fresh independent spec
and quality checks passed this correction and rejected5/8 in-memory mutations.
Runtime source and tested artifacts did not change. The final complete
**338-test host/SDK suite passed in861.705s without failures/errors/skips**
(`tailwind-full-suite.log`).

Fresh matched-build native fixtures passed five sequential snapshot-restored
turns: end-of-turn flags300/200/100/0/0 and effective Speed200/200/200/100/100
versus150. The accepted three-turn control already drops to100 after turn3;
modern Tailwind therefore preserves the fourth turn's ordering. Normal actions
consume15/30/45/60/75 RNG calls from seed12, retaining the control's first four
final states. Failed active recast consumes PP but does not refresh the timer.
A staggered-side fixture retains two Spikes/Toxic Spikes layers, independently
expires the foe's Tailwind and decrements Lucky Chant5/1 to4/0. All seven
comparisons matched every ARM9 instruction across12100 frames, with zero
fallbacks, guard failures or evictions (`tailwind-native-green-proof.json`).
These are controlled private-save/RAM fixtures, not natural stat claims. The
pre-residualB00 start is proven by built binary/SDK VM, not a native-frame capture.

Root accepted the fresh five-line Summary description showing “for four turns”
without clipping, alongside the previous three-turn control. Fourteen validation
saves, all tested source/test and three artifact hashes, plus the installed
ROM/runtime/launcher/current real save/config/clean ROM guard matched. Only
acceptance documentation changes follow those checks. This source milestone
does not implement Wind Rider, Gas or dynamic mid-turn resorting and leaves
the installed four-QoL game unchanged while the broader Gen IX work continues.
