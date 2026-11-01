#ifndef POKEHEARTGOLD_QOL_ABILITIES_H
#define POKEHEARTGOLD_QOL_ABILITIES_H

#include "global.h"
#include "pokemon_types_def.h"

BOOL Qol_IsSupportedAbility(u16 ability);
u8 Qol_GetStoredAbility(u16 species, u8 form, u8 ability);
void Qol_ApplyModernMonAbilities(int species, BASE_STATS *personal);

#endif
