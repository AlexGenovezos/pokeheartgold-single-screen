#ifndef POKEHEARTGOLD_BATTLE_QOL_WIND_EVENTS_H
#define POKEHEARTGOLD_BATTLE_QOL_WIND_EVENTS_H

#include "global.h"
#include "qol_config.h"

struct BattleSystem;
struct BattleContext;

#if QOL_MODERN_BATTLE
void Qol_WindEventsNew(struct BattleContext *ctx);
void Qol_WindEventsDelete(struct BattleContext *ctx);
void Qol_WindEventsReset(struct BattleContext *ctx);
void Qol_QueueTailwindStart(struct BattleSystem *bs, struct BattleContext *ctx, int side);
BOOL Qol_BeginWindRiderEntry(struct BattleSystem *bs, struct BattleContext *ctx, int battler);
BOOL Qol_ContinueWindRider(struct BattleSystem *bs, struct BattleContext *ctx);
#endif

#endif
