#include "qol_moves.h"

#include "constants/pokemon.h"

// Neither MoveTbl nor the legacy embedded table may grow for later IDs.
typedef char Qol_MoveTblSizeMustRemain16[(sizeof(MoveTbl) == 16) ? 1 : -1];
typedef char Qol_LegacyMoveCountMustRemain468[(NUM_MOVES + 1 == 468) ? 1 : -1];

#if QOL_MODERN_MOVES
static const u16 sExtendedMoveIds[] = {
#define QOL_EXTRA_MOVE(id, effect, category, power, type, accuracy, pp, chance, range, priority, flags, animation) id,
#include "data/qol_move_entries.inc"
#undef QOL_EXTRA_MOVE
};

// Native bit 0x20 means King's Rock eligibility; hg-engine uses it instead
// for unimplemented moves. Entries translate that bit and keep native drain's
// exclusion. Contest bytes have no imported Gen IX counterpart and stay zero.
static const MoveTbl sExtendedMoveData[] = {
#define QOL_EXTRA_MOVE(id, effect, category, power, type, accuracy, pp, chance, range, priority, flags, animation) \
    { effect, category, power, type, accuracy, pp, chance, range, priority, flags, { 0, 0, 0 } },
#include "data/qol_move_entries.inc"
#undef QOL_EXTRA_MOVE
};
#endif

const MoveTbl *Qol_GetExtendedMoveData(u16 moveId) {
#if QOL_MODERN_MOVES
    for (int i = 0; i < QOL_EXTENDED_MOVE_COUNT; i++) {
        if (moveId == sExtendedMoveIds[i]) {
            return &sExtendedMoveData[i];
        }
    }
#endif
    return NULL;
}

BOOL Qol_IsSupportedMove(u16 moveId) {
    return moveId <= NUM_MOVES || Qol_GetExtendedMoveData(moveId) != NULL;
}

const MoveTbl *Qol_GetBattleMoveData(const MoveTbl *legacy, u16 moveId) {
    const MoveTbl *extended;
    if (moveId <= NUM_MOVES) {
        return &legacy[moveId];
    }
    extended = Qol_GetExtendedMoveData(moveId);
    return extended != NULL ? extended : &legacy[MOVE_NONE];
}

u16 Qol_GetMoveAnimation(u16 moveId) {
#if QOL_MODERN_MOVES
    switch (moveId) {
#define QOL_EXTRA_MOVE(id, effect, category, power, type, accuracy, pp, chance, range, priority, flags, animation) case id: return animation;
#include "data/qol_move_entries.inc"
#undef QOL_EXTRA_MOVE
    }
#endif
    return moveId;
}

u16 Qol_GetMetronomeMove(u16 index) {
    if (index < NUM_MOVES) {
        return index + 1;
    }
#if QOL_MODERN_MOVES
    if (index < QOL_METRONOME_MOVE_COUNT) {
        return sExtendedMoveIds[index - NUM_MOVES];
    }
#endif
    return MOVE_NONE;
}

BOOL Qol_IsSoundMove(u16 moveId) {
    switch (moveId) {
    case MOVE_GROWL:
    case MOVE_ROAR:
    case MOVE_SING:
    case MOVE_SUPERSONIC:
    case MOVE_SCREECH:
    case MOVE_SNORE:
    case MOVE_UPROAR:
    case MOVE_METAL_SOUND:
    case MOVE_GRASS_WHISTLE:
    case MOVE_HYPER_VOICE:
    case MOVE_BUG_BUZZ:
    case MOVE_CHATTER:
#if QOL_MODERN_MOVES
    case MOVE_DISARMING_VOICE:
    case MOVE_BOOMBURST:
    case MOVE_SNARL:
#endif
        return TRUE;
    }
    return FALSE;
}

BOOL Qol_MoveBypassesSubstitute(u16 moveId) {
#if QOL_MODERN_MOVES
    // Play Nice is a visual status move, not sound, but ignores Substitute.
    if (moveId == MOVE_PLAY_NICE) {
        return TRUE;
    }
#endif
#if QOL_MODERN_BATTLE || QOL_MODERN_MOVES
    return Qol_IsSoundMove(moveId);
#else
    return FALSE;
#endif
}
