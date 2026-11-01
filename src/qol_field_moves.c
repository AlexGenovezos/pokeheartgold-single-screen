#include "qol_field_moves.h"

#include "constants/badge.h"
#include "constants/items.h"
#include "constants/moves.h"
#include "constants/std_script.h"
#include "bag.h"
#include "party.h"
#include "player_data.h"
#include "pokemon.h"

int Qol_HmIndex(u16 move) {
    switch (move) {
    case MOVE_CUT: return 0;
    case MOVE_FLY: return 1;
    case MOVE_SURF: return 2;
    case MOVE_STRENGTH: return 3;
    case MOVE_WHIRLPOOL: return 4;
    case MOVE_ROCK_SMASH: return 5;
    case MOVE_WATERFALL: return 6;
    case MOVE_ROCK_CLIMB: return 7;
    default: return -1;
    }
}

BOOL Qol_HmIsUnlocked(SaveData *save, u16 move) {
    static const u8 badges[] = {
        BADGE_HIVE, BADGE_STORM, BADGE_FOG, BADGE_PLAIN,
        BADGE_GLACIER, BADGE_ZEPHYR, BADGE_RISING, BADGE_EARTH
    };
    int index = Qol_HmIndex(move);
    if (index < 0 || !PlayerProfile_TestBadgeFlag(Save_PlayerData_GetProfile(save), badges[index])) {
        return FALSE;
    }
    // Waterfall checks run every field input update. The known HM pocket avoids
    // Bag_HasItem's item-data NARC read on every frame.
    ItemSlot *slots = Bag_GetPocketSlotN(Save_Bag_Get(save), POCKET_TMHMS, 0);
    for (int i = 0; i < NUM_BAG_TMS_HMS; i++) {
        if (slots[i].id == ITEM_HM01 + index && slots[i].quantity != 0) {
            return TRUE;
        }
    }
    return FALSE;
}

// The actor supplies the existing nickname/cut-in animation. Its moves are untouched.
u8 Qol_GetHmFieldActor(SaveData *save, u16 move) {
    if (Qol_HmIsUnlocked(save, move)) {
        Party *party = SaveArray_Party_Get(save);
        u8 count = Party_GetCount(party);
        for (u8 i = 0; i < count; i++) {
            if (!GetMonData(Party_GetMonByIndex(party, i), MON_DATA_IS_EGG, NULL)) {
                return i;
            }
        }
    }
    return 0xFF;
}

// Only these standard interactions request an HM animation actor. Other scripts
// asking which Pokemon knows a move must continue to get a truthful answer.
BOOL Qol_IsHmFieldScript(u16 script, u16 move) {
    switch (script) {
    case std_field_cut: return move == MOVE_CUT;
    case std_field_rock_smash: return move == MOVE_ROCK_SMASH;
    case std_field_strength: return move == MOVE_STRENGTH;
    case std_field_rock_climb: return move == MOVE_ROCK_CLIMB;
    case std_field_surf: return move == MOVE_SURF;
    case std_field_waterfall: return move == MOVE_WATERFALL;
    case std_field_whirlpool: return move == MOVE_WHIRLPOOL;
    default: return FALSE;
    }
}
