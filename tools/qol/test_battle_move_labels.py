"""Host-execute real move metadata, card labels and the literal FIGHT builder.

Only NARC/message/font/allocation and preview SDK boundaries are supplied here.
No SDK assembler, Wine, game build or native frontend is imported or invoked.
"""
from pathlib import Path
import re
import struct
import unittest
import xml.etree.ElementTree as ET

import test_game_logic as game
import test_modern_moves
from game_text import game_text
from move_resources import PRESENTATION
from nitro_data import unpack_narc

ROOT = Path(__file__).resolve().parents[2]
INPUT = 'src/battle/battle_input.c'


def array(name, values, ctype='u16'):
    return f'static const {ctype} {name}[]={{' + ','.join(map(str, values)) + '};\n'


def metadata_source():
    if not (ROOT / 'files/a/0/1/1').exists():
        raise unittest.SkipTest('Requires the locally supplied move archive')
    members, _ = unpack_narc((ROOT / 'files/a/0/1/1').read_bytes())
    data = b''.join(members[:468])
    assert len(data) == 468 * 16
    return test_modern_moves.ModernMoveTests().source() + array('moveBytes', data, 'u8') + r'''
#include <stdlib.h>
#include <stdio.h>
#include "constants/charcode.h"
#include "constants/battle_menu.h"
enum { NARC_poketool_waza_waza_tbl };
static int archiveReads;
static void ReadFromNarcMemberByIdPair(void *d,int n,int m,int o,int len) {
    assert(o==0 && len==(int)sizeof(moveBytes));memcpy(d,moveBytes,len);
}
static void ReadWholeNarcMemberByIdPair(void *d,int n,int m) {
    assert(m>=0 && m<=NUM_MOVES);archiveReads++;memcpy(d,moveBytes+m*16,16);
}
''' + test_modern_moves.no_includes((ROOT / 'src/move.c').read_text()) + r'''
typedef struct {u16 words[64];} String;
static int strings;
static String *String_New(int n,int heap) {
    assert(n<=64);String *s=calloc(1,sizeof(*s));assert(s);s->words[0]=EOS;strings++;return s;
}
static void String_Delete(String *s) {assert(s);strings--;free(s);}
static void CopyU16ArrayToString(String *s,const u16 *p) {
    int i=0;do {assert(i<64);s->words[i]=p[i];} while(p[i++]!=EOS);
}
typedef struct {int hp;} BattleMon;
typedef struct {BattleMon battleMons[4];} BattleContext;
typedef struct {BattleContext ctx;int battlers;} BattleSystem;
typedef struct {u16 moveNo[4];u8 pp[4],ppMax[4];} BattleInputFightMenu;
typedef struct {BattleSystem *battleSystem;int battlerType;struct {BattleInputFightMenu fight;} menu;void *ssWindow,*ssCursor;} BattleInput;
enum {HEAP_ID_BATTLE,MSGDATA_LOAD_LAZY,NARC_msgdata_msg,NARC_msg_msg_0735_bin=735,
      msg_0197_00938=938,msg_0197_00937=937,PRINTING_MODE_RIGHT_ALIGN,SS_MENU_FIGHT=4};
static BattleContext *BattleSystem_GetBattleContext(BattleSystem *s){return &s->ctx;}
static int BattleSystem_GetBattlerFromBattlerType(BattleSystem *s,int t){return t;}
static int BattleSystem_GetMaxBattlers(BattleSystem *s){return s->battlers;}
static int BattleSystem_GetFieldSide(BattleSystem *s,int t){return t&1;}
static int preview=-1,previews,lastTarget;
static int Qol_PreviewTypeEffectiveness(BattleContext *c,u16 move,int a,int t){previews++;lastTarget=t;return preview;}
'''


def label_source():
    return metadata_source() + game.function_source(INPUT, 'BattleInput_SingleScreen_Effectiveness')


def builder_source():
    for asset in ('files/graphic/font/font_00000000.bin', 'files/msgdata/msg/msg_0735.gmm',
                  'files/msgdata/msg/msg_0750.gmm'):
        if not (ROOT / asset).exists():
            raise unittest.SkipTest('Requires the locally supplied font and message assets')
    source = (ROOT / INPUT).read_text()
    item = re.search(r'typedef struct SingleScreenMenuItem \{.*?\} SingleScreenMenuItem;', source, re.S)[0]
    builder = game.function_source(INPUT, 'BattleInput_SingleScreen_BuildItems')
    # Copy the literal production branch, including its feature guards and break.
    fight = builder[builder.index('    case SS_MENU_FIGHT: {'):builder.index('    case SS_MENU_TARGET: {')]
    font = (ROOT / 'files/graphic/font/font_00000000.bin').read_bytes()
    widths = font[struct.unpack_from('<I', font, 4)[0]:]
    encoded = []
    cases = []
    for bank in (735, 750):
        rows = ET.parse(ROOT / f'files/msgdata/msg/msg_{bank:04}.gmm').getroot().findall('row')
        for index, row in enumerate(rows):
            text = row.find('language').text or ''
            if bank == 750 and index not in (33, 43, 67, 84):
                continue
            words = game_text(text, ROOT / 'charmap.txt')
            name = f'text{bank}_{index}'
            encoded.append(array(name, words))
            cases.append(f'case {bank*1000+index}:CopyU16ArrayToString(s,{name});break;')
    for move, presentation in PRESENTATION.items():
        encoded.append(array(f'card{move}', game_text(presentation['card'], ROOT / 'charmap.txt')))
        cases.append(f'case {829000+move}:CopyU16ArrayToString(s,card{move});break;')
    return metadata_source() + array('widths', widths, 'u8') + '\n'.join(encoded) + r'''
typedef struct {int bank;} MsgData;
typedef struct {int values[2];} MessageFormat;
static MsgData bank;static MessageFormat fmt;
static MsgData *BattleSystem_GetMessageLoader(BattleSystem *s){static MsgData m={197};return &m;}
static MessageFormat *BattleSystem_GetMessageFormat(BattleSystem *s){return &fmt;}
static u32 BattleSystem_GetBattleType(BattleSystem *s){return 0;}
static MsgData *NewMsgDataFromNarc(int mode,int narc,int b,int heap){bank.bank=b;return &bank;}
static void DestroyMsgData(MsgData *m){}
static String *NewString_ReadMsgData(MsgData *m,int id){
    String *s=String_New(64,0);
    if(m->bank==197){s->words[0]=CHAR_P;s->words[1]=CHAR_P;s->words[2]=EOS;return s;}
    switch(m->bank*1000+id){
''' + '\n'.join(cases) + r'''
    default:assert(!"message not supplied");}return s;
}
static String *GetMoveName(int id,int heap){MsgData m={750};return NewString_ReadMsgData(&m,id);}
static int FontID_String_GetWidth(int font,const String *s,int spacing){
    int w=0;for(int i=0;s->words[i]!=EOS;i++){assert(s->words[i]>0);w+=widths[s->words[i]-1];}return w;
}
static void BufferIntegerAsString(MessageFormat *f,int i,int v,int n,int mode,int extra){f->values[i]=v;}
static void StringExpandPlaceholders(MessageFormat *f,String *s,String *pattern){
    char text[16];snprintf(text,sizeof(text),"%d/%d",f->values[0],f->values[1]);int i=0;
    for(;text[i];i++)s->words[i]=text[i]=='/'?CHAR_SLASH:CHAR_0+text[i]-'0';s->words[i]=EOS;
}
''' + item + '\n' + game.function_source(INPUT, 'BattleInput_SingleScreen_MoveName') + '\n#if QOL_EFFECTIVENESS\n' + game.function_source(INPUT, 'BattleInput_SingleScreen_OnlyOpponent') + '\n' + game.function_source(INPUT, 'BattleInput_SingleScreen_Effectiveness') + '\n#endif\n' + r'''
static int fightItems(BattleInput *battleInput,int kind,int selection,SingleScreenMenuItem *items,u8 *rect){
    MsgData *msgLoader=BattleSystem_GetMessageLoader(battleInput->battleSystem);
    MessageFormat *format=BattleSystem_GetMessageFormat(battleInput->battleSystem);
    int count=0,i;switch(kind){
''' + fight + r'''
    }return count;
}
static void cleanup(SingleScreenMenuItem *items,int n){for(int i=0;i<n;i++)String_Delete(items[i].str);assert(strings==0);}
'''


class BattleMoveLabelTests(unittest.TestCase):
    compile_run = game.GameLogicTests.compile_run

    def test_status_has_no_badge_and_skips_preview_using_real_move_loader(self):
        source = label_source() + r'''
int main(void){
    BattleSystem sys={0};BattleInput in={.battleSystem=&sys};
    const int status[]={MOVE_LEER,MOVE_TAILWIND,541,507};
    for(int i=0;i<4;i++){
        if(i>=2 && !QOL_MODERN_MOVES)continue;
        assert(GetMoveAttr(status[i],MOVEATTR_CLASS)==CATEGORY_STATUS);
        int before=previews;String *s=BattleInput_SingleScreen_Effectiveness(&in,status[i],-1);
        assert(s && s->words[0]==EOS);assert(previews==before);String_Delete(s);
    }
    assert(strings==0);return 0;
}
'''
        for modern in (0, 1):
            with self.subTest(modern=modern):
                self.compile_run(source, f'-DQOL_MODERN_MOVES={modern}',
                                 '-Wno-unused-function', '-Wno-pointer-to-int-cast')

    def test_unknown_damaging_forecasts_and_neutral_numeric_labels_remain_explicit(self):
        source = label_source() + r'''
int main(void){
    BattleSystem sys={0};BattleInput in={.battleSystem=&sys};
    const int unknown[]={MOVE_TACKLE,MOVE_SEISMIC_TOSS,MOVE_HIDDEN_POWER,587};
    for(int i=0;i<4;i++){
        if(i==3 && !QOL_MODERN_MOVES)continue;
        assert(GetMoveAttr(unknown[i],MOVEATTR_CLASS)!=CATEGORY_STATUS);
        preview=-1;int before=previews;
        String *s=BattleInput_SingleScreen_Effectiveness(&in,unknown[i],-1);
        assert(s->words[0]==CHAR_QMARK && s->words[1]==EOS);
        assert(previews==before+1 && lastTarget==-1);String_Delete(s);
    }
    const int values[]={0,10,20,40,80,160};
    const u16 expected[][5]={{CHAR_0,CHAR_x,EOS},{CHAR_1,CHAR_SLASH,CHAR_4,CHAR_x,EOS},
      {CHAR_1,CHAR_SLASH,CHAR_2,CHAR_x,EOS},{CHAR_1,CHAR_x,EOS},{CHAR_2,CHAR_x,EOS},{CHAR_4,CHAR_x,EOS}};
    for(int i=0;i<6;i++){
        preview=values[i];String *s=BattleInput_SingleScreen_Effectiveness(&in,MOVE_TACKLE,1);
        for(int j=0;;j++){assert(s->words[j]==expected[i][j]);if(expected[i][j]==EOS)break;}
        String_Delete(s);
    }assert(strings==0);return 0;
}
'''
        for modern in (0, 1):
            with self.subTest(modern=modern):
                self.compile_run(source, f'-DQOL_MODERN_MOVES={modern}',
                                 '-Wno-unused-function', '-Wno-pointer-to-int-cast')

    def test_real_fight_branch_separates_type_pp_and_subdues_only_empty_cards(self):
        source = builder_source() + r'''
int main(void){
    BattleSystem sys={.battlers=2,.ctx={.battleMons={{100},{100}}}};
    BattleInput in={.battleSystem=&sys,.menu={.fight={{MOVE_LOW_KICK,MOVE_LEER,MOVE_THUNDER_SHOCK,MOVE_NONE},
      {10,0,10,0},{35,30,30,0}}}};
    for(int selection=1;selection<=4;selection++){
        SingleScreenMenuItem items[20]={0};u8 rect[4];
        int n=fightItems(&in,SS_MENU_FIGHT,selection,items,rect),cards=0;
        for(int k=0;k<n;k++)if(items[k].button){
            int i=cards++,bx=14+(i&1)*120,by=3+(i>>1)*32;
            SingleScreenMenuItem *b=&items[k];
            assert(b->x==bx && b->y==by && b->width==108 && b->height==29);
            if(i==3){assert(b->button==6 && !b->topLabel && b->grey && !b->selected);
                assert(b->str->words[0]==CHAR_HYPHEN && b->str->words[1]==EOS);assert(k==n-1);continue;}
            assert(b->button==5 && b->topLabel && !b->grey && b->selected==(selection==i+1));
            int type=k+1;
#if QOL_EFFECTIVENESS
            assert(items[k+1].str->words[0]==(i==1?EOS:CHAR_QMARK));type++;
#endif
            SingleScreenMenuItem *t=&items[type],*numbers=&items[type+1],*pp=&items[type+2];
            assert(!t->pill && t->x==bx+5 && t->y==by+14);
            assert(numbers->x+FontID_String_GetWidth(0,numbers->str,0)==bx+103);
            assert(t->x+FontID_String_GetWidth(0,t->str,0)+5<=pp->x);
            assert(numbers->grey==(i==1) && pp->grey==(i==1));
        }assert(cards==4);assert(rect[0]==0 && rect[1]==16 && rect[2]==32 && rect[3]==8);cleanup(items,n);
    }
    return 0;
}
'''
        for effectiveness in (0, 1):
            for modern in (0, 1):
                with self.subTest(effectiveness=effectiveness, modern=modern):
                    self.compile_run(source, f'-DQOL_EFFECTIVENESS={effectiveness}',
                                     f'-DQOL_MODERN_MOVES={modern}', f'-DQOL_MODERN_TYPES={modern}',
                                     f'-DQOL_MODERN_BATTLE={modern}', '-Wno-unused-function',
                                     '-Wno-pointer-to-int-cast')

    def test_empty_raster_preserves_text_and_keeps_quiet_fill_even_if_selected(self):
        source = r'''
#include <assert.h>
#include <string.h>
typedef unsigned char u8;typedef int BOOL;
typedef struct {int width;void *pixelBuffer;} Window;
''' + '\n'.join(game.function_source(INPUT, name) for name in
                ('SingleScreen_SetPixel', 'SingleScreen_GetPixel', 'SingleScreen_PaintButton')) + r'''
int main(void){
    u8 pixels[8192];Window w={32,pixels};memset(pixels,255,sizeof(pixels));
    SingleScreen_SetPixel(&w,55,16,12);
    SingleScreen_PaintButton(&w,14,3,108,29,6,1);
    assert(SingleScreen_GetPixel(&w,55,16)==12);
    assert(SingleScreen_GetPixel(&w,60,15)==15);
    assert(SingleScreen_GetPixel(&w,60,3)==12);
    assert(SingleScreen_GetPixel(&w,14,3)==15);
    SingleScreen_PaintButton(&w,134,3,108,29,5,1);
    assert(SingleScreen_GetPixel(&w,180,3)==14);
    assert(SingleScreen_GetPixel(&w,180,15)==1);return 0;
}
'''
        self.compile_run(source)

    def test_actual_render_loop_centres_grey_dash_and_preserves_real_name_inset(self):
        update = game.function_source(INPUT, 'BattleInput_SingleScreen_Update')
        start = update.index('    for (i = 0; i < count; i++) {', update.index('FillWindowPixelBuffer'))
        end = update.index('    // The buttons go behind the text', start)
        loop = update[start:end]
        source = builder_source() + r'''
#define MAKE_TEXT_COLOR(a,b,c) ((a)|((b)<<8)|((c)<<16))
#define SS_BUTTON_TEXT_COLOR MAKE_TEXT_COLOR(2,15,15)
#define SS_TEXT_COLOR MAKE_TEXT_COLOR(1,2,15)
#define SS_TEXT_COLOR_GREY MAKE_TEXT_COLOR(3,4,15)
enum {SS_BUTTON_WIDTH=54,SS_BUTTON_HEIGHT=22,TEXT_SPEED_NOTRANSFER};
static int prints,lastX,lastY,lastColor;
static void AddTextPrinterParameterizedWithColor(void *w,int font,String *s,int x,int y,int speed,int color,void *cb){
    prints++;lastX=x;lastY=y;lastColor=color;
}
static void ListMenuUpdateCursorObj(void *c,void *w,int x,int y){}
static void renderItems(BattleInput *battleInput,SingleScreenMenuItem *items,int count){
    int i,pillWidths[20],buttons=1;
''' + loop + r'''
    (void)pillWidths;
}
int main(void){
    BattleSystem sys={0};BattleInput in={.battleSystem=&sys};
    SingleScreenMenuItem real={.str=GetMoveName(MOVE_TACKLE,0),.x=14,.y=3,.button=5,
      .width=108,.height=29,.topLabel=1};
    renderItems(&in,&real,1);
    assert(prints==1 && lastX==18 && lastY==4 && lastColor==SS_BUTTON_TEXT_COLOR && strings==0);
    const u16 dash[]={CHAR_HYPHEN,EOS};String *s=String_New(2,0);CopyU16ArrayToString(s,dash);
    int width=FontID_String_GetWidth(0,s,0);
    SingleScreenMenuItem empty={.str=s,.x=134,.y=35,.button=6,.grey=1,.width=108,.height=29};
    renderItems(&in,&empty,1);
    assert(prints==2 && lastX==134+(108-width)/2 && lastY==41);
    assert(lastColor==MAKE_TEXT_COLOR(12,15,15) && strings==0);return 0;
}
'''
        self.compile_run(source, '-DQOL_EFFECTIVENESS=1', '-Wno-unused-function',
                         '-Wno-pointer-to-int-cast')


if __name__ == '__main__':
    unittest.main()
