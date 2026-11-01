#ifndef POKEHEARTGOLD_QOL_FIELD_MOVES_H
#define POKEHEARTGOLD_QOL_FIELD_MOVES_H

#include "global.h"
#include "save.h"
#include "qol_config.h"

int Qol_HmIndex(u16 move);
BOOL Qol_HmIsUnlocked(SaveData *save, u16 move);
u8 Qol_GetHmFieldActor(SaveData *save, u16 move);
BOOL Qol_IsHmFieldScript(u16 script, u16 move);

#endif
