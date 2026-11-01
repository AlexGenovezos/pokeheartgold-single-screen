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

#endif
