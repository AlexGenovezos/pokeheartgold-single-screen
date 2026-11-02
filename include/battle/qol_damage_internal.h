#ifndef POKEHEARTGOLD_BATTLE_QOL_DAMAGE_INTERNAL_H
#define POKEHEARTGOLD_BATTLE_QOL_DAMAGE_INTERNAL_H

#include "battle/battle_util.h"

// Private formula provenance. Compatibility callers never acquire Me First.
typedef enum QolDamageOrigin {
    QOL_DAMAGE_COMPATIBILITY = 0,
    QOL_DAMAGE_ORDINARY_COMMAND = 1
} QolDamageOrigin;

BOOL Qol_IsMeFirstEligible(BOOL flag, int total, int count);
int Qol_CalcMoveDamageInternal(BattleSystem *battleSystem, BattleContext *ctx, u32 moveNo, u32 sideCondition, u32 fieldCondition, u16 power, u8 type, u8 battlerIdAttacker, u8 battlerIdTarget, u8 crit, QolDamageOrigin origin, BOOL meFirstEligible);

#endif
