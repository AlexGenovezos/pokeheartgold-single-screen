"""Execute real EXP producer C with host edges; never import SDK tooling."""
import hashlib
import re
import unittest

from test_level_cap_save import ROOT, HOST_TYPES, adapter_program, function_source, host_run


BATTLE_CAP_BLOCK = '''#if QOL_LEVEL_CAPS
            if (!(battleType & (BATTLE_TYPE_NO_EXP | BATTLE_TYPE_TUTORIAL))) {
                totalExp = Qol_LevelCapLimitPlayerExp(SaveData_Get(),
                    GetMonData(mon, MON_DATA_SPECIES, NULL), newExp, totalExp);
            }
#endif
'''


def normalize_battle_cap(source):
    if source.count(BATTLE_CAP_BLOCK) != 1:
        raise AssertionError('expected exactly one known battle cap block')
    return source.replace(BATTLE_CAP_BLOCK, '', 1)


BATTLE_EDGES = r'''
#include "constants/battle.h"
#include "constants/items.h"
typedef void SysTask;
typedef void MsgData;
typedef struct Pokemon { u32 exp, hp, level, species, item, language; } Pokemon;
typedef struct { int id, tag; u32 param[2]; } BattleMessage;
typedef struct { int hp; u32 exp, species, form; } BattleMon;
typedef struct { int battlerIdFainted, victoryMusicPlayed;
    u32 expEarnFlags[2], selectedMonIndex[4], gainedExp, partyGainedExp;
    BattleMon battleMons[4]; } Context;
typedef struct { u32 type; Pokemon party[3]; BOOL playerOT; } BattleSystem;
typedef struct { BattleSystem *battleSystem; Context *ctx; int tempData[10], state; } GetterWork;
enum { DATA_GET_EXP_PARTY_SLOT, DATA_GET_EXP_PREV_PROGRESS_TO_NEXT_LEVEL,
    DATA_GET_EXP_PRINTER_ID, DATA_GET_EXP_FRAME_COUNTER };
enum { STATE_GET_EXP_START, STATE_GET_EXP_DONE = 30, STATE_GET_EXP_CHECK_DONE,
    HEAP_ID_BATTLE, SEQ_GS_WIN2,
    msg_0197_00001, msg_0197_00002, TAG_NICKNAME_NUM };
static unsigned evs, writes, prints, settingReads, limiterCalls;
static u32 displayed, requested, threshold = 1300;
static u8 gGameLanguage = 2;
static BOOL capOn = TRUE;
void *SaveData_Get(void) { settingReads++; return (void *)1; }
u32 Qol_LevelCapLimitPlayerExp(void *save, u16 species, u32 old, u32 request) {
    assert(save == (void *)1 && species == 25); limiterCalls++; requested = request;
    return !capOn ? request : old >= threshold ? 0 : request < threshold-old ? request : threshold-old;
}
MsgData *BattleSystem_GetMessageLoader(BattleSystem *bs) { return NULL; }
u32 BattleSystem_GetBattleType(BattleSystem *bs) { return bs->type; }
int BattleSystem_GetPartySize(BattleSystem *bs, int battler) { return 3; }
Pokemon *BattleSystem_GetPartyMon(BattleSystem *bs, int battler, int slot) { return &bs->party[slot]; }
u32 GetMonData(Pokemon *mon, int field, void *out) {
    switch(field) {
    case MON_DATA_HELD_ITEM: return mon->item;
    case MON_DATA_HP: return mon->hp;
    case MON_DATA_LEVEL: return mon->level;
    case MON_DATA_LANGUAGE: return mon->language;
    case MON_DATA_EXPERIENCE: return mon->exp;
    case MON_DATA_SPECIES: return mon->species;
    default: assert(0); return 0;
    }
}
void SetMonData(Pokemon *mon, int field, const u32 *value) {
    assert(field == MON_DATA_EXPERIENCE); mon->exp = *value; writes++;
}
int GetItemAttr(u16 item, int field, int heap) { return item; }
u32 MaskOfFlagNo(int slot) { return 1u << slot; }
void PlayBGM(int id) {}
void BattleSystem_SetCriticalHpMusicFlag(BattleSystem *bs, int flag) {}
BOOL BattleSystem_IsPlayerOT(BattleSystem *bs, Pokemon *mon) { return bs->playerOT; }
u32 GetMonBaseExperienceAtCurrentLevel(Pokemon *mon) { return 1000; }
void *BattleSystem_GetParty(BattleSystem *bs, int battler) { return bs; }
void BattleScript_CalcEffortValues(void *party, int slot, u32 species, u32 form) { evs++; }
int BattleSystem_GetTextFrameDelay(BattleSystem *bs) { return 1; }
int BattleSystem_PrintBattleMessage(BattleSystem *bs, MsgData *loader, BattleMessage *message, int delay) {
    prints++; displayed = message->param[1]; return 4;
}
static Context ctx;
static BattleSystem bs;
static GetterWork work;
static void init(u32 type, u32 old, u32 gain, u32 shared, int effect, int active, int playerOT, int language) {
    memset(&ctx, 0, sizeof(ctx)); memset(&bs, 0, sizeof(bs)); memset(&work, 0, sizeof(work));
    work.battleSystem = &bs; work.ctx = &ctx;
    bs.type = type; bs.playerOT = playerOT;
    bs.party[0] = (Pokemon){old, 10, 12, 25, effect, language};
    ctx.expEarnFlags[0] = 1; ctx.gainedExp = gain; ctx.partyGainedExp = shared;
    ctx.battlerIdFainted = 1; ctx.battleMons[1].hp = 1;
    ctx.battleMons[0].exp = ctx.battleMons[2].exp = 77;
    ctx.selectedMonIndex[0] = active ? 0 : 2; ctx.selectedMonIndex[2] = 1;
    evs = writes = prints = settingReads = limiterCalls = 0; displayed = requested = 0;
    capOn = TRUE; threshold = 1300;
}
'''


def battle_start():
    actual = function_source('src/battle/battle_command.c', 'Task_GetExp')
    # Preserve actual recipient selection, all multipliers, EVs, writes, message
    # and state transition; only later asynchronous cases are outside this run.
    return actual[:actual.index('    case STATE_GET_EXP_WAIT_MESSAGE_PRINT:')] + '\n}\n}\n'


DAYCARE_EDGES = r'''
#include "constants/species.h"
#define NUM_DAYCARE_MONS 2
typedef struct Party { Pokemon mons[6]; unsigned count; } Party;
typedef struct Daycare { DaycareMon mons[2]; BOOL hasEgg; u32 cycle; } Daycare;
typedef struct FieldSystem { SaveData *saveData; } FieldSystem;
static unsigned rolls, eggs, calls;
void Daycare_GetBothBoxMonsPtr(Daycare *daycare, BoxPokemon **parents) {
    parents[0] = &daycare->mons[0].mon; parents[1] = &daycare->mons[1].mon;
}
DaycareMon *Save_Daycare_GetMonX(Daycare *daycare, s32 index) { return &daycare->mons[index]; }
void DaycareMon_AddSteps(DaycareMon *mon, u32 steps) { mon->steps += steps; }
BOOL Save_Daycare_HasEgg(Daycare *daycare) { return daycare->hasEgg; }
u8 Save_Daycare_CalcCompatibilityInternal(Daycare *daycare) { return 100; }
u32 LCRandom(void) { rolls++; return 0; }
void GenerateEggPID(Daycare *daycare) { eggs++; daycare->hasEgg = TRUE; }
void FieldSystem_TryTriggerDaycareEggCall(FieldSystem *field) { calls++; }
int Save_Daycare_GetEggCycleCounter(Daycare *daycare) { return daycare->cycle; }
void Save_Daycare_SetEggCycleCounter(Daycare *daycare, int value) { daycare->cycle = value; }
int Daycare_GetEggCycleLength(FieldSystem *field) { return 255; }
u8 GetEggCyclesToSubtract(Party *party) { return 1; }
int Party_GetCount(Party *party) { return 0; }
Pokemon *Party_GetMonByIndex(Party *party, int index) { assert(0); return NULL; }
void SetMonData(Pokemon *mon, int field, const u32 *value) { assert(0); }
static Daycare daycare;
static FieldSystem field = {&saved};
static Party party;
static void init_daycare(u16 config, u16 phase, u32 steps, u32 baseExp) {
    memset(&saved, 0, sizeof(saved)); memset(&daycare, 0, sizeof(daycare));
    set_raw(config, phase);
    for (unsigned i = 0; i < 2; i++) {
        daycare.mons[i].mon = (Pokemon){25, baseExp, 13}; daycare.mons[i].steps = steps;
    }
    rolls = eggs = calls = 0;
}
enum { GAME_STAT_MONS_SENT_TO_DAYCARE };
void *Save_GameStats_Get(SaveData *save) { return save; }
void GameStats_Inc(void *stats, int stat) {}
int Save_Daycare_GetAvailableSlot(Daycare *dc) { return dc->mons[0].mon.species ? 1 : 0; }
void DaycareMon_CopyFromPartySlot(Party *party, u8 index, DaycareMon *dc, SaveData *save) {
    dc->mon = party->mons[index]; dc->steps = 0;
}
void DaycareMon_Copy(DaycareMon *dest, const DaycareMon *src) { *dest = *src; }
void DaycareMon_Init(DaycareMon *mon) { memset(mon, 0, sizeof(*mon)); }
typedef void MessageFormat;
int Save_Daycare_MoveMonToParty(Party *party, DaycareMon *dc, MessageFormat *format) {
    u16 species = dc->mon.species;
    party->mons[party->count] = dc->mon;
    party->mons[party->count++].exp += dc->steps;
    DaycareMon_Init(dc); return species;
}
'''

WALKER_EDGES = r'''
static unsigned copies, friendship;
u32 CalcBoxMonExpToNextLevel(BoxPokemon *mon) { return CalcMonExpToNextLevel(mon); }
void CopyBoxPokemonToPokemon(BoxPokemon *boxed, Pokemon *mon) { *mon = *boxed; copies++; }
void SetMonData(Pokemon *mon, int field, const u32 *value) {
    assert(field == MON_DATA_EXPERIENCE); mon->exp = *value; monWrites++;
}
void CalcMonLevelAndStats(Pokemon *mon) { mon->level = (mon->exp - mon->species) / 100; }
u32 CalcBoxMonLevel(BoxPokemon *mon) { return (mon->exp - mon->species) / 100; }
void MonApplyFriendshipMod(Pokemon *mon, int event, int location) { friendship++; }
'''

CANDY_EDGES = r'''
#include "constants/items.h"
enum HeapID { HEAP_ID_PARTY_MENU };
typedef struct Party { Pokemon mons[2]; } Party;
static unsigned genericUses, genericChecks, friendship;
Pokemon *Party_GetMonByIndex(Party *party, int index) { return &party->mons[index]; }
BOOL CanUseItemOnMonInParty(Party *party, u16 item, s32 index, s32 move, enum HeapID heap) {
    genericChecks++; return party->mons[index].level < MAX_LEVEL;
}
BOOL UseItemOnMonInParty(Party *party, u16 item, s32 index, u8 move, u16 location, enum HeapID heap) {
    Pokemon *mon = &party->mons[index]; genericUses++; friendship++;
    mon->exp += CalcMonExpToNextLevel(mon); mon->level++; return TRUE;
}
'''

PARTY_MENU_EDGES = r'''
typedef void String;
typedef int ItemData;
typedef struct Bag { int quantity; } Bag;
typedef struct FieldSystem { SaveData *saveData; } FieldSystem;
typedef struct Args { Party *party; u16 itemId; FieldSystem *fieldSystem; int context;
    Bag *bag; int species, evoMethod, selectedAction; } Args;
typedef struct PartyMenu PartyMenu;
struct PartyMenu {
    Args *args; int partyMonIndex, levelUpStatsTmp[6], levelUpLearnMovesLoopState;
    struct { int level, hp, maxHp, status; } monsDrawState[2];
    void *msgData, *msgFormat, *formattedStrBuf;
    int (*itemUseCallback)(PartyMenu *);
};
enum { PARTY_MENU_CONTEXT_USE_ITEM=1, PARTY_MENU_CONTEXT_COPIED=2,
    PARTY_MENU_STATE_FORM_CHANGE_ANIM=1, PARTY_MENU_STATE_SELECT_MOVE,
    PARTY_MENU_ACTION_RETURN_EVO_ITEM_USE, PARTY_MENU_STATE_BEGIN_EXIT,
    PARTY_MON_SELECTION_CONFIRM=7, PARTY_MENU_STATE_ITEM_USE_CB,
    msg_0300_00102=102, msg_0300_00177=177, PRINTING_MODE_LEFT_ALIGN=0,
    PARTY_MON_STATUS_ICON_OK=0 };
static unsigned restores, consumes, successMessages, noEffectMessages, moveCallbacks;
ItemData *LoadItemDataOrGfx(u16 item, int type, enum HeapID heap) { static int data; return &data; }
BOOL Mon_CanUseGracidea(Pokemon *mon) { return FALSE; }
void Heap_Free(void *data) {}
void PartyMenu_FormChangeScene_Begin(PartyMenu *menu) {}
int GetItemAttr_PreloadedItemData(ItemData *data, int field) { return 0; }
void PartyMenu_SelectMoveForPpRestoreOrPpUp(PartyMenu *menu, int mode) {}
BOOL Bag_TakeItem(Bag *bag, u16 item, int count, enum HeapID heap) { bag->quantity -= count; consumes++; return TRUE; }
BOOL Bag_AddItem(Bag *bag, u16 item, int count, enum HeapID heap) { assert(item == ITEM_RARE_CANDY); bag->quantity += count; restores++; return TRUE; }
int GetMonEvolution(void *party, Pokemon *mon, int context, u16 item, int *method) { return 0; }
void PartyMenu_SetItemUseFuncFromBagSelection(PartyMenu *menu) {}
void PartyMenu_PrintMessageOnWindow34(PartyMenu *menu, int id, BOOL wait) { if(id == msg_0300_00102) noEffectMessages++; }
int PartyMenu_ItemUseFunc_WaitTextPrinterThenExit(PartyMenu *menu) { return 0; }
int PartyMenu_GetCurrentMapSec(PartyMenu *menu) { return 1; }
String *NewString_ReadMsgData(void *data, int id) { assert(id == msg_0300_00177); successMessages++; return NULL; }
BoxPokemon *Mon_GetBoxMon(Pokemon *mon) { return mon; }
void BufferBoxMonNickname(void *fmt, int index, BoxPokemon *mon) {}
void BufferIntegerAsString(void *fmt, int index, int value, int width, int mode, BOOL sign) {}
void StringExpandPlaceholders(void *fmt, void *out, String *in) {}
void String_Delete(String *string) {}
int Pokemon_GetStatusIconId(Pokemon *mon) { return 0; }
void PartyMenu_DrawMonStatusIcon(PartyMenu *menu, int index, int status) {}
void PartyMenu_PrintMonLevelOnWindow(PartyMenu *menu, int index) {}
void PartyMenu_UpdateMonPanelPalette(PartyMenu *menu, int index) {}
int PartyMenu_ItemUseFunc_HPRestoreAnimLoop(PartyMenu *menu) { return 0; }
void PartyMenu_DrawPartyMonsList_Default(PartyMenu *menu, int index) {}
void PartyMenu_CommitPartyMonPanelWindowsToVram_InVBlank(PartyMenu *menu, int index) {}
int PartyMenu_ItemUseFunc_LevelUpLearnMovesLoop(PartyMenu *menu) { moveCallbacks++; return 0; }
'''

DAYCARE_PREVIEW_EDGES = r'''
#include <stdlib.h>
enum { HEAP_ID_FIELD2, PRINTING_MODE_LEFT_ALIGN };
static unsigned displayedGrowth;
Pokemon *AllocMonZeroed(int heap) { return calloc(1, sizeof(Pokemon)); }
BoxPokemon *Mon_GetBoxMon(Pokemon *mon) { return mon; }
void CopyBoxPokemonToBoxPokemon(BoxPokemon *src, BoxPokemon *dest) { *dest = *src; }
void SetBoxMonData(BoxPokemon *mon, int field, const u32 *value) {
    assert(field == MON_DATA_EXPERIENCE); mon->exp = *value;
}
u32 CalcBoxMonLevel(BoxPokemon *mon) { return (mon->exp - mon->species) / 100; }
void Heap_Free(void *pointer) { free(pointer); }
void BufferIntegerAsString(MessageFormat *fmt, int index, int value, int width, int mode, BOOL sign) { displayedGrowth = value; }
void BufferBoxMonNickname(MessageFormat *fmt, int index, BoxPokemon *mon) {}
'''


def candy_wrappers():
    result = []
    for prefix, args in (
            ('CanUse', 'SaveData *save, Party *party, u16 item, s32 index, s32 move, enum HeapID heap'),
            ('Use', 'SaveData *save, Party *party, u16 item, s32 index, u8 move, u16 location, enum HeapID heap')):
        name = prefix + 'ItemOnMonInPartyField'
        if re.search(r'\b' + name + r'\(', (ROOT / 'src/use_item_on_mon.c').read_text()):
            result.append(function_source('src/use_item_on_mon.c', name))
        else:
            # Existing behavior delegates directly to generic legality/effects.
            call_args = 'party, item, index, move, ' + ('location, ' if prefix == 'Use' else '') + 'heap'
            result.append(f'BOOL {name}({args}) {{ return {prefix}ItemOnMonInParty({call_args}); }}')
    return '\n'.join(result)


class LevelCapProducerTests(unittest.TestCase):
    def run_battle(self, checks, enabled=1):
        host_run(self, HOST_TYPES + BATTLE_EDGES + battle_start() + '\nint main(void) {\n' + checks + '\nreturn 0;}', enabled)

    def run_daycare(self, checks, enabled=1):
        actual = function_source('src/get_egg.c', 'HandleDaycareStep')
        host_run(self, adapter_program() + DAYCARE_EDGES + actual + '\nint main(void) {\n' + checks + '\nreturn 0;}', enabled)

    def run_walker(self, checks, enabled=1):
        actual = function_source('src/application/pokewalker/pokewalker_stroll.c', 'PokewalkerApp_AddStrollExp')
        # Name adaptation only for pre-integration RED: execute the actual old
        # function and make its missing explicit save argument visible in a tiny
        # shim. No cap behavior is supplied by the shim.
        if not re.search(r'PokewalkerApp_AddStrollExp\(SaveData\s*\*', actual):
            actual = actual.replace('PokewalkerApp_AddStrollExp(', 'Legacy_AddStrollExp(', 1)
            actual += '''\nBOOL PokewalkerApp_AddStrollExp(SaveData *save, BoxPokemon *box, Pokemon *mon, int exp) {
                return Legacy_AddStrollExp(box, mon, exp);
            }'''
        host_run(self, adapter_program() + WALKER_EDGES + actual + '\nint main(void) {\n' + checks + '\nreturn 0;}', enabled)

    def test_field_candy_rejects_before_generic_effects_but_below_cap_works(self):
        host_run(self, adapter_program() + CANDY_EDGES + candy_wrappers() + r'''
int main(void) {
    set_raw(0xc701, 0);
    Party party = {{{25, 1325, 13}, {25, 1225, 12}}};
    assert(!CanUseItemOnMonInPartyField(&saved, &party, ITEM_RARE_CANDY, 0, 0, HEAP_ID_PARTY_MENU));
    assert(!UseItemOnMonInPartyField(&saved, &party, ITEM_RARE_CANDY, 0, 0, 1, HEAP_ID_PARTY_MENU));
    assert(genericChecks == 0 && genericUses == 0 && friendship == 0 && party.mons[0].exp == 1325);
    assert(CanUseItemOnMonInPartyField(&saved, &party, ITEM_RARE_CANDY, 1, 0, HEAP_ID_PARTY_MENU));
    assert(UseItemOnMonInPartyField(&saved, &party, ITEM_RARE_CANDY, 1, 0, 1, HEAP_ID_PARTY_MENU));
    assert(party.mons[1].exp == 1325 && party.mons[1].level == 13 && friendship == 1);
    /* Generic paths remain available for copied facility Pokemon. */
    assert(UseItemOnMonInParty(&party, ITEM_RARE_CANDY, 0, 0, 1, HEAP_ID_PARTY_MENU));
    assert(party.mons[0].level == 14);
    return 0;
}
''')

    def test_field_candy_disabled_support_delegates_without_cap_reads(self):
        host_run(self, adapter_program() + CANDY_EDGES + candy_wrappers() + r'''
int main(void) {
    set_raw(0xc701, 0);
    Party party = {{{25, 1325, 13}, {25, 1225, 12}}};
    assert(CanUseItemOnMonInPartyField(&saved, &party, ITEM_RARE_CANDY, 0, 0, HEAP_ID_PARTY_MENU));
    assert(UseItemOnMonInPartyField(&saved, &party, ITEM_RARE_CANDY, 0, 0, 1, HEAP_ID_PARTY_MENU));
    assert(slotReads == 0 && progressionReads == 0 && growthReads == 0 && friendship == 1);
    return 0;
}
''', enabled=0)

    def test_field_menu_denial_consumes_nothing_and_late_failure_restores_candy(self):
        actual = '\n'.join(function_source(path, name) for path, name in (
            ('src/party_menu.c', 'PartyMenu_HandleUseItemOnMon'),
            ('src/party_menu_items.c', 'PartyMenu_ItemUseFunc_LevelUp')))
        host_run(self, adapter_program() + CANDY_EDGES + PARTY_MENU_EDGES + candy_wrappers() + actual + r'''
int main(void) {
    set_raw(0xc701, 0);
    Party party = {{{25, 1325, 13}, {25, 1225, 12}}}; Bag bag = {1};
    FieldSystem field = {&saved}; Args args = {&party, ITEM_RARE_CANDY, &field, PARTY_MENU_CONTEXT_USE_ITEM, &bag, 0, 0, 0};
    PartyMenu menu = {0}; menu.args = &args;
    assert(PartyMenu_HandleUseItemOnMon(&menu) == PARTY_MENU_STATE_ITEM_USE_CB);
    assert(bag.quantity == 1 && consumes == 0 && noEffectMessages == 1 && friendship == 0);
    /* Reach application after a successful usability check and one consumption,
     * then emulate a changed cap/mon before callback: rollback without success. */
    menu.partyMonIndex = 0; bag.quantity = 0; noEffectMessages = 0;
    assert(PartyMenu_ItemUseFunc_LevelUp(&menu) == PARTY_MENU_STATE_ITEM_USE_CB);
    assert(bag.quantity == 1 && restores == 1 && successMessages == 0 && friendship == 0);
    assert(menu.partyMonIndex == PARTY_MON_SELECTION_CONFIRM);
    assert(menu.itemUseCallback == PartyMenu_ItemUseFunc_WaitTextPrinterThenExit);
    menu.partyMonIndex = 1; bag.quantity = 1; noEffectMessages = 0;
    PartyMenu_HandleUseItemOnMon(&menu); assert(bag.quantity == 0 && consumes == 1);
    PartyMenu_ItemUseFunc_LevelUp(&menu);
    assert(party.mons[1].level == 13 && successMessages == 1 && friendship == 1);
    assert(menu.itemUseCallback == PartyMenu_ItemUseFunc_LevelUpLearnMovesLoop);
    return 0;
}
''')

    def test_walker_suppressed_gain_copies_output_without_level_up_friendship(self):
        self.run_walker(r'''
set_raw(0xc701, 0);
BoxPokemon box = {25, 1325, 13}; Pokemon mon = {0};
assert(!PokewalkerApp_AddStrollExp(&saved, &box, &mon, 10000));
assert(copies == 1 && mon.exp == 1325 && mon.species == 25 && mon.level == 13);
assert(friendship == 0 && box.exp == 1325);
''')

    def test_walker_reaches_cap_partial_negative_and_original_one_level_bound(self):
        self.run_walker(r'''
set_raw(0xc701, 0);
BoxPokemon box = {25, 1295, 12}; Pokemon mon = {0};
assert(PokewalkerApp_AddStrollExp(&saved, &box, &mon, 10000));
assert(mon.exp == 1325 && mon.level == 13 && friendship == 1);
friendship = 0;
assert(!PokewalkerApp_AddStrollExp(&saved, &box, &mon, 10));
assert(mon.exp == 1305 && mon.level == 12 && friendship == 0);
assert(!PokewalkerApp_AddStrollExp(&saved, &box, &mon, -100));
assert(mon.exp == box.exp && friendship == 0);
set_raw(0, 0); box = (BoxPokemon){25, 1395, 13};
assert(PokewalkerApp_AddStrollExp(&saved, &box, &mon, 10000));
assert(mon.exp == 1425 && mon.level == 14 && friendship == 1);
''')

    def test_walker_level_100_still_populates_output_without_award(self):
        self.run_walker(r'''
set_raw(0xc701, 0);
BoxPokemon box = {25, 10025, 100}; Pokemon mon = {0};
assert(!PokewalkerApp_AddStrollExp(&saved, &box, &mon, 10000));
assert(copies == 1 && mon.exp == box.exp && mon.level == 100 && friendship == 0);
assert(progressionReads == 0 && growthReads == 0);
''')

    def test_walker_disabled_support_retains_one_level_limit_without_cap_access(self):
        self.run_walker(r'''
set_raw(0xc701, 0);
BoxPokemon box = {25, 1395, 13}; Pokemon mon = {0};
assert(PokewalkerApp_AddStrollExp(&saved, &box, &mon, 10000));
assert(mon.exp == 1425 && mon.level == 14 && friendship == 1);
assert(slotReads == 0 && progressionReads == 0 && growthReads == 0);
''', enabled=0)

    def test_battle_multipliers_precede_cap_and_display_matches_both_writes(self):
        self.run_battle(r'''
/* Lucky Egg + trainer + foreign language: floor(floor(100*1.5)*1.5)*1.7 = 382. */
init(BATTLE_TYPE_TRAINER, 1290, 100, 0, HOLD_EFFECT_EXP_UP, 1, 0, 1);
Task_GetExp(NULL, &work);
assert(bs.party[0].exp == 1300 && ctx.battleMons[0].exp == 1300);
assert(displayed == 10 && prints == 1 && evs == 1 && writes == 1);
assert(requested == 382 && limiterCalls == 1);
/* Participation and EXP Share combine before trainer/foreign multipliers. */
init(BATTLE_TYPE_TRAINER, 1290, 100, 50, HOLD_EFFECT_EXP_SHARE, 0, 0, 2);
Task_GetExp(NULL, &work);
assert(requested == 337 && bs.party[0].exp == 1300 && displayed == 10);
assert(ctx.battleMons[0].exp == 77 && evs == 1);
/* Active second player recipient keeps its own cache. */
init(BATTLE_TYPE_DOUBLES, 1290, 50, 0, 0, 0, 1, 2);
ctx.selectedMonIndex[2] = 0;
Task_GetExp(NULL, &work);
assert(ctx.battleMons[2].exp == 1300 && ctx.battleMons[0].exp == 77);
''')

    def test_battle_zero_gain_retains_evs_and_skips_exp_message(self):
        self.run_battle(r'''
init(0, 1300, 200, 0, 0, 1, 1, 2);
Task_GetExp(NULL, &work);
assert(bs.party[0].exp == 1300 && ctx.battleMons[0].exp == 1300);
assert(evs == 1 && prints == 0 && work.state == STATE_GET_EXP_CHECK_DONE);
assert(limiterCalls == 1 && requested == 200);
''')

    def test_battle_exclusions_off_and_disabled_support_keep_original_award(self):
        checks = r'''
const u32 excluded[] = {BATTLE_TYPE_LINK, BATTLE_TYPE_FRONTIER, BATTLE_TYPE_SAFARI,
    BATTLE_TYPE_PAL_PARK, BATTLE_TYPE_TUTORIAL};
for (unsigned i = 0; i < NELEMS(excluded); i++) {
    init(excluded[i], 1290, 200, 0, 0, 1, 1, 2);
    Task_GetExp(NULL, &work);
    assert(bs.party[0].exp == 1490 && displayed == 200 && evs == 1);
    assert(settingReads == 0 && limiterCalls == 0);
}
init(0, 1290, 200, 0, 0, 1, 1, 2); capOn = FALSE;
Task_GetExp(NULL, &work); assert(bs.party[0].exp == 1490 && displayed == 200);
#if !QOL_LEVEL_CAPS
assert(settingReads == 0 && limiterCalls == 0);
#endif
'''
        for enabled in (0, 1):
            with self.subTest(enabled=enabled):
                self.run_battle(checks, enabled)

    def test_daycare_freezes_growth_but_keeps_independent_breeding_cadence(self):
        self.run_daycare(r'''
init_daycare(0xc701, 0, 254, 1071); /* Pending total 1325: exactly cap. */
HandleDaycareStep(&daycare, &party, &field);
assert(daycare.mons[0].steps == 254 && daycare.mons[1].steps == 254);
assert(raw_phase() == 0xd1ff && rolls == 1 && eggs == 1 && calls == 1);
for (unsigned i = 0; i < 255; i++) HandleDaycareStep(&daycare, &party, &field);
assert(raw_phase() == 0xd1fe && rolls == 1); /* Waiting egg never pauses phase. */
daycare.hasEgg = FALSE; HandleDaycareStep(&daycare, &party, &field);
assert(rolls == 2 && raw_phase() == 0xd1ff && daycare.mons[1].steps == 254);
Qol_LevelCapSetEnabledForSave(&saved, FALSE);
HandleDaycareStep(&daycare, &party, &field);
assert(raw_phase() == 0xd100 && daycare.mons[1].steps == 255);
assert(daycare.mons[0].steps == 255); /* No suppressed EXP is released. */
''')

    def test_daycare_reaches_cap_preserves_old_pending_and_resumes_on_cap_increase(self):
        self.run_daycare(r'''
init_daycare(0xc701, 0, 0, 1324);
HandleDaycareStep(&daycare, &party, &field);
assert(daycare.mons[0].steps == 1 && daycare.mons[1].steps == 1);
HandleDaycareStep(&daycare, &party, &field);
assert(daycare.mons[0].steps == 1 && daycare.mons[1].steps == 1);
saved.profile.badges = 1; /* New cap17 permits exactly one new EXP/walk. */
HandleDaycareStep(&daycare, &party, &field);
assert(daycare.mons[0].steps == 2 && daycare.mons[1].steps == 2);
init_daycare(0xc701, 0, 9000, 1000);
HandleDaycareStep(&daycare, &party, &field);
assert(daycare.mons[0].steps == 9000 && daycare.mons[1].steps == 9000);
init_daycare(0xc701, 0, UINT_MAX - 500, 1000);
HandleDaycareStep(&daycare, &party, &field);
assert(daycare.mons[0].steps == UINT_MAX - 500); /* Saturated pending calculation. */
''')

    def test_daycare_original_off_and_support_disabled_timing(self):
        for enabled in (0, 1):
            with self.subTest(enabled=enabled):
                self.run_daycare(r'''
init_daycare(0, 0x1234, 254, 1000);
HandleDaycareStep(&daycare, &party, &field);
assert(daycare.mons[0].steps == 255 && daycare.mons[1].steps == 255);
assert(rolls == 1 && eggs == 1 && raw_phase() == 0x1234);
HandleDaycareStep(&daycare, &party, &field);
assert(daycare.mons[1].steps == 256 && raw_phase() == 0x1234);
#if !QOL_LEVEL_CAPS
assert(slotReads == 0 && progressionReads == 0 && growthReads == 0);
#endif
''', enabled)

    def test_daycare_old_phase_255_wraps_without_roll_and_single_parent_resets(self):
        self.run_daycare(r'''
init_daycare(0xc701, 0, 255, 1070);
HandleDaycareStep(&daycare, &party, &field);
assert(raw_phase() == 0xd100 && rolls == 0 && daycare.mons[1].steps == 255);
daycare.mons[1].mon.species = 0; set_raw(0xc701, 0xd177);
HandleDaycareStep(&daycare, &party, &field);
assert(raw_phase() == 0xd100 && rolls == 0 && daycare.mons[0].steps == 255);
set_raw(0, 0x1234);
HandleDaycareStep(&daycare, &party, &field);
assert(raw_phase() == 0x1234 && daycare.mons[0].steps == 256 && rolls == 0);
''')

    def test_daycare_deposit_withdraw_compaction_and_reload_preserve_growth(self):
        actual = '\n'.join(function_source('src/get_egg.c', name) for name in
                           ('Save_Daycare_Compaction', 'Save_Daycare_PutMonIn', 'Save_Daycare_RetrieveMon'))
        host_run(self, adapter_program() + DAYCARE_EDGES + actual + r'''
int main(void) {
    init_daycare(0xc701, 0xd199, 9000, 1000);
    party.count = 0;
    assert(Save_Daycare_RetrieveMon(&party, NULL, &daycare, 0) == 25);
    assert(party.mons[0].exp == 10000); /* Preexisting over-cap pending growth survives. */
    assert(daycare.mons[0].steps == 9000 && daycare.mons[1].mon.species == 0);
    assert(raw_phase() == 0xd100);
    party.mons[1] = (Pokemon){26, 2000, 20};
    set_raw(0xc701, 0xd177);
    Save_Daycare_PutMonIn(&party, 1, &daycare, &saved);
    assert(daycare.mons[1].mon.species == 26 && daycare.mons[1].steps == 0 && raw_phase() == 0xd100);
    set_raw(0, 0xd1ff); /* Tagged phase remains meaningful after disable/reload. */
    SaveData saveCopy = saved; Daycare daycareCopy = daycare;
    memset(&saved, 0, sizeof(saved)); memset(&daycare, 0, sizeof(daycare));
    saved = saveCopy; daycare = daycareCopy;
    assert(Qol_LevelCapAdvanceDaycarePhase(&saved, &daycare.mons[1]) == 0);
    assert(raw_phase() == 0xd100);
    set_raw(0, 0xd188);
    assert(Save_Daycare_RetrieveMon(&party, NULL, &daycare, 1) == 26);
    assert(raw_phase() == 0xd100 && daycare.mons[1].mon.species == 0);
    set_raw(0, 0x1234);
    Save_Daycare_PutMonIn(&party, 1, &daycare, &saved);
    assert(raw_phase() == 0x1234); /* Untouched Off format remains untouched. */
    return 0;
}
''')

    def test_daycare_preview_price_and_withdraw_use_only_accepted_steps(self):
        actual = '\n'.join(function_source('src/get_egg.c', name) for name in
                           ('HandleDaycareStep', 'GetDaycareUpdatedLevel',
                            'DaycareMon_CalcLevelGrowth', 'DaycareMon_BufferLevelGrowthAndNick',
                            'DaycareMon_BufferNickAndRetrievalPrice'))
        host_run(self, adapter_program() + DAYCARE_EDGES + DAYCARE_PREVIEW_EDGES + actual + r'''
int main(void) {
    init_daycare(0xc701, 0, 0, 1324);
    for (unsigned i = 0; i < 300; i++) HandleDaycareStep(&daycare, &party, &field);
    assert(daycare.mons[0].steps == 1);
    assert(GetDaycareUpdatedLevel(&daycare.mons[0].mon, daycare.mons[0].steps) == 13);
    assert(DaycareMon_CalcLevelGrowth(&daycare.mons[0]) == 1);
    assert(DaycareMon_BufferLevelGrowthAndNick(&daycare.mons[0], NULL) == 1 && displayedGrowth == 1);
    assert(DaycareMon_BufferNickAndRetrievalPrice(&daycare.mons[0], NULL) == 200 && displayedGrowth == 200);
    Save_Daycare_MoveMonToParty(&party, &daycare.mons[0], NULL);
    assert(party.mons[0].exp == 1325); /* Preview/fee/withdraw derive from same stored award. */
    return 0;
}
''')

    def test_daycare_legacy_growth_consumers_and_walker_acquisitions_stay_original(self):
        for (path, name), digest in UNCHANGED_PRODUCER_FUNCTIONS.items():
            with self.subTest(function=name):
                actual = function_source(path, name)
                self.assertEqual(hashlib.sha256(actual.encode()).hexdigest(), digest)
        actual = function_source('src/application/pokewalker/pokewalker_stroll.c', 'PokewalkerApp_ReturnStrollMon')
        new = 'PokewalkerApp_AddStrollExp(app->saveData, boxMon, mon, app->strollSteps)'
        old = 'PokewalkerApp_AddStrollExp(boxMon, mon, app->strollSteps)'
        self.assertEqual(actual.count(new), 1)
        self.assertEqual(hashlib.sha256(actual.replace(new, old, 1).encode()).hexdigest(),
                         WALKER_RETURN_BASELINE_SHA256)

    def test_battle_normalizer_permits_only_the_exact_cap_block(self):
        actual = function_source('src/battle/battle_command.c', 'Task_GetExp')
        self.assertEqual(hashlib.sha256(normalize_battle_cap(actual).encode()).hexdigest(),
                         BATTLE_BASELINE_SHA256)

    def test_battle_normalizer_detects_ev_cache_message_and_level_up_mutations(self):
        original = function_source('src/battle/battle_command.c', 'Task_GetExp')
        if BATTLE_CAP_BLOCK not in original:
            original = original.replace('            newExp += totalExp;',
                                        BATTLE_CAP_BLOCK + '            newExp += totalExp;', 1)
        self.assertEqual(hashlib.sha256(normalize_battle_cap(original).encode()).hexdigest(),
                         BATTLE_BASELINE_SHA256)
        for old, new in (
                ('BattleScript_CalcEffortValues', 'BattleScript_RemoveEffortValues'),
                ('.exp = newExp;', '.exp = 999;'),
                ('msg.param[1] = totalExp;', 'msg.param[1] = 999;'),
                ('Pokemon_TryLevelUp(mon)', 'Pokemon_SkipLevelUp(mon)')):
            with self.subTest(token=old):
                self.assertIn(old, original)
                changed = original.replace(old, new, 1)
                self.assertNotEqual(hashlib.sha256(normalize_battle_cap(changed).encode()).hexdigest(),
                                    BATTLE_BASELINE_SHA256)


# Hash of the complete pre-cap Task_GetExp, including every later asynchronous
# move/stat/evolution state. Only BATTLE_CAP_BLOCK may be normalized away.
BATTLE_BASELINE_SHA256 = '1244ab2f5c1c050f9a2007d2c874467fae8157c0e88dbd4af34a2c642c78a910'

UNCHANGED_PRODUCER_FUNCTIONS = {
    ('src/get_egg.c', 'Save_Daycare_MoveMonToParty'):
        '87a6a970688a0608cf98d2accdd1064f5465340d2475f8bb5bfa6d971b35d328',
    ('src/get_egg.c', 'GetDaycareUpdatedLevel'):
        '0ba215a154a192c27a03a57ac48c35d296f2f9f6a76ca4723162ae4258cd23ef',
    ('src/get_egg.c', 'DaycareMon_CalcLevelGrowth'):
        'f04df4b4fbedb33199085d6f18a11fad474993baf7204d152135b54e43675f86',
    ('src/get_egg.c', 'DaycareMon_BufferNickAndRetrievalPrice'):
        '23d0561184c193be612cb56be74c86c085304282bb60bbc77c18213299a835ca',
    ('src/application/pokewalker/pokewalker_stroll.c', 'PokewalkerApp_AddStrollFriendship'):
        '6b5e61fab34c797900679be0f74ec9819e87c3ddea2a3583ef4764cc3d3dfc12',
}

WALKER_RETURN_BASELINE_SHA256 = '7544d2e8922abdfefb392b192762d00024465903c777049f72f932e5d24726bc'


if __name__ == '__main__':
    unittest.main()
