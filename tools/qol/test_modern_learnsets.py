"""Compile real learnset readers and consumers with the ROM/SDK edges stubbed."""
from pathlib import Path
import json
import re
import struct
import unittest
from test_game_logic import function_source
import test_game_logic
import learnset_import

ROOT = Path(__file__).resolve().parents[2]


class ModernLearnsetTests(unittest.TestCase):
    compile_run = test_game_logic.GameLogicTests.compile_run
    # Reuse only the existing compiler helper.
    def test_wide_learnsets_and_all_native_consumers(self):
        self.assertTrue((ROOT / 'include/qol_learnsets.h').exists(),
                        'missing wide level-up learnset adapter for move IDs above 511')
        header = (ROOT / 'include/qol_learnsets.h').read_text()
        header = '\n'.join(line for line in header.splitlines()
                           if not line.startswith('#include'))
        adapter = (ROOT / 'src/qol_learnsets.c').read_text()
        adapter = '\n'.join(line for line in adapter.splitlines()
                            if not line.startswith('#include "') or 'data/' in line)
        actual = '\n'.join(function_source(path, name) for path, name in (
            ('src/pokemon.c', 'InitBoxMonMoveset'),
            ('src/pokemon.c', 'MonTryLearnMoveOnLevelUp'),
            ('src/pokemon.c', 'Species_LoadLearnsetTable'),
            ('src/move_relearner.c', 'MoveRelearner_GetEligibleLevelUpMoves'),
            ('src/get_egg.c', 'InheritMoves'),
            ('src/field/scrcmd_move_tutor.c', 'ScrCmd_MonLearnsetHasMove'),
        ))
        egg_source = (ROOT / 'src/get_egg.c').read_text()
        egg_struct = re.search(r'struct EggMoveSearch \{.*?\};', egg_source, re.S)[0]
        actual = egg_struct + '\n' + actual
        declarations = r'''
#include <assert.h>
#include <limits.h>
#include <stdlib.h>
#include <string.h>
#include "constants/pokemon.h"
#include "constants/moves.h"
#include "constants/species.h"
#include "constants/items.h"
#include "qol_config.h"
typedef unsigned char u8;
typedef unsigned short u16;
typedef unsigned int u32;
typedef int BOOL;
typedef int s32;
enum { FALSE, TRUE };
enum HeapID { HEAP_ID_DEFAULT, HEAP_ID_FIELD1, HEAP_ID_FIELD2 };
#define MAX_EGG_MOVES 16
#define MI_CpuClearFast(p,n) memset(p,0,n)
#define NELEMS(a) (sizeof(a) / sizeof((a)[0]))
#define LEVEL_UP_LEARNSET_END 0xffff
#define LEVEL_UP_LEARNSET_MOVE(x) ((x) & 511)
#define LEVEL_UP_LEARNSET_LVL(x) ((x) >> 9)
#define LEVEL_UP_LEARNSET_LEVEL_MASK 0xfe00
#define LEVEL_UP_LEARNSET_LEVEL_SHIFT 9
#define MOVE_APPEND_FULL 0xffff
#define MOVE_APPEND_KNOWN 0xfffe
typedef struct { u16 species, form, level, moves[4]; } BoxPokemon;
typedef struct { BoxPokemon box; } Pokemon;
static int largestLegacy, calledSpecies, calledForm;
static void *Heap_Alloc(enum HeapID heap, size_t size) {
    size_t *p = calloc(1,sizeof(size_t)+size+4); assert(p); *p=size;
    unsigned canary=0xdeadbeef; memcpy((char *)(p+1)+size,&canary,4); return p+1;
}
static void Heap_Free(void *p) {
    size_t *start=(size_t *)p-1; unsigned canary;
    memcpy(&canary,(char *)p+*start,4); assert(canary==0xdeadbeef); free(start);
}
static void *Heap_AllocAtEnd(enum HeapID heap, size_t size) { return Heap_Alloc(heap,size); }
static int GetBoxMonData(BoxPokemon *p, int field, void *unused) {
    if (field == MON_DATA_SPECIES) return p->species;
    if (field == MON_DATA_FORM) return p->form;
    if (field == MON_DATA_LEVEL) return p->level;
    assert(field >= MON_DATA_MOVE1 && field <= MON_DATA_MOVE4);
    return p->moves[field - MON_DATA_MOVE1];
}
static int GetMonData(Pokemon *p, int f, void *u) { return GetBoxMonData(&p->box, f, u); }
static BOOL AcquireBoxMonLock(BoxPokemon *p) { return FALSE; }
static void ReleaseBoxMonLock(BoxPokemon *p, BOOL lock) { }
static int CalcBoxMonLevel(BoxPokemon *p) { return p->level; }
static u32 TryAppendBoxMonMove(BoxPokemon *p, u16 move) {
    for (int i=0;i<4;i++) if (p->moves[i] == move) return MOVE_APPEND_KNOWN;
    for (int i=0;i<4;i++) if (!p->moves[i]) { p->moves[i] = move; return move; }
    return MOVE_APPEND_FULL;
}
static u32 TryAppendMonMove(Pokemon *p, u16 move) { return TryAppendBoxMonMove(&p->box, move); }
static void DeleteBoxMonFirstMoveAndAppend(BoxPokemon *p, u16 move) {
    memmove(p->moves,p->moves+1,3*sizeof(u16)); p->moves[3]=move;
}
BOOL Qol_IsSupportedMove(u16 move) {
    if(move<=467)return TRUE;
#if QOL_MODERN_MOVES
    switch(move) {
#define QOL_EXTRA_MOVE(id,e,c,p,t,a,pp,ch,r,pr,f,an) case id:return TRUE;
#include "data/qol_move_entries.inc"
#undef QOL_EXTRA_MOVE
    }
#endif
    return FALSE;
}
static void LoadLevelUpLearnset_HandleAlternateForm(int species, int form, u16 *dest) {
    calledSpecies=species; calledForm=form;
    if (largestLegacy) {
        // Exercise the full bounded legacy capacity, including missing sentinel.
        for(int i=0;i<MAX_LEARNED_MOVES;i++) dest[i]=((i+1)<<9)|(i+1);
    } else {
        dest[0]=(1<<9)|10; dest[1]=(20<<9)|20; dest[2]=(30<<9)|30;
        dest[3]=LEVEL_UP_LEARNSET_END;
    }
}
static void DeleteMonFirstMoveAndAppend(Pokemon *p, u16 move) { DeleteBoxMonFirstMoveAndAppend(&p->box,move); }
static int LoadEggMoves(Pokemon *p, u16 *dest) { return 0; }
static int TMHMGetMove(int item) { return MOVE_NONE; }
static BOOL GetTMHMCompatBySpeciesAndForm(int species, int form, int index) { return FALSE; }
typedef struct { void *saveData; } FieldSystem;
typedef struct { FieldSystem *fieldSystem; u16 vars[3]; int index; } ScriptContext;
static u16 ScriptGetVar(ScriptContext *ctx) { return ctx->vars[ctx->index++]; }
static u16 *ScriptGetVarPointer(ScriptContext *ctx) { return &ctx->vars[ctx->index++]; }
static Pokemon *SaveArray_Party_Get(void *save) { return save; }
typedef Pokemon Party;
static Pokemon *Party_GetMonByIndex(Pokemon *party, int slot) { return &party[slot]; }
u32 MonTryLearnMoveOnLevelUp(Pokemon *, int *, u16 *);
'''
        checks = r'''
static int contains(const QolLevelUpMove *table, int count, int move, int level) {
    for(int i=0;i<count;i++) if(table[i].move==move && table[i].level==level) return 1;
    return 0;
}
int main(void) {
    assert(sizeof(((struct EggMoveSearch *)0)->baby_learnset) / sizeof(u16) == 50);
    assert(QOL_LEVEL_UP_LEARNSET_CAPACITY <= 50);
    struct { QolLevelUpMove table[QOL_LEVEL_UP_LEARNSET_CAPACITY]; unsigned canary; } guarded;
    guarded.canary=0xa55aa55a;
    int n=Qol_LoadLevelUpLearnset(35,0,guarded.table);
    assert(contains(guarded.table,n,10,1));
    assert(contains(guarded.table,n,20,20));
    assert(contains(guarded.table,n,30,30));
    assert(contains(guarded.table,n,577,1)==QOL_MODERN_MOVES);
    assert(contains(guarded.table,n,588,44)==QOL_MODERN_MOVES);
    assert(guarded.table[n].move==LEVEL_UP_LEARNSET_END);
    assert(guarded.canary==0xa55aa55a);
    for(int i=1;i<n;i++) assert(guarded.table[i-1].level<=guarded.table[i].level);
    n=Qol_LoadLevelUpLearnset(40,0,guarded.table);
    assert(contains(guarded.table,n,586,5)==QOL_MODERN_MOVES);
    n=Qol_LoadLevelUpLearnset(282,0,guarded.table);
    assert(contains(guarded.table,n,580,12)==QOL_MODERN_MOVES);
    assert(contains(guarded.table,n,608,0)==QOL_MODERN_MOVES);
    const int additions[][3]={{252,3,673},{143,40,670},{22,45,532},{78,0,687},
        {475,1,898},{383,1,622},{382,1,621},{3,0,575},{295,72,589},{303,4,587}};
    for(unsigned a=0;a<NELEMS(additions);a++) {
        n=Qol_LoadLevelUpLearnset(additions[a][0],0,guarded.table);
        assert(contains(guarded.table,n,additions[a][2],additions[a][1])==QOL_MODERN_MOVES);
    }
    // Every alternate form stays on its native/form-only table.
    for(int form=1;form<32;form++) {
        n=Qol_LoadLevelUpLearnset(35,form,guarded.table);
        assert(n==3 && calledSpecies==35 && calledForm==form);
    }
    for(int species=494;species<=507;species++) assert(Qol_LoadLevelUpLearnset(species,0,guarded.table)==3);
    // The widest legacy table remains bounded, with a terminator after additions.
    largestLegacy=1;
    for(int species=1;species<=493;species++) {
        n=Qol_LoadLevelUpLearnset(species,0,guarded.table);
        assert(n>=22 && n<QOL_LEVEL_UP_LEARNSET_CAPACITY);
        assert(guarded.table[n].move==LEVEL_UP_LEARNSET_END);
        assert(guarded.canary==0xa55aa55a);
    }
    Pokemon mon={{282,0,100,{0}}}; // Gardevoir has all five imported wide IDs.
    u16 *eligible=MoveRelearner_GetEligibleLevelUpMoves(&mon,HEAP_ID_DEFAULT);
    int k=0; while(eligible[k]!=LEVEL_UP_LEARNSET_END) { assert(k<28); k++; }
    assert(k==(QOL_MODERN_MOVES?27:22));
    int supported[]={577,580,588,608,598};
    for(int j=0;j<5;j++) {
        int found=0;
        for(int i=0;i<k;i++) found|=eligible[i]==supported[j];
        assert(found==QOL_MODERN_MOVES);
    }
    Heap_Free(eligible);
    largestLegacy=0;
    for(int level=2;level<=3;level++) {
        mon=(Pokemon){{252,0,level,{0}}};
        eligible=MoveRelearner_GetEligibleLevelUpMoves(&mon,HEAP_ID_DEFAULT);
        int leafage=0;
        for(k=0;eligible[k]!=LEVEL_UP_LEARNSET_END;k++) leafage|=eligible[k]==673;
        assert(leafage==(QOL_MODERN_MOVES && level==3)); Heap_Free(eligible);
    }
    mon=(Pokemon){{35,0,44,{0}}};
    InitBoxMonMoveset(&mon.box);
    assert(mon.box.moves[0]==(QOL_MODERN_MOVES?577:10));
    assert(mon.box.moves[1]==20 && mon.box.moves[2]==30);
    assert(mon.box.moves[3]==(QOL_MODERN_MOVES?588:0));
    mon=(Pokemon){{35,0,44,{0}}};
    int cursor=0; u16 move=0;
    assert(MonTryLearnMoveOnLevelUp(&mon,&cursor,&move)==(QOL_MODERN_MOVES?588:0));
    if(QOL_MODERN_MOVES) assert(move==588);
    assert(MonTryLearnMoveOnLevelUp(&mon,&cursor,&move)==0);
    cursor=INT_MAX; assert(MonTryLearnMoveOnLevelUp(&mon,&cursor,&move)==0);
    cursor=-1; assert(MonTryLearnMoveOnLevelUp(&mon,&cursor,&move)==0);
    mon=(Pokemon){{40,0,4,{0}}};
    eligible=MoveRelearner_GetEligibleLevelUpMoves(&mon,HEAP_ID_DEFAULT);
    for(k=0;eligible[k]!=LEVEL_UP_LEARNSET_END;k++) assert(eligible[k]!=586);
    Heap_Free(eligible);
    mon.box.level=5;
    eligible=MoveRelearner_GetEligibleLevelUpMoves(&mon,HEAP_ID_DEFAULT);
    int rough=0;
    for(k=0;eligible[k]!=LEVEL_UP_LEARNSET_END;k++) rough|=eligible[k]==586;
    assert(rough==QOL_MODERN_MOVES); Heap_Free(eligible);
    // A modern evolution move is offered on evolution, then skipped on later level-ups.
    mon=(Pokemon){{282,0,30,{0}}}; cursor=0;
    assert(Qol_MonTryLearnMoveAfterEvolution(&mon,&cursor,&move)==(QOL_MODERN_MOVES?608:30));
    if(QOL_MODERN_MOVES) assert(move==608);
    mon=(Pokemon){{282,0,31,{0}}}; cursor=0;
    assert(MonTryLearnMoveOnLevelUp(&mon,&cursor,&move)==0);
    // Species move list consumed by daycare keeps the full u16 move IDs and bounds.
    struct { u16 moves[QOL_LEVEL_UP_LEARNSET_CAPACITY]; u16 canary; } daycare;
    daycare.canary=0x1234;
    n=Species_LoadLearnsetTable(35,0,daycare.moves);
    int voice=0, moon=0;
    for(int i=0;i<n;i++) { voice|=daycare.moves[i]==577; moon|=daycare.moves[i]==588; }
    assert(voice==QOL_MODERN_MOVES && moon==QOL_MODERN_MOVES);
    assert(daycare.canary==0x1234);
    mon=(Pokemon){{35,0,44,{577,0,0,0}}};
    eligible=MoveRelearner_GetEligibleLevelUpMoves(&mon,HEAP_ID_DEFAULT);
    k=0; int found=0;
    while(eligible[k]!=LEVEL_UP_LEARNSET_END) { assert(eligible[k]!=577); found|=eligible[k]==588; assert(++k<28); }
    assert(found==QOL_MODERN_MOVES); Heap_Free(eligible);
    // Actual daycare inheritance scans the species list for shared parent moves.
    BoxPokemon father={35,0,100,{577,588,0,0}}, mother=father;
    mon=(Pokemon){{35,0,1,{0}}};
    InheritMoves(&mon,&father,&mother);
    assert(mon.box.moves[0]==(QOL_MODERN_MOVES?577:0));
    assert(mon.box.moves[1]==(QOL_MODERN_MOVES?588:0));
    // Actual script caller also allocates enough for the largest species table.
    largestLegacy=1;
    FieldSystem field={&mon};
    ScriptContext ctx={&field,{0,588,0},0};
    ScrCmd_MonLearnsetHasMove(&ctx);
    assert(ctx.vars[2]==QOL_MODERN_MOVES);
    return 0;
}
'''
        for enabled in (0, 1):
            with self.subTest(enabled=enabled):
                self.compile_run(declarations+header+'\n'+adapter+'\n'+actual+checks,
                                 f'-DQOL_MODERN_MOVES={enabled}')

    def test_generated_overlay_reproduces_pinned_profile(self):
        data = (ROOT / 'include/data/qol_learnsets.inc').read_text()
        entries = [tuple(map(int, row)) for row in
                   re.findall(r'QOL_LEVEL_UP_MOVE\((\d+), (\d+), (\d+)\)', data)]
        self.assertEqual(len(entries), 209)
        self.assertEqual(len({s for s, _, _ in entries}),160)
        self.assertIn((133,15,611),entries)
        self.assertEqual({m for _, _, m in entries}, set(learnset_import.SUPPORTED) - {506,530,615,696,709,787,809,815,818,831,854,887,889})
        from test_modern_next_moves import IDS
        self.assertEqual(set(learnset_import.SUPPORTED), {577,580,586,588,608,587,673,670,696,532,687,898,622,621,575,589,854} | IDS)
        self.assertIn((383, 1, 622), entries)
        self.assertIn((295, 72, 589), entries)
        self.assertIn((475, 1, 898), entries)
        self.assertIn((282, 0, 608), entries)
        from collections import Counter
        self.assertEqual(max(Counter(species for species, _, _ in entries).values()), 5)
        profile = ROOT / '.local-tools/validation/gen9-import-profile.json'
        if profile.exists():
            self.assertEqual(learnset_import.generate(json.loads(profile.read_text())), data)

    def test_generator_checks_precipice_source_spelling_before_restoring_official_name(self):
        profile_path=ROOT/'.local-tools/validation/gen9-import-profile.json'
        if not profile_path.exists():
            self.skipTest('Needs pinned import profile')
        profile=json.loads(profile_path.read_text())
        move=next(m for m in profile['moves'] if m['engine_id']==622)
        move['caps_name']='SOME OTHER MOVE'
        with self.assertRaises(ValueError):
            learnset_import.generate(profile)

    def test_native_legacy_members_fit_temporary_buffer(self):
        narc = (ROOT / 'files/poketool/personal/wotbl.narc').read_bytes()
        start = narc.index(b'BTAF')
        count = struct.unpack_from('<H', narc, start + 8)[0]
        for index in range(count):
            begin, end = struct.unpack_from('<II', narc, start + 12 + index * 8)
            self.assertLessEqual(end - begin, 22 * 2, f'legacy member {index}')

    def test_native_list_destinations_have_capacity(self):
        daycare = (ROOT / 'src/get_egg.c').read_text()
        capacity = re.search(r'baby_learnset\[(\d+)\]', daycare)
        self.assertIsNotNone(capacity)
        self.assertGreaterEqual(int(capacity[1]), 28)
        tutor = function_source('src/field/scrcmd_move_tutor.c', 'ScrCmd_MonLearnsetHasMove')
        self.assertIn('QOL_LEVEL_UP_LEARNSET_CAPACITY * sizeof(u16)', tutor)


if __name__ == '__main__':
    unittest.main()
