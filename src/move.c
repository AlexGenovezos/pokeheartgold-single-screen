#include "move.h"

#include "global.h"

#include "constants/moves.h"
#include "constants/pokemon.h"

#include "filesystem.h"
#include "qol_config.h"
#include "qol_moves.h"

#if QOL_MODERN_TYPES
// Existing move IDs/types follow hg-engine data/Moves.c at 61b510cf.
static void Qol_ApplyModernMoveType(u16 moveId, MoveTbl *moveTbl) {
    switch (moveId) {
    case MOVE_CHARM:
    case MOVE_SWEET_KISS:
    case MOVE_MOONLIGHT:
        moveTbl->type = TYPE_FAIRY;
        break;
    case MOVE_CURSE:
        moveTbl->type = TYPE_GHOST;
        break;
    }
}
#endif

void LoadMoveTbl(MoveTbl *dest) {
    ReadFromNarcMemberByIdPair(dest, NARC_poketool_waza_waza_tbl, 0, 0, (NUM_MOVES + 1) * sizeof(MoveTbl));
#if QOL_MODERN_TYPES
    for (int moveId = 0; moveId <= NUM_MOVES; moveId++) {
        Qol_ApplyModernMoveType(moveId, &dest[moveId]);
    }
#endif
}

u32 GetMoveAttr(u16 moveId, MoveAttr attrno) {
    MoveTbl movedata;
    LoadMoveEntry(moveId, &movedata);
    return GetMoveTblAttr(&movedata, attrno);
}

u8 GetMoveMaxPP(u16 moveId, u8 ppUps) {
    u8 pp;
    if (ppUps > 3) {
        ppUps = 3;
    }
    pp = GetMoveAttr(moveId, MOVEATTR_PP);
    return pp + ((pp * 20 * ppUps) / 100);
}

u32 GetMoveTblAttr(const MoveTbl *moveTbl, MoveAttr attr) {
    switch (attr) {
    case MOVEATTR_EFFECT:
        return moveTbl->effect;
    case MOVEATTR_CLASS:
        return moveTbl->category;
    case MOVEATTR_POWER:
        return moveTbl->power;
    case MOVEATTR_TYPE:
        return moveTbl->type;
    case MOVEATTR_ACCURACY:
        return moveTbl->accuracy;
    case MOVEATTR_PP:
        return moveTbl->pp;
    case MOVEATTR_EFFECT_CHANCE:
        return moveTbl->effectChance;
    case MOVEATTR_RANGE:
        return moveTbl->range;
    case MOVEATTR_PRIORTY:
        return moveTbl->priority;
    case MOVEATTR_UNK9:
        return moveTbl->flags;
    case MOVEATTR_UNK10:
        return moveTbl->unkC;
    case MOVEATTR_CONTEST_TYPE:
        return moveTbl->contestType;
    default:
        return (u32)moveTbl;
    }
}

void LoadMoveEntry(u16 moveId, MoveTbl *moveTbl) {
#if QOL_MODERN_MOVES
    if (moveId > NUM_MOVES) {
        const MoveTbl *extended = Qol_GetExtendedMoveData(moveId);
        if (extended != NULL) {
            *moveTbl = *extended;
            return;
        }
        moveId = MOVE_NONE;
    }
#endif
    ReadWholeNarcMemberByIdPair(moveTbl, NARC_poketool_waza_waza_tbl, moveId);
#if QOL_MODERN_TYPES
    Qol_ApplyModernMoveType(moveId, moveTbl);
#endif
}
