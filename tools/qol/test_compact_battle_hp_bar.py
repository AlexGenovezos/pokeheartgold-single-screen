"""Host-only actual-C compact HUD tests; SDK/font/printer edges use local assets.

Run with battle_scripts.compile_battle_script and battle_script_tools blocked before
importing this module. No SDK, ROM generation, or emulator is used by this suite.
"""
from pathlib import Path
import re
import struct
import unittest
import shutil
import subprocess
import tempfile

import test_game_logic as game
from test_battle_controls_geometry import ROOT, HP, declaration, cell_oams
from nitro_data import unpack_narc, lz10_decompress


def raw_character(data):
    if data[0] == 0x10:
        data = lz10_decompress(data)
    assert data[:4] == b'RGCN'
    length, offset = struct.unpack_from('<II', data, 40)
    return data[24 + offset:24 + offset + length]


def c_bytes(name, data):
    return 'static const u8 ' + name + '[]={' + ','.join(map(str, data)) + '};\n'


def fixture_source():
    text = (ROOT / HP).read_text()
    enum = re.search(r'typedef enum HPBarType \{.*?\} HPBarType;', text, re.S)[0]
    # Actual in-tree component data, not a Python drawing model.
    components = (ROOT / 'src/battle/battle_hp_bar_data.h').read_text().replace('#include <nitro.h>', '')
    numeric = raw_character((ROOT / 'files/graphic/font/font_00000005.bin').read_bytes())
    # SDK numeric char preparation maps 0/1/2 to bg/fg/shadow. Battle uses 15/14/2.
    numeric = bytes(({0:15,1:14,2:2}.get(b & 15,b & 15) | ({0:15,1:14,2:2}.get(b >> 4,b >> 4) << 4)) for b in numeric)
    font = (ROOT / 'files/graphic/font/font_00000000.bin').read_bytes()
    header, widths, count, fw, fh, tw, th = struct.unpack_from('<IIIBBBB', font)
    assert count == 509 and (tw, th) == (2, 2)
    templates = re.findall(r'^static const ManagedSpriteTemplate (sSpriteTemplate_\w+) =', text, re.M)
    arrays = ('sHpBarArrowXOffsets', 'sNicknameVramRegions', 'sGenderIconVramRegions',
              'sLevelVramRegions', 'sCurrentHpVramRegions', 'sMaxHpVramRegions',
              'sHpGaugeVramRegions', 'sCaughtIconVramRegions', 'sStatusIconVramRegions',
              'ov12_0226D3A8', 'ov12_0226D3D8', 'ov12_0226D408')
    names = ['BattleHpBar_Util_GetComponentRawGraphic',
             'BattleHpBar_Util_GetHpBoxSpriteTemplate', 'BattleHpBar_CreateBoxSprite',
             'BattleHpBar_Draw', 'BattleHpBar_ToggleHpNumbers',
             'BattleHpBar_DrawNickname', 'BattleHpBar_DrawGenderIcon', 'BattleHpBar_DrawLevel',
             'BattleHpBar_DrawCurrentHp', 'BattleHpBar_DrawMaxHp', 'BattleHpBar_DrawStatusIcon',
             'BattleHpBar_InitHpChange', 'BattleHpBar_UpdateHpChange',
             'BattleHpBar_StepGauge', 'BattleHpBar_DrawGauge',
             'BattleHpBar_CalculatePixelsChangeFrame', 'BattleHpBar_Util_MakeHpBarPixelBuffer',
             'BattleHpBar_Util_GetPixelsToGain']
    names = re.findall(r'^static [^\n;{}]*\b(BattleHpBar_(?:IsCompact|Compact\w+))\([^;{}]*\)\s*\{', text, re.M) + names
    functions = [game.function_source(HP, n).replace('(u32)vramAddr','(uintptr_t)vramAddr').replace('(u32)vramBaseAddr','(uintptr_t)vramBaseAddr') for n in names]
    prototypes = '\n'.join(f[:f.index('{')].strip() + ';' for f in functions)
    return r'''
#include <assert.h>
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <stdio.h>
#include "constants/charcode.h"
typedef unsigned char u8;typedef signed char s8;typedef unsigned short u16;typedef signed short s16;
typedef unsigned int u32;typedef signed int s32;typedef int BOOL;typedef int PrintingMode;
#define TRUE 1
#define FALSE 0
#define GF_ASSERT assert
#define ALIGN(n) __attribute__((aligned(n)))
#define HEAP_ID_BATTLE 0
#define BATTLE_TYPE_TRAINER 1
#define NNS_G2D_VRAM_TYPE_2DMAIN 0
#ifdef FAST_HP_BARS
#define USE_SUBPIXELS_TEST TRUE
#else
#define USE_SUBPIXELS_TEST (maxHp < pixelsWide)
#endif
#define PRINTING_MODE_LEFT_ALIGN 0
#define PRINTING_MODE_RIGHT_ALIGN 1
#define TEXT_SPEED_NOTRANSFER 0
#define MAKE_TEXT_COLOR(a,b,c) 0
#define msg_0197_00964 964
typedef struct {int x,y,z,animation,drawPriority,pal,vram,resIdList[6],bgPriority,vramTransfer;} ManagedSpriteTemplate;
typedef struct {struct {uintptr_t baseAddrOfVram[1];} vramLocation;} NNSG2dImageProxy;
typedef struct {NNSG2dImageProxy image;int x,y;} Sprite;
typedef struct {Sprite *sprite;} ManagedSprite;
typedef int SpriteSystem;typedef int SpriteManager;
typedef struct {u16 offset,size;} HpBarVramRegion;
typedef struct {int type,showHpNumbers,hp,maxHp,gainedHp,hpCalc,exp,maxExp,gainedExp,expCalc,level,gender,status,battlerId,monId;void *battleSystem;ManagedSprite *boxObj;} BattleHpBar;
static struct {u16 before[16],data[0x800],after[16];} memory;
static u8 *vram=(u8*)memory.data;
static Sprite sprite;static ManagedSprite managed={&sprite};
static ManagedSprite *SpriteSystem_NewSprite(SpriteSystem *s,SpriteManager *m,const ManagedSpriteTemplate *t){sprite.x=t->x;sprite.y=t->y;return &managed;}
static void Sprite_TickFrame(Sprite *s){}
static void *G2_GetOBJCharPtr(void){return vram;}
static NNSG2dImageProxy *Sprite_GetImageProxy(Sprite *s){return &s->image;}
static void *Heap_Alloc(int heap,int n){void *p=malloc(n);assert(p);return p;}
static void Heap_Free(void *p){free(p);}
static void MI_CpuFill8(void *p,int c,int n){assert((uintptr_t)p<(uintptr_t)vram||(uintptr_t)p>=(uintptr_t)vram+0x1000);memset(p,c,n);}
static void MI_CpuFill16(void *p,int c,int n){assert(!((uintptr_t)p&1)&&!(n&1));for(int i=0;i<n/2;i++)((u16*)p)[i]=c;}
static void MI_CpuCopy16(const void *s,void *d,int n){assert(!((uintptr_t)s&1)&&!((uintptr_t)d&1)&&!(n&1));memcpy(d,s,n);}
static void MI_CpuCopy32(const void *s,void *d,int n){memcpy(d,s,n);}
static int BattleSystem_GetBattleType(void *b){return 0;}
static void BattleHpBar_InitExpChange(BattleHpBar *h,int n){}
static void BattleHpBar_DrawCaughtIcon(BattleHpBar *h){}
static void BattleHpBar_PrintSafariOrParkBallsString(BattleHpBar *h,u32 f){}
static void BattleHpBar_PrintNumRemainingSafariOrParkBalls(BattleHpBar *h,u32 f){}
static u8 HpBar_GetColorIdx(u32 pixelsCur,u32 pixelsWide);
static int printedNum,printerCalls;
typedef struct {const u8 *pRawData;} CharacterData;
typedef struct {int fillVal;u16 strbuf[4];CharacterData *charData;} BattleNumberPrinter;
static CharacterData chars;static BattleNumberPrinter printer={15,{0},&chars};
static BattleNumberPrinter *BattleSystem_GetLevelNumPrinter(void *b){return &printer;}
static BattleNumberPrinter *BattleSystem_GetHpNumPrinter(void *b){return &printer;}
static void ConvertUIntToDecimalString(u16 *dst,u32 num,int mode,int n){
    assert(n==3);printedNum=num;printerCalls++;char digits[32];snprintf(digits,sizeof(digits),"%u",num);
    int len=strlen(digits);assert(len<=n);for(int i=0;i<n;i++)dst[i]=CHAR_SPACE;
    int start=mode==PRINTING_MODE_RIGHT_ALIGN?n-len:0;
    for(int i=0;i<len;i++)dst[start+i]=CHAR_JP_0+digits[i]-'0';dst[n]=EOS;
}
typedef int BgConfig;typedef int MsgData;typedef int MessageFormat;typedef int Pokemon;typedef int BoxPokemon;typedef int String;
typedef struct {u8 *pixelBuffer;} Window;
static BgConfig *BattleSystem_GetBgConfig(void *b){return NULL;}
static MsgData *BattleSystem_GetMessageLoader(void *b){return NULL;}
static MessageFormat *BattleSystem_GetMessageFormat(void *b){return NULL;}
static String *String_New(int n,int h){return NULL;}
static String *NewString_ReadMsgData(MsgData *m,int n){return NULL;}
static Pokemon *BattleSystem_GetPartyMon(void *b,int battler,int mon){return NULL;}
static BoxPokemon *Mon_GetBoxMon(Pokemon *p){return NULL;}
static void BufferBoxMonNickname(MessageFormat *m,int n,BoxPokemon *b){}
static void StringExpandPlaceholders(MessageFormat *m,String *s,String *s2){}
static void String_Delete(String *s){}
static u8 nameWindow[0x200];
static void AddTextWindowTopLeftCorner(BgConfig *b,Window *w,int x,int y,int p,int c){assert(x==8&&y==2);w->pixelBuffer=nameWindow;}
static void AddTextPrinterParameterizedWithColorAndSpacing(Window *w,int f,String *s,int x,int y,int speed,int color,int a,int b,void *cb){}
static void RemoveWindow(Window *w){}
static u16 sFontHalfRowLookupTable[256];static u8 sBgColor,sFgColor,sShadowColor;
''' + enum + '\n' + components + c_bytes('numericGraphic', numeric) + c_bytes('fontGlyphs', font[header:header+count*64]) + c_bytes('fontWidths',font[widths:widths+count]) + '\n'.join(declaration(HP, n) for n in arrays + tuple(templates)) + '\n' + prototypes + '\n' + game.function_source('src/ui_util.c','HpBar_GetColorIdx') + '\n' + game.function_source('src/message_printer_number.c','BattleNumberPrinter_PrintUInt') + '\n' + game.function_source('src/text.c','GenerateFontHalfRowLookupTable') + '\n' + game.function_source('src/text.c','DecompressGlyphTile') + '\n' + '\n'.join(functions) + r'''
static int pixel(int x,int y){
    assert(x>=0&&x<128&&y>=0&&y<24);
    int px=x%64,py=y+16;
    int a=x/64*0x800+((py/8)*8+px/8)*32+(py%8)*4+px%8/2;
    return (vram[a]>>((px&1)*4))&15;
}
static int srcPixel(const u8 *p,int tiles,int x,int y){int a=((y/8)*tiles+x/8)*32+(y%8)*4+x%8/2;return(p[a]>>((x&1)*4))&15;}
static void canaries(void){for(int i=0;i<16;i++){assert(memory.before[i]==0xa55a);assert(memory.after[i]==0xa55a);}}
static BattleHpBar reset(void){
    memset(&memory,0xa5,sizeof(memory));for(int i=0;i<16;i++)memory.before[i]=memory.after[i]=0xa55a;
    chars.pRawData=numericGraphic;memset(nameWindow,255,sizeof(nameWindow));
    GenerateFontHalfRowLookupTable(14,15,2);
    BattleHpBar h={.type=HP_BAR_TYPE_DOUBLE_PLAYER_LHS,.hp=100,.maxHp=100,.level=100};
    h.boxObj=BattleHpBar_CreateBoxSprite(NULL,NULL,h.type);canaries();return h;
}
static void prepareName(const u16 *name,int length){
    memset(nameWindow,255,sizeof(nameWindow));int cursor=0;
    for(int n=0;n<length;n++){
        int glyph=name[n]-1;assert(glyph>=0&&glyph<509);ALIGN(4) u8 decoded[128];
        for(int t=0;t<4;t++)DecompressGlyphTile(fontGlyphs+glyph*64+t*16,decoded+t*32);
        for(int y=0;y<16;y++){for(int x=0;x<16&&cursor+x<64;x++){
            int color=srcPixel(decoded,2,x,y);if(!color)continue;
            int px=cursor+x,a=((y/8)*8+px/8)*32+(y%8)*4+px%8/2,shift=(px&1)*4;
            nameWindow[a]=(nameWindow[a]&~(15<<shift))|(color<<shift);
        }}
        cursor+=fontWidths[glyph];
    }
}
static void sameRect(const u8 *p,int tiles,int sx,int sy,int dx,int dy,int w,int h){
    for(int y=0;y<h;y++)for(int x=0;x<w;x++)assert(pixel(dx+x,dy+y)==srcPixel(p,tiles,sx+x,sy+y));canaries();
}
static void gaugeRect(BattleHpBar *h){
    u8 fills[6];s32 calc=h->hpCalc;
    int pixels=BattleHpBar_Util_MakeHpBarPixelBuffer(h->maxHp,h->hp,h->gainedHp,&calc,fills,6);
    int color=HpBar_GetColorIdx(pixels,48),base=color==3?2:color==2?11:20;
    for(int i=0;i<6;i++)sameRect(BattleHpBar_Util_GetComponentRawGraphic(base+fills[i]),1,0,2,24+i*8,17,8,3);
}
static void numberRect(int num,int mode,int x,int y){
    ALIGN(4) u8 expected[96];memset(expected,255,96);
    BattleNumberPrinter_PrintUInt(&printer,num,3,mode,(u16*)expected);
    sameRect(expected,3,0,1,x,y,24,7);
}
'''


class CompactBattleHpBarTests(unittest.TestCase):
    compile_run = game.GameLogicTests.compile_run

    def run_c(self, checks, *flags):
        self.compile_run(fixture_source()+checks, '-DSINGLE_SCREEN',
                         '-Wno-unused-function','-Wno-unused-variable',
                         '-Wno-pointer-to-int-cast','-Wno-int-to-pointer-cast','-Wno-sign-compare', *flags)

    def test_number_draw_uses_animation_argument_and_preserves_neighboring_fields(self):
        self.run_c(r'''
int main(void){BattleHpBar h=reset();
    const int values[]={0,1,99,100,999};
    for(int i=0;i<5;i++){
        h.maxHp=values[4-i];BattleHpBar_DrawMaxHp(&h);
        BattleHpBar_DrawCurrentHp(&h,values[i]);
        numberRect(values[i],PRINTING_MODE_RIGHT_ALIGN,72,16);
        numberRect(h.maxHp,PRINTING_MODE_LEFT_ALIGN,104,16);
        for(int x=24;x<72;x++)assert(pixel(x,23)!=0);
    }return 0;}
''')

    def test_components_level_and_clear_are_lossless_and_do_not_erase_name(self):
        self.run_c(r'''
int main(void){BattleHpBar h=reset();
    memset(nameWindow,0xee,sizeof(nameWindow));BattleHpBar_DrawNickname(&h);
    const int top[]={62,60,64},bottom[]={74,72,76},levels[]={1,99,100};
    for(int gender=0;gender<3;gender++){
        h.gender=gender;BattleHpBar_DrawGenderIcon(&h);
        ALIGN(4) u8 graphic[128];memcpy(graphic,BattleHpBar_Util_GetComponentRawGraphic(top[gender]),64);
        memcpy(graphic+64,BattleHpBar_Util_GetComponentRawGraphic(bottom[gender]),64);
        sameRect(graphic,2,0,3,88,0,16,9);
        for(int j=0;j<3;j++){h.level=levels[j];BattleHpBar_DrawLevel(&h);numberRect(h.level,PRINTING_MODE_LEFT_ALIGN,104,0);}
        for(int c=38;c<=53;c+=3){BattleHpBar_DrawStatusIcon(&h,c);sameRect(BattleHpBar_Util_GetComponentRawGraphic(c),3,0,0,104,8,24,8);}
        BattleHpBar_DrawStatusIcon(&h,38);sameRect(BattleHpBar_Util_GetComponentRawGraphic(38),3,0,0,104,8,24,8);
        for(int y=0;y<15;y++)for(int x=24;x<88;x++)assert(pixel(x,y)==14);
    }return 0;}
''')

    def test_all_font0_glyph_ink_and_worst_name_are_retained_at_native_scale(self):
        self.run_c(r'''
int main(void){BattleHpBar h=reset();
    for(int glyph=0;glyph<509;glyph++){
        ALIGN(4) u8 decoded[128];
        for(int tile=0;tile<4;tile++)DecompressGlyphTile(fontGlyphs+glyph*64+tile*16,decoded+tile*32);
        for(int x=0;x<16;x++){int p=srcPixel(decoded,2,x,15);assert(p==15||p==0);}
        memset(nameWindow,255,512);
        for(int ty=0;ty<2;ty++)memcpy(nameWindow+ty*256,decoded+ty*64,64);
        BattleHpBar_DrawNickname(&h);sameRect(nameWindow,8,0,0,24,0,64,15);
    }
    assert(fontWidths[CHAR_W-1]*10==60);
    const u16 wideName[]={CHAR_W,CHAR_W,CHAR_W,CHAR_W,CHAR_W,CHAR_W,CHAR_W,CHAR_W,CHAR_W,CHAR_W};
    prepareName(wideName,10);BattleHpBar_DrawNickname(&h);sameRect(nameWindow,8,0,0,24,0,64,15);
    const u16 mixedName[]={CHAR_F,CHAR_e,CHAR_r,CHAR_a,CHAR_l,CHAR_i,CHAR_g,CHAR_a,CHAR_t,CHAR_r};
    prepareName(mixedName,10);BattleHpBar_DrawNickname(&h);sameRect(nameWindow,8,0,0,24,0,64,15);
    memset(nameWindow,0xee,512);BattleHpBar_DrawNickname(&h);
    memset(nameWindow,255,512);BattleHpBar_DrawNickname(&h);
    for(int y=0;y<15;y++)for(int x=24;x<88;x++)assert(pixel(x,y)==15);
    return 0;}
''')

    def test_gauge_numbers_both_logical_modes_toggle_and_single_step_animation(self):
        self.run_c(r'''
int main(void){BattleHpBar h=reset();
    for(int mode=0;mode<2;mode++){
        h.showHpNumbers=mode;
        const int values[]={0,1,19,20,21,49,50,51,99,100};
        for(int k=0;k<10;k++){
            h.hp=values[k];h.maxHp=100;BattleHpBar_Draw(&h,h.hp,1);
            numberRect(h.hp,PRINTING_MODE_RIGHT_ALIGN,72,16);numberRect(100,PRINTING_MODE_LEFT_ALIGN,104,16);
            int fills[6]={0},remaining=h.hp*48/100;if(!remaining&&h.hp)remaining=1;
            int base=remaining>24?2:remaining>9?11:20;
            for(int i=0;i<6;i++){fills[i]=remaining>8?8:remaining;remaining-=fills[i];sameRect(BattleHpBar_Util_GetComponentRawGraphic(base+fills[i]),1,0,2,24+i*8,17,8,3);}
            u8 saved[4096];memcpy(saved,vram,4096);BattleHpBar_ToggleHpNumbers(&h);assert(!memcmp(saved,vram,4096));
            assert(h.showHpNumbers==!mode);BattleHpBar_ToggleHpNumbers(&h);
        }
        h.hp=100;BattleHpBar_Draw(&h,h.hp,1);BattleHpBar_InitHpChange(&h,-5);
        int last=100,steps=0,cur;
        while((cur=BattleHpBar_UpdateHpChange(&h))!=-1){
            assert(cur==last-1);last=cur;steps++;numberRect(cur,PRINTING_MODE_RIGHT_ALIGN,72,16);gaugeRect(&h);assert(steps<=5);
            s32 before=h.hpCalc;u8 saved[4096];memcpy(saved,vram,4096);
            BattleHpBar_ToggleHpNumbers(&h);assert(h.hpCalc==before&&!memcmp(saved,vram,4096));BattleHpBar_ToggleHpNumbers(&h);
        }
        assert(steps==5&&h.hp==95);numberRect(95,PRINTING_MODE_RIGHT_ALIGN,72,16);
    }return 0;}
''')

    def test_creation_clears_original_ncgr_canvas_and_fully_bounds_compact_card(self):
        members,_=unpack_narc((ROOT/'files/a/0/0/8').read_bytes())
        objects=','.join('{'+','.join(map(str,o))+'}' for o in cell_oams(members[199])[0])
        self.run_c('static const int oams[][5]={'+objects+'};\n'+r'''
int main(void){BattleHpBar h=reset();(void)h;
    for(int y=0;y<64;y++)for(int x=0;x<128;x++){
        int a=x/64*0x800+((y/8)*8+(x%64)/8)*32+(y%8)*4+(x%8)/2;
        int p=(vram[a]>>((x&1)*4))&15;
        assert((p!=0)==(y>=16&&y<40));
    }
    for(int y=0;y<24;y++)assert(pixel(0,y)!=0&&pixel(23,y)!=0&&pixel(24,y)!=0);
    /* Decode generated bytes with the actual NCER OAM coordinates/tile indices,
     * independently of the card writer's half and y-offset transformation. */
    for(int side=0;side<2;side++){
        int count=0,center=side?192:64;
        for(int o=0;o<2;o++){
            const int *obj=oams[o];
            for(int py=0;py<obj[3];py++)for(int px=0;px<obj[2];px++){
                int a=obj[4]*64+((py/8)*(obj[2]/8)+px/8)*32+(py%8)*4+(px%8)/2;
                if((vram[a]>>((px&1)*4))&15){
                    int x=center+obj[0]+px,y=116+obj[1]+py;
                    assert(x>=side*128&&x<side*128+128&&y>=104&&y<=127);count++;
                }
            }
        }assert(count==128*24);
    }
    canaries();return 0;}
''', '-fsanitize=address,undefined', '-fno-omit-frame-pointer')

    def test_damage_heal_subpixel_and_fast_modes_follow_original_one_step_math(self):
        checks=r'''
int main(void){
    const int maxima[]={1,37,100,999};
    for(int scenario=0;scenario<16;scenario++){
        int mode=scenario/8,heal=(scenario/4)%2,m=scenario%4;
        BattleHpBar h=reset();h.showHpNumbers=mode;h.maxHp=maxima[m];h.hp=heal?0:h.maxHp;
        BattleHpBar_Draw(&h,h.hp,1);BattleHpBar_InitHpChange(&h,heal?h.maxHp:-h.maxHp);
        s32 expectedCalc=h.hpCalc;int done=0;
        for(int frame=0;frame<1200;frame++){
            int expected=BattleHpBar_CalculatePixelsChangeFrame(h.maxHp,h.hp,h.gainedHp,&expectedCalc,6,1);
            int current=BattleHpBar_UpdateHpChange(&h);assert(current==expected);
            numberRect(current<0?h.hp:current,PRINTING_MODE_RIGHT_ALIGN,72,16);
            if(current<0){assert(h.hp==(heal?h.maxHp:0)&&h.hpCalc==0);done=1;break;}
            assert(h.hpCalc==expectedCalc);gaugeRect(&h);canaries();
        }assert(done);
    }return 0;}
'''
        for flags in ((),('-DFAST_HP_BARS',)):
            with self.subTest(fast=bool(flags)):
                self.run_c(checks,*flags,'-fsanitize=address,undefined','-fno-omit-frame-pointer')

    def test_shared_halfwords_fields_survive_arbitrary_redraw_order_and_recreation(self):
        self.run_c(r'''
int main(void){
    for(int type=HP_BAR_TYPE_DOUBLE_PLAYER_LHS;type<=HP_BAR_TYPE_DOUBLE_PLAYER_RHS;type+=2){
        BattleHpBar h=reset();h.type=type;h.boxObj=BattleHpBar_CreateBoxSprite(NULL,NULL,type);
        h.level=100;h.gender=1;h.status=5;h.hp=999;h.maxHp=999;
        const u16 name[]={CHAR_W,CHAR_W,CHAR_W,CHAR_W,CHAR_W,CHAR_W,CHAR_W,CHAR_W,CHAR_W,CHAR_W};
        prepareName(name,10);BattleHpBar_Draw(&h,h.hp,~0u);
        int snapshot[24][128];for(int y=0;y<24;y++)for(int x=0;x<128;x++)snapshot[y][x]=pixel(x,y);
        const int regions[][4]={{24,0,64,15},{88,0,16,9},{104,0,24,7},{104,8,24,8},{24,17,48,3},{72,16,24,7},{104,16,24,7}};
        for(int field=0;field<7;field++){
            for(int y=0;y<24;y++)for(int x=0;x<128;x++)snapshot[y][x]=pixel(x,y);
            switch(field){
                case 0:memset(nameWindow,255,512);BattleHpBar_DrawNickname(&h);break;
                case 1:h.gender=2;BattleHpBar_DrawGenderIcon(&h);break;
                case 2:h.level=1;BattleHpBar_DrawLevel(&h);break;
                case 3:BattleHpBar_DrawStatusIcon(&h,38);break;
                case 4:h.hp=1;BattleHpBar_InitHpChange(&h,0);BattleHpBar_StepGauge(&h,FALSE);break;
                case 5:BattleHpBar_DrawCurrentHp(&h,0);break;
                case 6:h.maxHp=1;BattleHpBar_DrawMaxHp(&h);break;
            }
            const int *r=regions[field];
            for(int y=0;y<24;y++)for(int x=0;x<128;x++)if(x<r[0]||x>=r[0]+r[2]||y<r[1]||y>=r[1]+r[3])assert(pixel(x,y)==snapshot[y][x]);
            canaries();
        }
        h.hp=0;BattleHpBar_Draw(&h,0,1);numberRect(0,PRINTING_MODE_RIGHT_ALIGN,72,16);
        h.boxObj=BattleHpBar_CreateBoxSprite(NULL,NULL,type);h.maxHp=100;h.hp=100;h.level=1;
        memset(nameWindow,255,512);BattleHpBar_Draw(&h,100,~0u);
        for(int y=0;y<15;y++)for(int x=24;x<88;x++)assert(pixel(x,y)==15);
        numberRect(1,PRINTING_MODE_LEFT_ALIGN,104,0);numberRect(100,PRINTING_MODE_RIGHT_ALIGN,72,16);
        canaries();
    }return 0;}
''', '-fsanitize=address,undefined', '-fno-omit-frame-pointer')

    def test_ordinary_build_keeps_original_canvas_gauge_and_number_routes(self):
        source=fixture_source()+r'''
int main(void){BattleHpBar h=reset();
    for(int i=0;i<0x1000;i++)assert(vram[i]==0xa5);
    for(int type=0;type<8;type++)assert(!BattleHpBar_IsCompact(type));
    for(int type=HP_BAR_TYPE_DOUBLE_PLAYER_LHS;type<=HP_BAR_TYPE_DOUBLE_PLAYER_RHS;type+=2){
        h.type=type;h.hp=h.maxHp=100;h.showHpNumbers=0;printerCalls=0;
        BattleHpBar_Draw(&h,100,7);assert(printerCalls==0);
        for(int i=0;i<6;i++)assert(!memcmp(vram+0xc00+i*32,BattleHpBar_Util_GetComponentRawGraphic(10),32));
        h.showHpNumbers=1;BattleHpBar_Draw(&h,99,7);assert(printerCalls==2);
        ALIGN(4) u8 digits[96];memset(digits,255,96);
        BattleNumberPrinter_PrintUInt(&printer,99,3,PRINTING_MODE_RIGHT_ALIGN,(u16*)digits);assert(!memcmp(vram+0xc00,digits,96));
        BattleNumberPrinter_PrintUInt(&printer,100,3,PRINTING_MODE_LEFT_ALIGN,(u16*)digits);assert(!memcmp(vram+0xc80,digits,96));
        BattleHpBar_ToggleHpNumbers(&h);assert(!h.showHpNumbers);
        for(int i=0;i<6;i++)assert(!memcmp(vram+0xc00+i*32,BattleHpBar_Util_GetComponentRawGraphic(10),32));
        canaries();
    }return 0;}
'''
        self.compile_run(source,'-Wno-unused-function','-Wno-unused-variable',
                         '-Wno-pointer-to-int-cast','-Wno-int-to-pointer-cast','-Wno-sign-compare')

    def test_compiler_keeps_obj_writes_as_volatile_aligned_halfwords(self):
        compiler=shutil.which('clang')
        if not compiler:
            self.skipTest('Clang LLVM inspection requires a host clang')
        actual=game.function_source(HP,'BattleHpBar_CompactPutPixel')
        source='#include <assert.h>\ntypedef unsigned char u8;typedef unsigned short u16;\n#define GF_ASSERT assert\n'+actual.replace('static void','void',1)
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'pixel.c';path.write_text(source)
            result=subprocess.run([compiler,'-O2','-S','-emit-llvm',str(path),'-o','-'],capture_output=True,text=True)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertRegex(result.stdout,r'load volatile i16,.*align 2')
            self.assertRegex(result.stdout,r'store volatile i16 .*align 2')
            self.assertNotRegex(result.stdout,r'store(?: volatile)? i8 ')

    def test_asset_oams_and_us_keyboard_width_contract(self):
        members,_=unpack_narc((ROOT/'files/a/0/0/8').read_bytes())
        for cell in (199,202):
            self.assertEqual(cell_oams(members[cell]), [[(-64,-28,64,64,0),(0,-28,64,64,32)]])
        for char in (200,203):
            self.assertEqual(len(raw_character(members[char])),0x1000)
        for center in (64,192):
            for cell in cell_oams(members[184]):
                for x,y,w,h,tile in cell:
                    self.assertGreaterEqual(center-48+x,center-64)
                    self.assertLess(center-48+x+w,center-64+25)
                    self.assertGreaterEqual(116+y,104)
                    self.assertLessEqual(116+y+h-1,127)
        font=(ROOT/'files/graphic/font/font_00000000.bin').read_bytes()
        widths=struct.unpack_from('<I',font,4)[0]
        codes={name:int(value) for name,value in re.findall(r'^#define\s+(CHAR_\w+)\s+(\d+)',(ROOT/'include/constants/charcode.h').read_text(),re.M)}
        rows=re.findall(r'sKeyboardRow_(?:Upper|Lower|Symbols)_\d\[\] = \{([^}]+)\}',(ROOT/'src/naming_screen.c').read_text())
        self.assertEqual(len(rows),15)
        for row in rows:
            for name in re.findall(r'CHAR_\w+',row):
                self.assertLessEqual(font[widths+codes[name]-1]*10,60,name)


if __name__=='__main__':
    unittest.main()
