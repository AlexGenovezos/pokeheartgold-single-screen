"""Execute HM unlock and caller logic without proprietary SDK dependencies."""
import unittest
import test_game_logic as game


class HmActionTests(unittest.TestCase):
    compile_run = game.GameLogicTests.compile_run
    def test_each_hm_requires_its_item_and_badge_and_a_valid_actor(self):
        declarations = r'''
#include <assert.h>
#include <stddef.h>
#include "constants/items.h"
#include "constants/moves.h"
#include "constants/badge.h"
#include "constants/std_script.h"
typedef unsigned char u8;
typedef unsigned short u16;
typedef int BOOL;
#define TRUE 1
#define FALSE 0
#define PARTY_SIZE 6
#define HEAP_ID_FIELD2 2
#define MON_DATA_IS_EGG 0
typedef struct { int egg; } Pokemon;
typedef struct { Pokemon mons[6]; int count; } Party;
typedef struct { u16 id, quantity; } ItemSlot;
typedef struct { ItemSlot slots[NUM_BAG_TMS_HMS]; } Bag;
typedef struct { unsigned badges; Bag bag; Party party; } SaveData;
int PlayerProfile_TestBadgeFlag(SaveData *save, int badge) { return !!(save->badges & (1u << badge)); }
SaveData *Save_PlayerData_GetProfile(SaveData *save) { return save; }
Bag *Save_Bag_Get(SaveData *save) { return &save->bag; }
int Bag_HasItem(Bag *bag, int item, int quantity, int heap) { assert(!"HM checks must not load item metadata every frame"); return 0; }
ItemSlot *Bag_GetPocketSlotN(Bag *bag, int pocket, int slot) { assert(pocket == POCKET_TMHMS); return &bag->slots[slot]; }
Party *SaveArray_Party_Get(SaveData *save) { return &save->party; }
int Party_GetCount(Party *party) { return party->count; }
Pokemon *Party_GetMonByIndex(Party *party, int slot) { assert(slot < party->count); return &party->mons[slot]; }
int GetMonData(Pokemon *mon, int field, void *unused) { return mon->egg; }
'''
        actual = "\n".join(game.function_source("src/qol_field_moves.c", name) for name in
                           ("Qol_HmIndex", "Qol_HmIsUnlocked", "Qol_GetHmFieldActor",
                            "Qol_IsHmFieldScript"))
        checks = r'''
int main(void) {
    const int moves[] = { MOVE_CUT, MOVE_FLY, MOVE_SURF, MOVE_STRENGTH,
                         MOVE_WHIRLPOOL, MOVE_ROCK_SMASH, MOVE_WATERFALL, MOVE_ROCK_CLIMB };
    const int badges[] = { BADGE_HIVE, BADGE_STORM, BADGE_FOG, BADGE_PLAIN,
                          BADGE_GLACIER, BADGE_ZEPHYR, BADGE_RISING, BADGE_EARTH };
    for (int i = 0; i < 8; i++) {
        for (int item = 0; item < 2; item++) {
            for (int badge = 0; badge < 2; badge++) {
                SaveData save = {0}; save.party.count = 2;
                save.party.mons[0].egg = 1;
                save.bag.slots[100].id = ITEM_HM01 + i;
                save.bag.slots[100].quantity = item;
                save.badges = badge ? (1u << badges[i]) : 0;
                assert(Qol_HmIndex(moves[i]) == i);
                assert(!!Qol_HmIsUnlocked(&save, moves[i]) == (item && badge));
                assert(Qol_GetHmFieldActor(&save, moves[i]) == (item && badge ? 1 : 0xff));
                save.party.mons[1].egg = 1;
                assert(Qol_GetHmFieldActor(&save, moves[i]) == 0xff);
                save.party.count = 0;
                assert(Qol_GetHmFieldActor(&save, moves[i]) == 0xff);
            }
        }
        SaveData save = {0}; save.party.count = 1;
        save.bag.slots[0].id = ITEM_HM01 + i;
        save.bag.slots[0].quantity = 1;
        save.badges = 1u << badges[(i + 1) % 8];
        assert(!Qol_HmIsUnlocked(&save, moves[i]));
    }
    SaveData save = {0}; save.badges = 0xffff;
    for (int i = 0; i < 8; i++) { save.bag.slots[i].id = ITEM_HM01 + i; save.bag.slots[i].quantity = 1; }
    assert(Qol_HmIndex(MOVE_HEADBUTT) == -1);
    assert(!Qol_HmIsUnlocked(&save, MOVE_HEADBUTT));
    const int scripts[] = {std_field_cut, std_field_rock_smash, std_field_strength,
                          std_field_rock_climb, std_field_surf, std_field_waterfall,
                          std_field_whirlpool};
    const int scriptMoves[] = {MOVE_CUT, MOVE_ROCK_SMASH, MOVE_STRENGTH,
                              MOVE_ROCK_CLIMB, MOVE_SURF, MOVE_WATERFALL, MOVE_WHIRLPOOL};
    for (int i = 0; i < 7; i++) {
        for (int j = 0; j < 7; j++)
            assert(!!Qol_IsHmFieldScript(scripts[i], scriptMoves[j]) == (i == j));
        assert(!Qol_IsHmFieldScript(42, scriptMoves[i]));
        assert(!Qol_IsHmFieldScript(std_field_headbutt, scriptMoves[i]));
    }
    return 0;
}
'''
        self.compile_run(declarations + actual + checks)

    def test_standard_scripts_use_an_actor_but_other_move_queries_stay_truthful(self):
        declarations = r'''
#include <assert.h>
#include <stddef.h>
#include "constants/moves.h"
#include "constants/std_script.h"
#include "constants/pokemon.h"
typedef unsigned char u8;
typedef unsigned short u16;
typedef int BOOL;
#define TRUE 1
#define FALSE 0
#define PARTY_SIZE 6
#define SCRIPTENV_ACTIVE_SCRIPT_NUMBER 8
typedef struct { int data[512]; } Pokemon;
typedef struct { Pokemon mons[6]; int count; } Party;
typedef struct { Party party; } SaveData;
typedef struct { SaveData *saveData; u16 script; } FieldSystem;
typedef struct { FieldSystem *fieldSystem; u16 result, move; } ScriptContext;
int actor;
u16 *ScriptGetVarPointer(ScriptContext *ctx) { return &ctx->result; }
u16 ScriptGetVar(ScriptContext *ctx) { return ctx->move; }
void *FieldSysGetAttrAddr(FieldSystem *fs, int attr) { return &fs->script; }
Party *SaveArray_Party_Get(SaveData *save) { return &save->party; }
int Party_GetCount(Party *party) { return party->count; }
Pokemon *Party_GetMonByIndex(Party *party, int index) { assert(index < party->count); return &party->mons[index]; }
int GetMonData(Pokemon *mon, int field, void *unused) { return mon->data[field]; }
u8 Qol_GetHmFieldActor(SaveData *save, u16 move) { return actor; }
'''
        actual = game.function_source("src/qol_field_moves.c", "Qol_IsHmFieldScript")
        actual += game.function_source("src/scrcmd_party.c", "ScrCmd_GetPartySlotWithMove")
        checks = r'''
int main(void) {
    SaveData save = {0}; save.party.count = 3;
    save.party.mons[0].data[MON_DATA_IS_EGG] = 1;
    save.party.mons[0].data[MON_DATA_MOVE1] = MOVE_SURF;
    save.party.mons[2].data[MON_DATA_MOVE4] = MOVE_SURF;
    FieldSystem fs = {&save, std_field_surf};
    ScriptContext ctx = {&fs, 99, MOVE_SURF};
    actor = 1; ScrCmd_GetPartySlotWithMove(&ctx);
    assert(ctx.result == (QOL_HM_ACTIONS ? 1 : 2));
    actor = 0xff; ScrCmd_GetPartySlotWithMove(&ctx);
    assert(ctx.result == (QOL_HM_ACTIONS ? PARTY_SIZE : 2));
    actor = 1; fs.script = 42; ScrCmd_GetPartySlotWithMove(&ctx);
    assert(ctx.result == 2);
    fs.script = std_field_cut; ScrCmd_GetPartySlotWithMove(&ctx);
    assert(ctx.result == 2); // wrong move for this script
    fs.script = std_field_headbutt; ctx.move = MOVE_HEADBUTT;
    ScrCmd_GetPartySlotWithMove(&ctx); assert(ctx.result == PARTY_SIZE);
    return 0;
}
'''
        for enabled in (0, 1):
            self.compile_run(declarations + actual + checks, f"-DQOL_HM_ACTIONS={enabled}")

    def test_party_menu_offers_unlearned_actions_and_stays_within_capacity(self):
        declarations = r'''
#include <assert.h>
#include <stddef.h>
#include <string.h>
#include "constants/moves.h"
#include "constants/pokemon.h"
typedef unsigned char u8;
typedef unsigned short u16;
typedef unsigned int u32;
typedef int BOOL;
#define TRUE 1
#define FALSE 0
#define MAX_MON_MOVES 4
#define PARTY_MON_CONTEXT_MENU_SUMMARY 0
#define PARTY_MON_CONTEXT_MENU_MAIL 2
#define PARTY_MON_CONTEXT_MENU_ITEM 3
#define PARTY_MON_CONTEXT_MENU_QUIT 4
#define PARTY_MON_CONTEXT_MENU_SWITCH 5
#define PARTY_MON_CONTEXT_MENU_FIELD_MOVES_BEGIN 16
#define PARTY_MON_CONTEXT_MENU_FIELD_MOVES_COUNT 16
#define FIELD_MOVE_FUNC_CHECK 1
#define FIELD_MOVE_RESPONSE_OK 0
typedef struct { int data[512]; } Pokemon;
typedef struct { Pokemon mons[6]; } Party;
typedef struct { int unlocked; } SaveData;
typedef struct { SaveData *saveData; } FieldSystem;
typedef struct { int unused; } FieldMoveCheckData;
typedef struct { Party *party; FieldSystem *fieldSystem; FieldMoveCheckData *fieldMoveCheckData; } Args;
typedef struct { int isEgg, heldItem; } DrawState;
typedef struct { Args *args; int partyMonIndex; DrawState monsDrawState[6]; } PartyMenu;
typedef u32 (*FieldMoveCheckFunc)(const FieldMoveCheckData *);
int tower, allowed[14], requested, labels[4], labelCount;
const u16 sFieldMoves[] = {MOVE_CUT, MOVE_FLY, MOVE_SURF, MOVE_STRENGTH, MOVE_ROCK_SMASH,
    MOVE_WATERFALL, MOVE_ROCK_CLIMB, MOVE_WHIRLPOOL, MOVE_FLASH, MOVE_TELEPORT, MOVE_DIG,
    MOVE_SWEET_SCENT, MOVE_CHATTER, MOVE_HEADBUTT, MOVE_MILK_DRINK, MOVE_SOFTBOILED};
Pokemon *Party_GetMonByIndex(Party *party, int index) { return &party->mons[index]; }
int GetMonData(Pokemon *mon, int field, void *unused) { return mon->data[field]; }
int FieldSystem_MapIsBattleTowerMultiPartnerSelectRoom(FieldSystem *fs) { return tower; }
int ItemIdIsMail(int item) { return item == 1; }
int Qol_HmIsUnlocked(SaveData *save, u16 move) { return save->unlocked; }
u32 check(const FieldMoveCheckData *data) { return allowed[requested] ? 0 : 1; }
void *FieldMove_GetMoveFunc(int type, int index) { assert(index < 14); requested = index; return check; }
void PartyMenu_ContextMenuAddFieldMove(PartyMenu *menu, u16 move, u8 index) {
    assert(index < 4); labels[index] = move; labelCount++;
}
'''
        actual = game.function_source("src/qol_field_moves.c", "Qol_HmIndex")
        actual += game.function_source("src/party_menu.c", "MoveId_GetFieldEffectId")
        actual += game.function_source("src/party_menu.c", "PartyMenu_SetContextMenuItems_Field")
        checks = r'''
int main(void) {
    Party party = {0}; SaveData save = {1}; FieldSystem fs = {&save};
    FieldMoveCheckData field = {0}; Args args = {&party, &fs, &field}; PartyMenu menu = {0};
    menu.args = &args;
    struct { u8 entries[8]; u8 sentinel; } out;
    out.sentinel = 0xa5;
    allowed[1] = 1; // Fly only; no Pokemon has learned it.
    int count = PartyMenu_SetContextMenuItems_Field(&menu, out.entries);
    assert(count == (QOL_HM_ACTIONS ? 5 : 4));
    assert(out.sentinel == 0xa5);
#if QOL_HM_ACTIONS
    assert(labels[0] == MOVE_FLY);
    allowed[2] = 1; // Surf at a usable shoreline.
    party.mons[0].data[MON_DATA_MOVE1] = MOVE_SURF;
    party.mons[0].data[MON_DATA_MOVE2] = MOVE_FLASH;
    party.mons[0].data[MON_DATA_MOVE3] = MOVE_DIG;
    party.mons[0].data[MON_DATA_MOVE4] = MOVE_HEADBUTT;
    labelCount = 0;
    count = PartyMenu_SetContextMenuItems_Field(&menu, out.entries);
    assert(count == 8 && labelCount == 4 && out.sentinel == 0xa5);
    assert(labels[0] == MOVE_FLY && labels[1] == MOVE_SURF);
    assert(labels[2] == MOVE_FLASH && labels[3] == MOVE_DIG);
    // Even impossible combinations from malformed map state cannot overrun the menu.
    for (int i = 0; i < 14; i++) allowed[i] = 1;
    labelCount = 0;
    assert(PartyMenu_SetContextMenuItems_Field(&menu, out.entries) == 8);
    assert(labelCount == 4 && out.sentinel == 0xa5);
    memset(allowed, 0, sizeof(allowed)); allowed[12] = 1;
    memset(&party, 0, sizeof(party)); labelCount = 0;
    assert(PartyMenu_SetContextMenuItems_Field(&menu, out.entries) == 5);
    assert(labelCount == 1 && labels[0] == MOVE_WHIRLPOOL);
    party.mons[0].data[MON_DATA_MOVE1] = MOVE_SURF;
    party.mons[0].data[MON_DATA_MOVE2] = MOVE_FLASH;
    party.mons[0].data[MON_DATA_MOVE3] = MOVE_DIG;
    party.mons[0].data[MON_DATA_MOVE4] = MOVE_HEADBUTT;
    // A learned HM does not bypass acquisition and badge requirements.
    save.unlocked = 0; labelCount = 0;
    assert(PartyMenu_SetContextMenuItems_Field(&menu, out.entries) == 7);
    assert(labels[0] == MOVE_FLASH);
#endif
    menu.monsDrawState[0].isEgg = 1;
    assert(PartyMenu_SetContextMenuItems_Field(&menu, out.entries) == 3);
    tower = 1;
    assert(PartyMenu_SetContextMenuItems_Field(&menu, out.entries) == 2);
    assert(out.sentinel == 0xa5);
    return 0;
}
'''
        for enabled in (0, 1):
            self.compile_run(declarations + actual + checks, f"-DQOL_HM_ACTIONS={enabled}")
