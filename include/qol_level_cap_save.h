#ifndef POKEHEARTGOLD_QOL_LEVEL_CAP_SAVE_H
#define POKEHEARTGOLD_QOL_LEVEL_CAP_SAVE_H

#include "daycare.h"
#include "pokemon_types_def.h"
#include "qol_level_caps.h"
#include "save.h"

QolLevelCap Qol_LevelCapForSave(SaveData *saveData);
BOOL Qol_LevelCapEnabledForSave(SaveData *saveData);
void Qol_LevelCapSetEnabledForSave(SaveData *saveData, BOOL enabled);
u32 Qol_LevelCapLimitPlayerExp(SaveData *saveData, u16 species, u32 oldExp, u32 requestedExp);
BOOL Qol_LevelCapCanUseRareCandy(SaveData *saveData, Pokemon *mon);
u8 Qol_LevelCapAdvanceDaycarePhase(SaveData *saveData, DaycareMon *second);
void Qol_LevelCapResetDaycarePhase(SaveData *saveData);

#endif
