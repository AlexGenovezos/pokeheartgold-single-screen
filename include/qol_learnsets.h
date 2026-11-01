#ifndef POKEHEARTGOLD_QOL_LEARNSETS_H
#define POKEHEARTGOLD_QOL_LEARNSETS_H

#include "pokemon.h"

// Private working data only: the ROM's packed u16 records and saved moves stay
// unchanged. Allow every legacy slot, five additions, and an explicit sentinel.
#define QOL_LEVEL_UP_ADDITIONS_MAX 5
#define QOL_LEVEL_UP_LEARNSET_CAPACITY (MAX_LEARNED_MOVES + QOL_LEVEL_UP_ADDITIONS_MAX + 1)

typedef struct QolLevelUpMove {
    u16 move;
    u16 level;
} QolLevelUpMove;

// dest has QOL_LEVEL_UP_LEARNSET_CAPACITY records; count excludes the sentinel.
int Qol_LoadLevelUpLearnset(int species, int form, QolLevelUpMove *dest);
u32 Qol_MonTryLearnMove(Pokemon *mon, int *last_i, u16 *newMove, BOOL afterEvolution);
u32 Qol_MonTryLearnMoveAfterEvolution(Pokemon *mon, int *last_i, u16 *newMove);

#endif
