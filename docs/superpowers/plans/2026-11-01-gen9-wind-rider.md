# Wind Rider and selective Shiftry assignment

This bounded Gen IX change adds internal ability241 Wind Rider, then assigns
Shiftry's second standard slot after the attack, entry/gain and Tailwind-start
mechanics passed their focused C and genuine SDK gates. The accepted prerequisite
is Tailwind commit `103d88b4d396554aa9dbde1cd914e7d1730003e0`.

The reference pins are expansion `c460a8661dfa0598ae25d42a968c690ecbf489c6`
and Pokémon Showdown `82f129e0b847bf23395d552f9bb48eb82e53a0ec`
(`onStart`, `onTryHit`, `onSideConditionStart`). This adopts selected Gen IX
behavior. It does not claim complete Gen IX rules or Champions rules.

## Mechanics

`Qol_IsWindMove` recognizes original IDs16,18,59,177,196,201,239,257,314,366.
With modern moves enabled it also recognizes internal575 Petal Blizzard and587
Fairy Wind. This repository's later IDs include its three post-IV placeholders.
Razor Wind13, Silver Wind318, Ominous Wind466, unsupported Hurricane545, all
other unsupported IDs and65535 are excluded. Wind classification is independent
of modern battle and existing MoveTbl flags. The absorption predicate additionally
requires move support and excludes Sandstorm201 and Tailwind366.

A living distinct Wind Rider target absorbs eligible attacks before accuracy,
without accuracy RNG or Micle consumption. The native following effect phase
still enforces Protect/Detect and hidden states. Only sole type immunity can be
removed by the existing script182 exception; composite failures remain intact.
The ordinary immunity controller's NO_MORE_WORK flag prevents the absorbed
current target's damage, secondary effects and Whirlwind switch. Wind does not
redirect attacks. Each spread target resolves independently; allies can absorb.
Mold Breaker bypasses attack immunity and Gastro Acid's active-ability getter
suppresses it. Eligibility precedes the mutating Mold Breaker query.

The single original182 source pass branches Wind Rider to Attack, while retaining
Motor Drive's Speed and Lightning Rod/Storm Drain's Sp. Atk paths, timing, message622
and capped638 response. Actual native UpdateMonData applies and clamps the boost,
including the absorber-to-Simple transition test. Once activated, the self boost
does not inherit an opposing current attacker's Mold Breaker or Shield Dust.

Entry consumes a living raw241 holder's native sendOutFlag once, including when
suppressed, capped or without Tailwind. Active Wind Rider under its own Tailwind
gets one actual Attack stage, silently skipping the cap. Native setter changes
into241 reset that latch only when the raw ability actually changes; no-op241
writes and AI knowledge revelation do not reset it. Trace187, Role Play135,
Skill Swap143, Worry Seed167 and Transform retain their original commands and
entry-scan routes. Physical population and Transform keep their native latch
resets. Expiry does not reset the entry latch. A genuine later own-side Tailwind
start is a separate event and can boost a consumed entrant again.

## ARM ownership and script continuation

Native BattleContext, BattleMon, MoveTbl, save structures and packets are unchanged.
A one-entry ARM overlay-BSS registry stores `{BattleContext *owner, state *}`;
the88-byte private payload is separately allocated from HEAP_ID_BATTLE. ARM-target
checks prove four-byte pointers, an eight-byte registry and the payload offsets.
The registry has no host/frontend cache and no lazy AI/getter allocation.

The capacity audit reconfirmed one New caller, BattleSystem_InitFromSetup; its
only caller is Battle_PartyPreviewInit. Battle_Run owns one battle overlay manager
and its0xB0000 battle heap across preview, versus and main. Battle_BattleExit is
the only Delete caller, before heap destruction. No assembly or hypothetical AI
allocation/clone exists. The controller, util, command, main and battle-run units
share OVY_12. Future concurrent contexts must deliberately review capacity;
a second owner asserts and never replaces the existing owner.

New publishes a fully byte-zeroed heap payload after native context zeroing and
before Init. Reset asserts idle/no pending/no saved presentation before clearing
transients; it preserves entry latches and Tailwind. Delete unregisters before
clearing/freeing the payload and before freeing the context. Missing/deleted
owners, duplicate acquisition, allocation failure and active reset reject safely.
One hundred real New/Init/Delete battles verify300 allocations and300 matching
frees across context, item data and Wind payload. This is ownership-path evidence,
not a leak-detector claim.

The native UpdateVar hook captures a previous value only for either side word.
It queues only the original subscript160 FLAG_ON into the resolved attacker's
side condition, transitioning from no public Tailwind presence to presence.
It asserts canonicalB00. Snatch therefore uses its resolved attacker. Copies,
UpdateVar2 GET, Guard Spec, timer ticks, failed recasts and no-op ORs do not queue.
The existing160 resource owner remains the sole source transform.

The queue validates and captures native turnOrder without sorting or RNG, up to
two living active same-side recipients and their selected-party identities.
Recipients are consumed before stage mutation or presentation. Dispatch rechecks
life, active ability, identity, side and Tailwind. A second queue cannot merge or
overwrite work. Snapshot simulation verifies deterministic continuation without
replaying an applied boost.

At completed160, the scheduler saves exactly battlerIdTemp, battlerIdStatChange,
msgTemp and waitCounter, plus verification-only copies of the native stack arrays
and depth. Each recipient gets waitCounter0 and presentation304. Actual animation,
message formatting and EmitPrintMessage packet construction were executed; their
only semantic presentation scratch is that four-field tuple. AI ability revelation
is legitimate and retained. Script progress, battleContinueFlag and emitted packet
state are legitimate VM flow. All other semantic scratch and Competitive pending
state remain intact. A corrupted saved stack asserts and holds End without popping
or discarding the active payload.

Presentation304 is56 bytes: animation, Wait, message622, Wait, WaitButton30, End.
It contains no Call, attack message or stat command. ReadBattleScriptFromNarc
replaces completed160/304 without pushing another frame. Draining restores the
tuple and performs exactly the original End/Return, at native depths0 through4.
Competitive12→298 remains independent before and after Wind.

The native VM drains these tail replacements synchronously. QUEUED before the
first apply and the transition between recipients need not be observable at an
emulator frame boundary. Host/SDK execution proves those exact transitions.
Root native acceptance must restore every reachable yielding presentation phase;
no artificial yield was added to make a test state visible.

## Prediction, resources and assignment

Preview, CalcTypeEffectivenessFlags and the actual BattleSystem_ApplyTypeEffectiveness
all recognize Wind immunity. Damaging preview is0; status Whirlwind retains-1.
Flags use the supplied known/guessed abilities, including party/switch predictions,
and type overrides do not erase a wind property. Actual TrainerAI_CalcDamage and
an actual switching caller execute these paths. Wind adds no RNG, knowledge,
announcement, allocation, pending-event or stage writes. The legacy AI damage
function's existing IGNORE_TYPE_EFFECTIVENESS scratch clear is explicitly tested;
this does not claim that all legacy AI work was already byte-pure. Its unchanged
intrinsic damage formula is separately protected by the existing formula tests.

All old exact299 owners remain in their original order. Optional moves append
299..303 first; Wind appends304 last. Battle-only fills299..303 with five End224
words. Thus battle-on is305 members, moves-only304, and base/types-only297.
Original12's source SHA256
`ba9ac6363a1fbff29b678ddd7189f4245bf4b894c6fcdba8d3947b8e62125336`
and genuine assembly parity are checked before304 compilation. Original182 has
its independent guarded parity pass before transformation; later Simple still
owns its existing runtime arithmetic. All eight actual pipeline combinations
preserve NARC names, counts, keys, old owner order and reserved members. Test-only
assembly caching fingerprints macro/constants/tool inputs, source and output hashes;
every cache miss uses the genuine serial SDK assembler.

Support241 is modern-battle-only. Shiftry275 changes `[Chlorophyll34, Early Bird48]`
to `[Chlorophyll34, Wind Rider241]`. Save reads adapt only form0, stored48, odd
original PID; even48, stored34, all explicit custom bytes, existing241, forms1..31
and other species retain their explicit choices. Native create/update ability
selection uses the standard pair. Actual encrypted getters, lock/checksum logic,
constructors and block permutations verify byte-identical reads across all256
stored bytes, both parities and32 forms.

Sparse banks720/721/722 keep243 rows, their original source/encoded guards and
keys7280/50258/26692. Row241 is Wind Rider / WIND RIDER /
“Wind moves and Tailwind\nraise Attack. Blocks wind.” Font widths are52/58 pixels
for names and121/140 for description lines, below149. Sharpness242 remains intact;
240 stays unsupported. NUM_ABILITIES remains123. The move universe remains72
modern moves and336 learnset rows across237 species.

## Verification and remaining acceptance

Semantic RED evidence covers missing Gust immunity, missing Tailwind Attack gain,
actual AI type-application damage40 instead of0, absent182 Attack branch,
299 instead of305 resources, unsupported assignment241 and the forced-stack-pop
regression. Ignored validation logs retain those failures and focused results.

Final focused gates passed:

- Guarded host:95 tests in95.254s, zero failures/errors/skips and zero SDK entry
  attempts. Both SDK entry points are forbidden before importing any test module;
  mixed test classes use an explicit method allowlist.
- Serial ASan/UBSan plus genuine SDK:26 tests in506.215s, zero failures/errors/skips.
  All52 unique pipeline sources were freshly assembled in a new final cache;
  original12/182/160 parity and304's exact VM profile were also freshly checked.
- Focused genuine SDK C:all five changed C units compiled with all three flags
  disabled and enabled,10 temporary objects in90.757s, all exit0. Every input
  source hash is recorded. No standard build or link occurred.
- `git diff --check` passed. The capacity audit searched all production src,
  include and asm paths and reconfirmed the unique lifetime described above.

The worker's exact commands, counts, durations, sanitizer limits and frozen input
hashes are recorded in `.local-tools/validation/wind-rider-frozen-hashes.json`.
The earlier overlapping SDK run and its mixed-class fixture log are explicitly
non-final; final SDK provenance uses a separate fresh cache and one serial runner.
ASan/UBSan runs keep both sanitizers active. On macOS detect_leaks=0 is explicit;
LSan coverage is not claimed. The host-only normalization of the legacy signed
NO_MORE_WORK bit31 macro asserts its identical0x80000000 pattern; production's
macro is untouched. SDK C objects use disposable output directories, with no
standard build or link.

Root still owns fresh specification then quality reviews, the complete host/SDK
suite, a matching paired SDK/native ROM, ELF/map/layout validation, native registry
BSS and heap snapshot coverage, summary/singles and genuine doubles proofs,
reachable queue restores, hash acceptance and any later commit/push. No install,
standard build, PR, staging, commit or push is part of this worker change. The
installed four-QoL app, REAL ROM and REAL save remain separate and unchanged.

Neutralizing Gas240, Gas recovery/restarts, dynamic mid-turn resorting and
unsupported wind moves remain future work. Gas recovery must explicitly restart
an active Wind entry once under Tailwind when that lifecycle is implemented;
there is no Gas provider or restart state here.


## Root integration acceptance

Fresh specification review passed 60 guarded host tests in 79.678 s and 15
additional actual-C edge cases. Fresh quality review passed 21 guarded host
tests in 25.253 s and an independent ASan/UBSan program covering 48 order/side
combinations,12 malformed orders and registry lifetime checks. Both reviews
retained all 176 frozen hashes; neither entered the SDK lane.

The matching all-three-modern-flags SDK/resource/layout/native build passed.
The initial 364-test host/SDK run reported 21 compilation subtest failures across
nine methods. Six test-only fixture fixes add missing dependency declarations
and retain fail-closed Wind boundaries without changing production or original
assertions. Fresh specification and quality reviews passed those fixes. All 91
affected checks passed in 358.472 s, and an independent guarded run passed
the three additional Sharpness consumers in 13.111 s. Combined with the initial
355 passing methods, these runs cover the complete 364-case collection; a single
fully green 364-case rerun is not claimed. The Wind resource matrix reused 52
exact-profile cached genuine assemblies; the final focused run assembled all 52
freshly.
The new linked eight-byte registry is inside OVY_12's SDK-declared BSS range;
the private heap payload's linked DWARF size is 88 bytes. No native battle/save/
packet structure changed.

Seven genuine cold-boot trainer-doubles cases verify friendly Tailwind boosts
both allies, Gust absorption, opposing Mold Breaker bypass, friendly Tailwind
despite opposing Mold Breaker, per-target Petal Blizzard absorption while the
adjacent non-Wind foe is hit, no player boosts from opposing Tailwind, and
Whirlwind absorption preserving active party identities. Separate battle-RAM
fixtures verify a capped holder does not block its ally, Gastro Acid suppression,
and a failed recast does not repeat boosts or refresh Tailwind.

Native snapshots at first-applied/pending-second and second-applied/pending-zero
preserve the eight-byte ARM BSS registry and 88-byte heap payload. Restoring each
yielding phase and the final drain produces byte-identical full 4 MiB ARM RAM at
the accepted endpoint, without replaying a boost. Initial QUEUED and the
inter-recipient dispatch are synchronous VM phases; they retain actual-C/SDK
coverage rather than a claimed native frame-boundary capture.

All 13 stable comparisons matched every ARM 9 instruction over 46400 frames, with
zero interpreter fallbacks, guard failures or evictions. The separate 2500-frame
cold boot also matched every ARM 9 instruction, with 1.24% fallback and 42 guards/
evictions during loading; those are excluded from the zero-metric claim. Fresh
single-battle constructors confirm odd 241, even 34 and explicit even 48. Wind
Rider's Summary name/two-line description and the two-line Attack-rise message
fit cleanly. Native ability-gain routes are not claimed here; the focused genuine
SDK VM tests cover those routes.

Frozen production,172 unchanged original frozen files, six reviewed fixture fixes,
tested artifacts, six private validation saves and
the installed game/current real-save/config guards matched. Ignored evidence
is recorded in wind-rider-native-green-proof.json and wind-rider-regression-acceptance.json.
This is a source-only development milestone: no full Gen IX install, no Gas
implementation, no mid-turn sorting and no Linux/Steam Deck execution claim.
The installed four-QoL app remains separate and unchanged.
