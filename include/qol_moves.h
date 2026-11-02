#ifndef POKEHEARTGOLD_QOL_MOVES_H
#define POKEHEARTGOLD_QOL_MOVES_H

#include "constants/moves.h"
#include "constants/qol_moves.h"
#include "move.h"
#include "qol_config.h"

BOOL Qol_IsSupportedMove(u16 moveId);
const MoveTbl *Qol_GetExtendedMoveData(u16 moveId);
const MoveTbl *Qol_GetBattleMoveData(const MoveTbl *legacy, u16 moveId);
u16 Qol_GetMoveAnimation(u16 moveId);
u16 Qol_GetMetronomeMove(u16 index);
BOOL Qol_IsSoundMove(u16 moveId);
BOOL Qol_IsWindMove(u16 moveId);
BOOL Qol_WindMoveCanBeAbsorbed(u16 moveId);
BOOL Qol_IsSlicingMove(u16 moveId);
BOOL Qol_MoveBypassesSubstitute(u16 moveId);

#if QOL_MODERN_MOVES
#define BATTLE_MOVE_DATA(ctx, moveId) (*Qol_GetBattleMoveData((ctx)->trainerAIData.moveData, (moveId)))
#define QOL_METRONOME_MOVE_COUNT (NUM_MOVES + QOL_EXTENDED_MOVE_COUNT)
#else
// Preserve legacy indexing, code generation and RNG behavior when disabled.
#define BATTLE_MOVE_DATA(ctx, moveId) ((ctx)->trainerAIData.moveData[(moveId)])
#define QOL_METRONOME_MOVE_COUNT NUM_MOVES
#endif

#endif
