# Optional level caps

Level caps start **Off**. Open the game’s Options menu, press **X** or touch **X: CAPS**, then choose Off or On. Confirm applies the change together with your other Options edits; Quit or B discards it. Save the game normally to keep the setting. X and the touch header work with every button mode, including L=A.

When enabled, the cap follows the lowest original ace level among the unbeaten Gym Leaders in the current region. Individual badges determine which leaders remain. Johto starts at Falkner’s level 13; Chuck uses 31 and Clair uses 41. Because Gym order is flexible, beating Jasmine before Pryce can leave a lower next cap. Existing Pokémon never lose levels or EXP when that happens.

After all eight Johto badges, the first League attempt advances through Will 42, Koga 44, Bruno 46, Karen 47 and Lance 50 as its victory flags are set. Starting another attempt before the first clear resets this progression. After the first League clear, the cap follows the remaining Kanto leaders, regardless of reset League flags. Once all Kanto badges are earned, ordinary level-100 growth rules apply.

The cap limits new battle EXP, field Rare Candy, Pokéwalker stroll EXP and daycare growth. Battle EVs still apply when EXP gain is zero. Rare Candy is usable one level below the cap and is rejected without consumption at the cap. A Pokéwalker level-up friendship bonus requires an actual accepted level-up; ordinary walking friendship still applies. Daycare egg rolls continue while growth is frozen, and its preview, withdrawal fee and returned EXP all use the accepted stored growth.

Captures, gifts, trades, imports and already higher-level Pokémon keep their existing levels and EXP. Daycare growth accumulated before enabling a lower cap also remains intact. Suppressed new EXP is discarded. Raising the cap or turning it Off permits new gains from that point; it does not release stored suppressed EXP.

## Save format

The feature reserves two existing, audited save-variable slots. It adds no save block, Pokémon field, Options field or persistent packet data.

| Variable | Format |
| --- | --- |
| `0x416F`, `VAR_QOL_LEVEL_CAP_CONFIG` | `0x0000` = Off; exact `0xC701` = On, schema 1. Every other value reads Off without automatic rewriting. |
| `0x416E`, `VAR_QOL_DAYCARE_BREEDING_PHASE` | `0xD100`–`0xD1FF` = schema 1 with the breeding clock in the low byte. Other values are uninitialized. |

The boss and cap are derived from story state and are never saved in these slots. Options preview and confirmation do not migrate the breeding clock. On the first capped daycare walk, an uninitialized clock migrates from the second parent’s existing growth-step low byte before the walk changes growth. A tagged clock continues after disabling caps because frozen growth no longer measures breeding time. Depositing a new second parent or withdrawing either parent resets an active clock.

Untouched Off saves retain their original breeding timing and uninitialized phase value. A build with `QOL_LEVEL_CAPS=0` performs no accesses to either reserved slot and uses the original producers. The names remain reserved in every build. `QOL_LEVEL_CAPS` defaults to `QOL_MODS` independently of modern type, battle and move switches; runtime default remains Off.

Original save sizes and checksums retain their normal ownership. An original ROM can still read the existing Pokémon and growth counters, but it derives breeding timing from growth steps rather than the independent tagged clock; downgrading therefore does not preserve the exact breeding phase after capped daycare use.

Use `scripts/build.sh` for builds so the tracked message preparer appends the ten owned cap labels to imported Options assets before header compilation. Support-disabled builds restore the exact stock 60-row bank. Instant text keeps its synthesized C label; stock rows 56–59 remain the final four window-frame labels. No original message dump or generated header is added to source control.
