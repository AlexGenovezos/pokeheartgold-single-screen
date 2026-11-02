#ifndef POKEHEARTGOLD_QOL_LEVEL_CAPS_H
#define POKEHEARTGOLD_QOL_LEVEL_CAPS_H

#include "global.h"

#define QOL_LEVEL_CAP_CONFIG_OFF 0x0000
#define QOL_LEVEL_CAP_CONFIG_ON  0xC701

enum {
    QOL_LEVEL_CAP_DEFEATED_WILL = 1 << 0,
    QOL_LEVEL_CAP_DEFEATED_KOGA = 1 << 1,
    QOL_LEVEL_CAP_DEFEATED_BRUNO = 1 << 2,
    QOL_LEVEL_CAP_DEFEATED_KAREN = 1 << 3
};

typedef struct QolLevelCap {
    u16 trainerId;
    u8 level;
} QolLevelCap;

// Inputs are individual badge bits and the four first-League attempt flags.
// The resolver also works while the option is Off, for displaying the next boss.
// TRAINER_NONE / MAX_LEVEL means retain the original level-100 growth rules.
QolLevelCap Qol_GetLevelCap(u16 badges, BOOL gameClear, u8 defeatedEliteFour);
BOOL Qol_LevelCapConfigEnabled(u16 value);
u16 Qol_LevelCapConfigValue(BOOL enabled);

// capExp is the native growth-table EXP needed to reach the selected ace level.
// Return only accepted new EXP; existing EXP is never rewritten or banked.
// Callers disable progression limiting for the final no-boss/MAX_LEVEL result
// and retain their ordinary level-100 bounds in both modes.
u32 Qol_LevelCapAllowedExp(BOOL enabled, u32 oldExp, u32 requestedExp, u32 capExp);

#endif
