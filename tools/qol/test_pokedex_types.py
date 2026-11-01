"""Run the real Pokédex filter and controls against independent roster data."""
import json
from pathlib import Path
import re
import unittest

import test_game_logic as game

ROOT = Path(__file__).resolve().parents[2]
DEX = 'src/application/pokedex/'
# Search selectors deliberately exclude type slot 9 and retain ALL/OK/CANCEL.
FAIRY_SELECTOR = 20
CHANGES = {
    'CLEFAIRY': (9, 9), 'CLEFABLE': (9, 9), 'CLEFFA': (9, 9),
    'JIGGLYPUFF': (0, 9), 'WIGGLYTUFF': (0, 9), 'IGGLYBUFF': (0, 9),
    'MR_MIME': (14, 9), 'TOGEPI': (9, 9), 'TOGETIC': (9, 2),
    'MARILL': (11, 9), 'AZUMARILL': (11, 9), 'SNUBBULL': (9, 9),
    'GRANBULL': (9, 9), 'RALTS': (14, 9), 'KIRLIA': (14, 9),
    'GARDEVOIR': (14, 9), 'AZURILL': (0, 9), 'MAWILE': (8, 9),
    'MIME_JR': (14, 9), 'TOGEKISS': (9, 2),
}
COMMON = r'''
#include <assert.h>
#include <stdlib.h>
#include <string.h>
#include <stdio.h>
#include "qol_config.h"
#include "constants/pokemon.h"
#include "constants/species.h"
typedef unsigned char u8;typedef unsigned short u16;typedef unsigned int u32;
typedef signed int s32;typedef int BOOL;
#define TRUE 1
#define FALSE 0
#define GF_ASSERT assert
#define GF_AssertFail() assert(0)
#define NELEMS(a) (sizeof(a)/sizeof((a)[0]))
''' + (ROOT / DEX / 'pokedex_modern_types.h').read_text()


def constants():
    # Keep real archive-derived selector constants, without SDK include paths.
    header = (ROOT / 'include/application/pokedex/pokedex_internal_constants.h').read_text()
    return ((ROOT / 'files/application/zukanlist/zkn_data/zukan_data.naix').read_text()
            + '\n' + '\n'.join(line for line in header.splitlines() if not line.startswith('#include'))
            + '\n')


def table(source, name):
    return re.search(r'static const [\w ]+ ' + name + r'\[[^=]*=\s*\{.*?\};', source, re.S)[0]


class PokedexTypeTests(unittest.TestCase):
    compile_run = game.GameLogicTests.compile_run

    def test_filters_all_species_and_both_selectors_using_current_personal_types(self):
        rows = json.loads((ROOT / 'files/poketool/personal/personal.json').read_text())['baseStats'][:494]
        self.assertEqual(len(rows), 494)
        original = 'static const u8 original[494][2] = {' + ','.join(
            '{' + ','.join(row['types']) + '}' for row in rows) + '};\n'
        expected = 'static const u8 modern[494][2] = {' + ','.join(
            '{' + ','.join(map(str, CHANGES[row['species']])) + '}' if row['species'] in CHANGES
            else '{' + ','.join(row['types']) + '}' for row in rows) + '};\n'
        # Execute the real personal loader too; only its archive read is replaced.
        loader = game.function_source('src/pokemon.c', 'Qol_ApplyModernMonTypes')
        loader = '\n#if QOL_MODERN_TYPES\n' + loader + '\n#endif\n'
        loader += game.function_source('src/pokemon.c', 'LoadMonPersonal')
        actual = '\n'.join(game.function_source(DEX + 'pokedex_search.c', name) for name in (
            'PokedexApp_IdentityU32', 'PokedexApp_IntersectSpeciesLists', 'PokedexApp_FilterByType'))
        stubs = r'''
typedef struct {u8 types[2];} BASE_STATS;
typedef struct {u8 caught[494];} Pokedex;
#define NARC_poketool_personal_personal 0
void ReadWholeNarcMemberByIdPair(BASE_STATS *p,int narc,int species) {
 assert(species>=1&&species<=493);memcpy(p->types,original[species],2);
}
int Pokedex_CheckMonCaughtFlag(const Pokedex *p,int species) {return p->caught[species];}
void Heap_Free(void *p) {free(p);}
void *PokedexApp_LoadSortData(u32 index,u32 *count) {
 int selector=index-DEX_SORT_FILE(NARC_zukan_data_sort_order_types_normal);
 assert(selector>=0&&selector<17);
 int type=selector>=9?selector+1:selector;
 u16 *data=malloc(493*sizeof(u16));*count=0;
 for(int species=1;species<=493;species++)
  if(original[species][0]==type||original[species][1]==type)data[(*count)++]=species;
 return data;
}
'''
        checks = r'''
int Expected(int species,int selector) {
 if(selector==DEX_SEARCH_TYPE_ALL)return 1;
 int type=selector==20?9:(selector>=9?selector+1:selector);
 const u8 (*pairs)[2]=QOL_MODERN_TYPES?modern:original;
 return pairs[species][0]==type||pairs[species][1]==type;
}
int main(void) {
 Pokedex dex={{0}};u16 src[493],first[493],second[493];u32 n,m;
 // Reverse order detects re-sorting, and a second pass excludes uncaught species.
 for(int i=0;i<493;i++)src[i]=493-i;
 for(int caught=0;caught<2;caught++) {
  for(int species=1;species<=493;species++)dex.caught[species]=!caught||species%3;
  for(int a=0;a<(QOL_MODERN_TYPES?19:18);a++) {
   int one=a==18?20:a;n=99;
   PokedexApp_FilterByType(one,first,&n,src,493,&dex);
   unsigned want=0;
   for(int i=0;i<493;i++)if(Expected(src[i],one)&&(one==17||dex.caught[src[i]])) {
    if(want>=n||first[want]!=src[i])fprintf(stderr,"selector=%d missing species=%d\n",one,src[i]);
    assert(want<n&&first[want++]==src[i]);
   }
   assert(n==want);
   for(int b=0;b<(QOL_MODERN_TYPES?19:18);b++) {
    int two=b==18?20:b;m=99;
    PokedexApp_FilterByType(two,second,&m,first,n,&dex);want=0;
    for(int i=0;i<493;i++)if(Expected(src[i],one)&&Expected(src[i],two)
       &&((one==17&&two==17)||dex.caught[src[i]]))assert(want<m&&second[want++]==src[i]);
    assert(m==want);
   }
  }
 }
 return 0;
}
'''
        for enabled in (0, 1):
            with self.subTest(enabled=enabled):
                self.compile_run(COMMON + constants() + original + expected + stubs + loader + actual + checks,
                                 f'-DQOL_MODERN_TYPES={enabled}')

    def test_grid_contains_fairy_and_all_navigation_targets_are_bounded(self):
        source = (ROOT / DEX / 'pokedex_input.c').read_text()
        tables = '\n'.join(table(source, name) for name in (
            'sSearchTypeHitboxes', 'sSearchTypeDpadBoxes', 'sSearchTypeCursorAnims'))
        declarations = r'''
typedef union {struct {u8 top,bottom,left,right;} rect;} TouchscreenHitbox;
typedef struct {u8 left,top,width,height,buttonUp,buttonDown,buttonLeft,buttonRight;} DpadMenuBox;
#define TOUCHSCREEN_RECTLIST_END 255
'''
        checks = r'''
int main(void) {
 unsigned count=QOL_MODERN_TYPES?21:20;
 assert(NELEMS(sSearchTypeDpadBoxes)==count);
 assert(NELEMS(sSearchTypeCursorAnims)==count);
 assert(NELEMS(sSearchTypeHitboxes)==count+1);
 assert(sSearchTypeHitboxes[count].rect.top==255);
 int reached[21]={1};
 for(unsigned pass=0;pass<count;pass++)for(unsigned i=0;i<count;i++) {
  const DpadMenuBox *b=&sSearchTypeDpadBoxes[i];
  const u8 links[]={b->buttonUp,b->buttonDown,b->buttonLeft,b->buttonRight};
  for(int d=0;d<4;d++){assert(links[d]<count);if(reached[i])reached[links[d]]=1;}
  const TouchscreenHitbox *h=&sSearchTypeHitboxes[i];
  assert(b->left>=h->rect.left&&b->left<=h->rect.right);
  assert(b->top>=h->rect.top&&b->top<=h->rect.bottom);
  assert(sSearchTypeCursorAnims[i]==(i==18||i==19?35:38));
 }
 for(unsigned i=0;i<count;i++)assert(reached[i]);
 assert(sSearchTypeDpadBoxes[18].top==176&&sSearchTypeDpadBoxes[19].top==176);
 if(QOL_MODERN_TYPES)assert(sSearchTypeDpadBoxes[20].left==160&&sSearchTypeDpadBoxes[20].top==144);
 return 0;
}
'''
        for enabled in (0, 1):
            with self.subTest(enabled=enabled):
                self.compile_run(COMMON + declarations + tables + checks, f'-DQOL_MODERN_TYPES={enabled}',
                                 '-Wno-missing-field-initializers', '-Wno-array-bounds')

    def test_cancel_navigation_returns_to_fairy_column(self):
        actual = game.function_source(DEX + 'pokedex_input.c', 'PokedexApp_OnSearchTypeGridMove')
        declarations = r'''
typedef struct {int prevGridInput;void *gridInput;} PokedexAppData;
static int cursor,next,last,ret;
void GridInputHandler_SetNextLastReturnInputs(void *g,int n,int l,int r){next=n;last=l;ret=r;}
void PokedexApp_UpdateSearchTypeCursor(PokedexAppData *p,int target){assert(target>=0&&target<(QOL_MODERN_TYPES?21:20));cursor=target;}
#define SEQ_SE_GS_ZKN03 1
void PlaySE(int sound){}
'''
        checks = r'''
int main(void) {
 PokedexAppData app={0};
 app.prevGridInput=2;
 PokedexApp_OnSearchTypeGridMove(&app,15,19);
 assert(cursor==(QOL_MODERN_TYPES?20:14));
 assert(next==cursor&&last==19&&ret==19&&app.prevGridInput==19);
 if(QOL_MODERN_TYPES) {
  app.prevGridInput=20;PokedexApp_OnSearchTypeGridMove(&app,3,19);
  assert(cursor==2&&next==2);
  app.prevGridInput=20;PokedexApp_OnSearchTypeGridMove(&app,15,19);
  assert(cursor==20&&next==20);
 }
 return 0;
}
'''
        for enabled in (0, 1):
            self.compile_run(COMMON + declarations + actual + checks, f'-DQOL_MODERN_TYPES={enabled}')

    def test_select_both_types_start_submit_and_cancel_restore_criteria(self):
        actual = game.function_source(DEX + 'pokedex_input.c', 'PokedexApp_HandleSearchTypeInput')
        actual += game.function_source(DEX + 'pokedex_main_seq.c', 'PokedexApp_MainSeq_35')
        declarations = r'''
typedef struct {void *menuInputStatePtr;} Args;
typedef int Window;
typedef struct {Args *args;void *gridInput;u32 dexSearchCriteria[10],dexSearchCriteriaBak[2];Window windows[101];} PokedexAppData;
static struct {int newKeys;} gSystem;
static int chosen,flash;
#define PAD_BUTTON_START 8
#define MENU_INPUT_STATE_BUTTONS 0
#define SEQ_SE_GS_ZKN04 0
#define SEQ_SE_GS_GEARCANCEL 1
#define POKEDEXAPP_MAINSEQ_35 35
#define POKEDEXAPP_MAINSEQ_36 36
void MenuInputStateMgr_SetState(void *p,int state){}
int MenuInputStateMgr_GetState(void *p){return 0;}
int GridInputHandler_HandleInput_AllowHold(void *p){return chosen;}
void PlaySE(int sound){}
void PokedexApp_HighlightSearchTypes(PokedexAppData *p){}
void PokedexApp_DrawSearchTypeValue(PokedexAppData *p,u32 type,u32 w,s32 x){assert(type<=17||(QOL_MODERN_TYPES&&type==20));}
void ScheduleWindowCopyToVram(Window *w){}
int PokedexApp_FlashSearchButton(PokedexAppData *p,int button,int frames,int seq){flash=button;return seq;}
'''
        checks = r'''
int main(void) {
 Args args={0};PokedexAppData app={0};app.args=&args;
 int target=QOL_MODERN_TYPES?20:0;
 app.dexSearchCriteria[2]=17;app.dexSearchCriteria[3]=17;
 chosen=target;assert(PokedexApp_MainSeq_35(&app)==35);
 assert(app.dexSearchCriteria[2]==(u32)target&&app.dexSearchCriteria[3]==17);
 chosen=11;PokedexApp_MainSeq_35(&app);assert(app.dexSearchCriteria[3]==11);
 chosen=target;PokedexApp_MainSeq_35(&app);
 assert(app.dexSearchCriteria[2]==11&&app.dexSearchCriteria[3]==(u32)target);
 chosen=target;PokedexApp_MainSeq_35(&app);assert(app.dexSearchCriteria[2]==11);
 chosen=17;PokedexApp_MainSeq_35(&app);assert(app.dexSearchCriteria[2]==11&&app.dexSearchCriteria[3]==17);
 chosen=17;PokedexApp_MainSeq_35(&app);assert(app.dexSearchCriteria[2]==17&&app.dexSearchCriteria[3]==17);
 app.dexSearchCriteria[2]=target;app.dexSearchCriteria[3]=target;
 gSystem.newKeys=PAD_BUTTON_START;assert(PokedexApp_MainSeq_35(&app)==36);
 assert(flash==0&&app.dexSearchCriteria[2]==(u32)target&&app.dexSearchCriteria[3]==17);
 gSystem.newKeys=0;
 for(int i=0;i<2;i++) {
  app.dexSearchCriteriaBak[0]=target;app.dexSearchCriteriaBak[1]=11;
  app.dexSearchCriteria[2]=0;app.dexSearchCriteria[3]=17;
  chosen=i?-2:19;assert(PokedexApp_MainSeq_35(&app)==36);
  assert(flash==22&&app.dexSearchCriteria[2]==(u32)target&&app.dexSearchCriteria[3]==11);
 }
 return 0;
}
'''
        for enabled in (0, 1):
            self.compile_run(COMMON + constants() + declarations + actual + checks,
                             f'-DQOL_MODERN_TYPES={enabled}')

    def test_fairy_labels_use_transformed_type_name_and_reuse_existing_window(self):
        source = (ROOT / DEX / 'pokedex_windows.c').read_text()
        tables = '\n'.join(table(source, name) for name in ('sSearchTypeMsgIds', 'sSearchWindowTemplates'))
        helper = ''
        if 'static void PokedexApp_PrintSearchFairy' in source:
            helper = '\n#if QOL_MODERN_TYPES\n' + game.function_source(DEX + 'pokedex_windows.c', 'PokedexApp_PrintSearchFairy') + '\n#endif\n'
        actual = game.function_source(DEX + 'pokedex_windows.c', 'PokedexApp_DrawSearchTypeValue')
        actual += game.function_source(DEX + 'pokedex_windows.c', 'PokedexApp_DrawSearchTypePage')
        declarations = r'''
typedef struct {u8 bgId,left,top,width,height,palette;u16 baseTile;} WindowTemplate;
#define GF_BG_LYR_SUB_1 5
#define GF_BG_LYR_MAIN_0 0
#define GF_BG_LYR_MAIN_1 1
#define MAKE_TEXT_COLOR(a,b,c) 0
#define MSGDATA_LOAD_LAZY 0
#define NARC_msgdata_msg 0
#define NARC_msg_msg_0735_bin 735
#define HEAP_ID_POKEDEX_APP 0
#define msg_0802_00028 28
#define msg_0802_00039 39
#define msg_0802_00040 40
typedef struct {int bank;} MsgData;
typedef struct {int marker;} Window;
typedef struct {int bank,id;} String;
typedef struct {Window windows[101];MsgData *msgData;void *bgConfig;u32 dexSearchCriteria[10];} PokedexAppData;
static int bank,id,xpos,cleared,fairyCell,allCell,copies;
static struct {u16 ids[18];WindowTemplate templates[13];} legacyMsgLayout;
// Simulate the original contiguous rodata layout used by the page's pointer.
#define sSizeCheckWindowTemplates legacyMsgLayout.templates
void FillWindowPixelBuffer(Window *w,int v){cleared++;}
int GetWindowWidth(Window *w){return 8;}
void PokedexApp_PrintMessage(Window *w,MsgData *m,int msg,int x,int y,int f,int c,int a){bank=m->bank;id=msg;xpos=x;if(w->marker==64&&bank==735&&id==9&&x==96)fairyCell++;if(w->marker==64&&bank==802&&id==64&&x==32)allCell++;}
void PokedexApp_ClearBgTilemap(PokedexAppData *p,int layer){}
void PokedexApp_DrawSearchButton(PokedexAppData *p,int w,int msg){}
void ScheduleWindowCopyToVram(Window *w){copies++;}
MsgData *NewMsgDataFromNarc(int mode,int narc,int group,int heap){MsgData *m=malloc(sizeof(*m));m->bank=group;return m;}
void DestroyMsgData(MsgData *m){free(m);}
String *NewString_ReadMsgData(MsgData *m,int msg){String *s=malloc(sizeof(*s));s->bank=m->bank;s->id=msg;return s;}
void PokedexApp_PrintString(Window *w,String *s,int x,int y,int f,int c,int a){bank=s->bank;id=s->id;xpos=x;}
void String_Delete(String *s){free(s);}
'''
        checks = r'''
int main(void) {
 MsgData m={802};PokedexAppData app={0};app.msgData=&m;
 for(int i=0;i<101;i++)app.windows[i].marker=i;
 const WindowTemplate *all=&sSearchWindowTemplates[64];
 assert(NELEMS(sSearchWindowTemplates)==101);
 assert(all->left==8&&all->top==17&&all->height==2);
 assert(all->width==(QOL_MODERN_TYPES?16:8));
 assert(all->baseTile==(QOL_MODERN_TYPES?0xA2:0xB2));
 // The preceding final-row window ends exactly at the widened window's end.
 assert(all->baseTile+all->width*2==sSearchWindowTemplates[63].baseTile);
 for(unsigned type=0;type<18;type++) {
  PokedexApp_DrawSearchTypeValue(&app,type,45,29);
  assert(bank==802&&id==sSearchTypeMsgIds[type]&&xpos==29);
 }
 if(QOL_MODERN_TYPES) {
  PokedexApp_DrawSearchTypeValue(&app,20,45,29);assert(bank==735&&id==9&&xpos==29);
  PokedexApp_DrawSearchTypeValue(&app,20,46,-1);assert(bank==735&&id==9&&xpos==32);
 }
 assert(cleared==(QOL_MODERN_TYPES?20:18));
 memcpy(legacyMsgLayout.ids,sSearchTypeMsgIds,sizeof(sSearchTypeMsgIds));
 app.dexSearchCriteria[2]=QOL_MODERN_TYPES?20:0;app.dexSearchCriteria[3]=17;
 PokedexApp_DrawSearchTypePage(&app);
 assert(fairyCell==QOL_MODERN_TYPES&&allCell==1&&copies==21);
 return 0;
}
'''
        for enabled in (0, 1):
            self.compile_run(COMMON + constants() + declarations + tables + helper + actual + checks,
                             f'-DQOL_MODERN_TYPES={enabled}')

    def test_fairy_selection_highlights_a_real_background_cell(self):
        source = (ROOT / DEX / 'pokedex_screen_setup.c').read_text()
        actual = game.function_source(DEX + 'pokedex_screen_setup.c', 'PokedexApp_HighlightSearchTypes')
        declarations = r'''
typedef struct {int x,y,width,height;} PokedexBgRect;
typedef struct {u32 dexSearchCriteria[10];void *bgConfig;} PokedexAppData;
static u16 tiles[32*24];static int highlighted[24][32];
#define GF_BG_LYR_MAIN_2 2
u16 *GetBgTilemapBuffer(void *c,int layer){return tiles;}
void MI_CpuCopy16(const void *src,void *dst,int n){memcpy(dst,src,n);}
void PokedexApp_HighlightSearchOption(PokedexAppData *p,const PokedexBgRect *r,BOOL h) {
 assert(r->x>=0&&r->x+r->width<=32&&r->y>=0&&r->y+r->height<=24);
 for(int y=r->y;y<r->y+r->height;y++)for(int x=r->x;x<r->x+r->width;x++)highlighted[y][x]=h;
}
'''
        checks = r'''
int main(void) {
 PokedexAppData app={0};app.dexSearchCriteria[2]=0;app.dexSearchCriteria[3]=17;
 for(int y=17;y<19;y++)for(int x=8;x<16;x++)tiles[y*32+x]=x+y*32;
 PokedexApp_HighlightSearchTypes(&app);assert(highlighted[5][0]&&highlighted[17][8]);
 if(QOL_MODERN_TYPES) {
  app.dexSearchCriteria[2]=20;app.dexSearchCriteria[3]=14;PokedexApp_HighlightSearchTypes(&app);
  assert(highlighted[17][16]&&highlighted[14][16]&&!highlighted[17][8]&&!highlighted[5][0]);
  for(int y=17;y<19;y++)for(int x=16;x<24;x++)assert(tiles[y*32+x]==tiles[y*32+x-8]);
 }
 return 0;
}
'''
        for enabled in (0, 1):
            self.compile_run(COMMON + constants() + declarations + table(source, 'sSearchTypeOptionRects') + actual + checks,
                             f'-DQOL_MODERN_TYPES={enabled}', '-Wno-sign-compare')


if __name__ == '__main__':
    unittest.main()
