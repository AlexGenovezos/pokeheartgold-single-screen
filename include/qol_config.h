#ifndef POKEHEARTGOLD_QOL_CONFIG_H
#define POKEHEARTGOLD_QOL_CONFIG_H

// Opt in explicitly so original game behavior remains the default.
#ifndef QOL_MODS
#define QOL_MODS 0
#endif
#ifndef QOL_REUSABLE_TMS
#define QOL_REUSABLE_TMS QOL_MODS
#endif
#ifndef QOL_INSTANT_TEXT
#define QOL_INSTANT_TEXT QOL_MODS
#endif
#ifndef QOL_HM_ACTIONS
#define QOL_HM_ACTIONS QOL_MODS
#endif
#ifndef QOL_EFFECTIVENESS
#define QOL_EFFECTIVENESS QOL_MODS
#endif
// An independently testable foundation; the current QoL build stays Gen IV.
#ifndef QOL_MODERN_TYPES
#define QOL_MODERN_TYPES 0
#endif

// Core modern arithmetic is opt-in independently of the installed QoL build.
#ifndef QOL_MODERN_BATTLE
#define QOL_MODERN_BATTLE 0
#endif

#endif
