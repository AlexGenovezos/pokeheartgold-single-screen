"""Execute real touch/HP position routes with SDK rendering and task edges stubbed.

The asset audit reads local NCER/NCGR files; no game assets are embedded here.
These are host compiler tests, with no SDK, Wine or runtime invocation.
"""
from pathlib import Path
import re
import struct
import unittest

import test_game_logic as game
from nitro_data import unpack_narc, lz10_decompress

ROOT = Path(__file__).resolve().parents[2]
INPUT = 'src/battle/battle_input.c'
HP = 'src/battle/battle_hp_bar.c'


def declaration(path, name):
    text = (ROOT / path).read_text()
    match = re.search(r'^static const [^;=]+\b' + re.escape(name) + r'[^;=]*=\s*\{', text, re.M)
    if not match:
        return ''
    pos, depth = match.end(), 1
    while depth:
        depth += (text[pos] == '{') - (text[pos] == '}')
        pos += 1
    return text[match.start():text.index(';', pos) + 1]


def touch_source():
    declarations = r'''
#include <assert.h>
#include <stddef.h>
#include <string.h>
#include "constants/battle_menu.h"
#include "constants/moves.h"
typedef unsigned char u8;typedef unsigned short u16;typedef signed short s16;typedef unsigned int u32;typedef int BOOL;
#define TRUE 1
#define FALSE 0
#define GF_ASSERT assert
#define TOUCH_MENU_NO_INPUT -1
#define TOUCHSCREEN_RECTLIST_END 255
#define BATTLE_TYPE_TUTORIAL 1
typedef union {struct {u8 top,bottom,left,right;} rect;} TouchscreenHitbox;
static struct {int touchNew,touchHeld;u32 touchX,touchY;} gSystem;
typedef struct {int menuX,menuY;} BattleMenuCursor;
typedef struct {int commandX,commandY,moveX,moveY;} BattleCursorPosition;
typedef struct {int battleType;} BattleSystem;
typedef struct {u16 moveNo[4];int pp[4];} BattleInputFightMenu;
typedef struct BattleInput {
    BattleSystem *battleSystem;int curMenuId,isTouchDisabled,battlerType,keyPressed,ssMenuId;
    BattleMenuCursor menuCursor;void *cursor;struct {BattleInputFightMenu fight;} menu;
    struct {struct {const s16 *screenOffsets;const void *touchscreenHitbox;int bufferIndex,ret,shouldDeleteAfter;} button;} feedback;
} BattleInput;
typedef struct {
    int unk_00,paletteId,screenBufferIds[4],priority[4];
    const TouchscreenHitbox *touchscreenRect;const int *touchInput;const u8 *rectPaletteIds;
    int (*funcCursor)(BattleInput*,int);void (*funcSaveCursorPos)(BattleInput*,int);
    void (*funcCreateMenuObjects)(void);int (*funcTouchCallback)(BattleInput*,int,int);
} BattleMenuTemplate;
static int saved=-1,palette=-1,hidden,updated,disabled,feedbacks,cursorInput=-1,tutorialInput=-1;
static int BattleSystem_GetBattleType(BattleSystem *s){return s->battleType;}
static int BattleInput_CatchingTutorialMain(BattleInput *b){return tutorialInput;}
static int BattleInput_CheckCursorInput(BattleInput *b){return cursorInput;}
static void BattleInput_CursorSave_FightMenu(BattleInput *b,int i){saved=i;}
static void BattleInput_CursorSave_MainMenu(BattleInput *b,int i){}
static int BattleInput_CursorMove_FightMenu(BattleInput *b,int j){return -1;}
static int BattleInput_CursorMove_MainMenu(BattleInput *b,int j){return -1;}
static void BattleInput_CreateFightMenuObjects(void){}
static void BattleInput_CreateMainMenuObjectsInitial(void){}
static int BattleInput_TouchCallback_MainMenu(BattleInput *b,int ret,int p){palette=p;return ret;}
static void BattleInput_ButtonFeedbackDummy(BattleInput *b,int p){palette=p;}
static void Task_FightMenuButtonFeedback(void){}
static void BattleInput_StartFeedbackTask(void (*task)(void),BattleInput *b){feedbacks++;}
static BattleCursorPosition cursorPos;
static BattleCursorPosition *OpponentData_GetCursorPosition(void *p){return &cursorPos;}
static void *BattleSystem_GetOpponentData(BattleSystem *s,int b){return s;}
static int BattleSystem_GetBattlerFromBattlerType(BattleSystem *s,int b){return b;}
static void MI_CpuClear8(void *p,int n){memset(p,0,n);}
static void BattleCursor_Disable(void *p){disabled++;}
static void BattleInput_SingleScreen_Hide(BattleInput *b){hidden++;}
static void BattleInput_SingleScreen_Update(BattleInput *b){updated++;}
static int BattleInput_SingleScreen_GetMenuKind(int m){return m;}
static int BattleInput_SingleScreen_GetSelection(BattleInput *b,int k){return 0;}
static void SingleScreen_SetBattleMenu(int k,int s){}
'''
    arrays = '\n'.join(declaration(INPUT, name) for name in (
        'sTouchscreenRectFightMenuButtons',
        'sTouchscreenRectMainMenuButtons', 'sTouchArrayMainMenu', 'sRectPaletteIdsMainMenu',
        'sTouchArrayFightMenu', 'sRectPaletteIdsFightMenu',
        'sFightMenuButtonsScreenOffsets', 'sFightMenuButtonsTouchscreenRect'))
    arrays += '\n#ifdef SINGLE_SCREEN\n' + declaration(INPUT, 'sSingleScreenFightTouchRects') + '\n#endif\n'
    text = (ROOT / INPUT).read_text()
    # Keep every production fight-template field, rather than duplicating its mapping.
    entry = re.search(r'\[BATTLE_MENU_FIGHT\] = \{.*?\n\s*\},', text, re.S)[0]
    entry += re.search(r'\[BATTLE_MENU_MAIN\] = \{.*?\n\s*\},', text, re.S)[0]
    return declarations + arrays + '\n' + game.function_source(INPUT, 'BattleInput_TouchCallback_FightMenu') + '\nstatic const BattleMenuTemplate sBattleMenuTemplates[BATTLE_MENU_20+1]={' + entry + '};\n' + '\n'.join(
        game.function_source('src/touchscreen.c', n) for n in (
            'TouchscreenHitbox_FindRectAtPoint', 'TouchscreenHitbox_FindRectAtTouchNew')) + '\n' + game.function_source(INPUT, 'BattleInput_CheckTouch') + r'''
static BattleSystem systemState;static BattleInput input;
static void reset(void){
    memset(&input,0,sizeof(input));input.battleSystem=&systemState;systemState.battleType=0;
    input.curMenuId=BATTLE_MENU_FIGHT;input.ssMenuId=BATTLE_MENU_NONE;
    for(int i=0;i<4;i++)input.menu.fight.moveNo[i]=MOVE_TACKLE;
    saved=palette=-1;hidden=updated=disabled=feedbacks=0;cursorInput=tutorialInput=-1;
    memset(&gSystem,0,sizeof(gSystem));
}
static int tap(int x,int y){gSystem.touchNew=1;gSystem.touchX=x;gSystem.touchY=y;return BattleInput_CheckTouch(&input);}
'''


def cell_oams(data):
    if data[0] == 0x10:
        data = lz10_decompress(data)
    assert data[:4] == b'RECN' and data[16:20] == b'KBEC'
    count, extended, offset, mapping = struct.unpack_from('<HHII', data, 24)
    assert extended == 1 and mapping == 1
    cells = 24 + offset
    oams = cells + count * 16
    output = []
    sizes = (((8, 8), (16, 16), (32, 32), (64, 64)),
             ((16, 8), (32, 8), (32, 16), (64, 32)),
             ((8, 16), (8, 32), (16, 32), (32, 64)))
    for index in range(count):
        n, attr, start = struct.unpack_from('<HHI', data, cells + index * 16)
        objects = []
        for j in range(n):
            a, b, c = struct.unpack_from('<HHH', data, oams + start + j * 6)
            shape, size = a >> 14, b >> 14
            assert shape < 3 and not a & 0x2300  # 4bpp, unrotated, visible
            x, y = b & 511, a & 255
            if x >= 256:
                x -= 512
            if y >= 128:
                y -= 256
            width, height = sizes[shape][size]
            objects.append((x, y, width, height, c & 1023))
        output.append(objects)
    return output


def opaque_box_bounds(cell, character):
    if character[0] == 0x10:
        character = lz10_decompress(character)
    assert character[:4] == b'RGCN' and character[16:20] == b'RAHC'
    length, offset = struct.unpack_from('<II', character, 40)
    pixels = character[24 + offset:24 + offset + length]
    assert len(pixels) == length
    points = []
    for x, y, width, height, tile in cell_oams(cell)[0]:
        for py in range(height):
            for px in range(width):
                address = tile * 64 + ((py // 8) * (width // 8) + px // 8) * 32 + (py % 8) * 4 + px % 8 // 2
                value = (pixels[address] >> ((px & 1) * 4)) & 15
                if value:
                    points.append((x + px, y + py))
    assert points
    return min(y for x, y in points), max(y for x, y in points)


def hp_source():
    text = (ROOT / HP).read_text()
    enum = re.search(r'typedef enum HPBarType \{.*?\} HPBarType;', text, re.S)[0]
    templates = re.findall(r'^static const ManagedSpriteTemplate (sSpriteTemplate_\w+) =', text, re.M)
    return r'''
#include <assert.h>
#include <stddef.h>
typedef unsigned char u8;typedef signed char s8;typedef signed short s16;
typedef unsigned int u32;typedef int s32;typedef int BOOL;
#define TRUE 1
#define FALSE 0
#define GF_ASSERT assert
#define NNS_G2D_VRAM_TYPE_2DMAIN 0
#define FX32_ONE 4096
#define FX32_CONST(x) ((int)((x)*4096))
static int FX_Mul(int a,int b){return a*b/4096;}
static int GF_SinDegNoWrap(int angle){return angle<180?4096:-4096;}
typedef struct {int x,y,z,animation,drawPriority,pal,vram,resIdList[6],bgPriority,vramTransfer;} ManagedSpriteTemplate;
typedef struct {int x,y,animActive,frame,draw;} Sprite;
typedef struct {Sprite *sprite;} ManagedSprite;
typedef int SpriteSystem;typedef int SpriteManager;
typedef struct {int destroyed;} SysTask;
typedef struct {int type,slideDone,slideOut,bobAngle;ManagedSprite *boxObj,*arrowObj;SysTask *sysTask;void *battleSystem;} BattleHpBar;
static Sprite created;static ManagedSprite managed={&created};static SysTask active;
#define BATTLE_TYPE_PAL_PARK 1
#define BATTLE_TYPE_SAFARI 2
static int taskCreates;
static int BattleSystem_GetBattleType(void *b){return 0;}
static void Sprite_SetAnimActiveFlag(Sprite *s,int f){s->animActive=f;}
static void Sprite_SetAnimationFrame(Sprite *s,int f){s->frame=f;}
static void ManagedSprite_SetDrawFlag(ManagedSprite *s,int f){s->sprite->draw=f;}
static void BattleHpBar_StartBobTask(BattleHpBar*);
static void BattleHpBar_StopBobTask(BattleHpBar*);
static void BattleHpBar_SetArrowDrawFlag(BattleHpBar*,int);
static void Task_BattleHpBarBob(SysTask*,void*);
static ManagedSprite *SpriteSystem_NewSprite(SpriteSystem *s,SpriteManager *m,const ManagedSpriteTemplate *t){created.x=t->x;created.y=t->y;return &managed;}
static void Sprite_TickFrame(Sprite *s){}
static void Sprite_SetPositionXY(Sprite *s,int x,int y){s->x=x;s->y=y;}
static void ManagedSprite_GetPositionXY(ManagedSprite *s,s16 *x,s16 *y){*x=s->sprite->x;*y=s->sprite->y;}
static void ManagedSprite_SetPositionXY(ManagedSprite *s,int x,int y){Sprite_SetPositionXY(s->sprite,x,y);}
static SysTask *SysTask_CreateOnMainQueue(void (*fn)(SysTask*,void*),void *data,int p){taskCreates++;active.destroyed=0;return &active;}
static void SysTask_Destroy(SysTask *s){s->destroyed++;}
static void Task_BattleHpBarSlide(SysTask*,void*);
static void BattleHpBar_CompactInitialize(ManagedSprite *s){}
''' + enum + '\n' + declaration(HP, 'sHpBarArrowXOffsets') + '\n' + '\n'.join(declaration(HP, n) for n in templates) + '\n' + '\n'.join(
        game.function_source(HP, n) for n in (
            'BattleHpBar_IsCompact', 'BattleHpBar_Util_GetHpBoxSpriteTemplate', 'BattleHpBar_CreateBoxSprite',
            'BattleHpBar_SetOffset', 'BattleHpBar_StartSlide', 'Task_BattleHpBarSlide',
            'BattleHpBar_StopBobTask', 'Task_BattleHpBarBob',
            'BattleHpBar_StartBobTask','BattleHpBar_SetArrowDrawFlag',
            'BattleHpBar_StartActiveEffect','BattleHpBar_StopActiveEffect'))


class BattleControlsGeometryTests(unittest.TestCase):
    compile_run = game.GameLogicTests.compile_run

    def test_visible_card_centres_use_matching_move_palette_and_saved_index(self):
        source = touch_source() + r'''
int main(void){
    const int points[][2]={{68,140},{188,140},{68,177},{188,177}};
    for(int i=0;i<4;i++){
        reset();assert(tap(points[i][0],points[i][1])==i+1);
        assert(saved==i+1 && palette==8+i && input.keyPressed==0);
        assert(disabled==1 && feedbacks==1);
#ifdef SINGLE_SCREEN
        assert(hidden==1);
#endif
    }return 0;
}
'''
        self.compile_run(source, '-DSINGLE_SCREEN', '-Wno-unused-function', '-Wno-sign-compare')

    def test_visible_edges_gaps_and_field_do_not_activate_old_touch_cancel(self):
        source = touch_source() + r'''
int main(void){
    const int accepted[][3]={{14,131,1},{121,159,1},{134,131,2},{241,159,2},
      {14,163,3},{121,191,3},{134,163,4},{241,191,4},{68,159,1},{68,163,3}};
    for(unsigned i=0;i<sizeof(accepted)/sizeof(*accepted);i++){
        reset();assert(tap(accepted[i][0],accepted[i][1])==accepted[i][2]);
    }
    const int ignored[][2]={{68,52},{68,130},{68,160},{68,161},{68,162},{122,140},
      {133,140},{130,177},{242,177},{0,177},{255,177},{68,192},{68,0}};
    for(unsigned i=0;i<sizeof(ignored)/sizeof(*ignored);i++){
        reset();assert(tap(ignored[i][0],ignored[i][1])==-1);
        assert(saved==-1 && feedbacks==0 && hidden==0);
    }return 0;
}
'''
        self.compile_run(source, '-DSINGLE_SCREEN', '-Wno-unused-function', '-Wno-sign-compare')

    def test_empty_new_touch_disabled_and_existing_keyboard_fallback(self):
        source = touch_source() + r'''
int main(void){
    reset();input.menu.fight.moveNo[2]=MOVE_NONE;
    assert(tap(68,177)==-1 && saved==-1 && feedbacks==0);
    reset();input.menu.fight.pp[0]=0;assert(tap(68,140)==1);
    reset();gSystem.touchHeld=1;gSystem.touchX=68;gSystem.touchY=140;
    assert(BattleInput_CheckTouch(&input)==-1 && saved==-1);
    reset();input.isTouchDisabled=1;assert(tap(68,140)==-1 && feedbacks==0);
    for(int i=0;i<5;i++){
        reset();cursorInput=i;int result=BattleInput_CheckTouch(&input);
        assert(result==(i?i:BATTLE_INPUT_CANCEL));assert(saved==i && input.keyPressed==1);
        assert(palette==(i?7+i:4));
    }
    reset();systemState.battleType=BATTLE_TYPE_TUTORIAL;tutorialInput=2;
    assert(tap(68,177)==2 && saved==2);return 0;
}
'''
        self.compile_run(source, '-DSINGLE_SCREEN', '-Wno-unused-function', '-Wno-sign-compare')

    def test_ordinary_build_preserves_original_touch_and_cancel_geometry(self):
        source = touch_source() + r'''
int main(void){
    reset();assert(tap(68,52)==BATTLE_INPUT_MOVE_1 && saved==1 && palette==8);
    reset();assert(tap(188,52)==BATTLE_INPUT_MOVE_2 && saved==2 && palette==9);
    reset();assert(tap(68,177)==BATTLE_INPUT_CANCEL && saved==0 && palette==4);
    reset();input.menu.fight.moveNo[0]=MOVE_NONE;assert(tap(68,52)==-1);
    return 0;
}
'''
        self.compile_run(source, '-Wno-unused-function', '-Wno-sign-compare')

    def test_other_menu_still_uses_its_original_touch_rectangles(self):
        source = touch_source() + r'''
int main(void){
    const int points[][4]={{68,52,BATTLE_INPUT_FIGHT,1},{20,177,BATTLE_INPUT_BAG,2},
      {200,177,BATTLE_INPUT_POKEMON,3},{130,177,BATTLE_INPUT_RUN,4}};
    for(int i=0;i<4;i++){
        reset();input.curMenuId=BATTLE_MENU_MAIN;
        assert(tap(points[i][0],points[i][1])==points[i][2]);assert(palette==points[i][3]);
    }return 0;
}
'''
        self.compile_run(source, '-DSINGLE_SCREEN', '-Wno-unused-function', '-Wno-sign-compare')

    def test_actual_cursor_keeps_a_b_and_supplies_empty_slot_mask(self):
        source = touch_source().replace(
            'static int BattleInput_CursorMove_FightMenu(BattleInput *b,int j){return -1;}',
            'static int BattleInput_CursorMove_FightMenu(BattleInput*,int);')
        source += r'''
#define MAX_MON_MOVES 4
#define FX32_CONST(x) (x)
enum {PAD_KEY_UP=1,PAD_KEY_DOWN,PAD_KEY_LEFT,PAD_KEY_RIGHT,PAD_BUTTON_A,PAD_BUTTON_B};
static int pressed;
static void MI_CpuCopy8(const void *s,void *d,int n){memcpy(d,s,n);}
static void BattleCursor_SetRectWithOffset(void *c,int l,int r,int t,int b,int z){}
static u32 BattleCursor_CheckKeyInput(BattleMenuCursor *c,int cols,int rows,u8 *grid){
    assert(cols==2);
#ifdef SINGLE_SCREEN
    assert(rows==2 && grid[3]==255);
#else
    assert(rows==3 && grid[3]==4);
#endif
    return pressed;
}
'''
        source += declaration(INPUT, 'sCursorArrayFightMenu') + '\n'
        source += game.function_source(INPUT, 'BattleInput_CursorMove_FightMenu') + r'''
int main(void){
    reset();input.menu.fight.moveNo[3]=MOVE_NONE;
    for(int i=0;i<3;i++){
        input.menuCursor.menuX=i&1;input.menuCursor.menuY=i>>1;pressed=PAD_BUTTON_A;
        assert(BattleInput_CursorMove_FightMenu(&input,0)==i+1);
    }
    pressed=PAD_BUTTON_B;assert(BattleInput_CursorMove_FightMenu(&input,0)==0);
    cursorPos.moveX=1;cursorPos.moveY=1;
    assert(BattleInput_CursorMove_FightMenu(&input,1)==-1);
    assert(input.menuCursor.menuX==0 && input.menuCursor.menuY==0);
#ifdef SINGLE_SCREEN
    cursorPos.moveX=0;cursorPos.moveY=2;
    assert(BattleInput_CursorMove_FightMenu(&input,1)==-1);
    assert(input.menuCursor.menuX==0 && input.menuCursor.menuY==0);
#endif
    return 0;
}
'''
        for flags in ((), ('-DSINGLE_SCREEN',)):
            with self.subTest(single_screen=bool(flags)):
                self.compile_run(source, *flags, '-Wno-unused-function', '-Wno-sign-compare')

    def test_actual_hp_position_routes_keep_opaque_double_bars_above_panel(self):
        if not (ROOT / 'files/a/0/0/8').exists():
            self.skipTest('Requires the locally supplied battle sprite archive')
        members, _ = unpack_narc((ROOT / 'files/a/0/0/8').read_bytes())
        bounds = [opaque_box_bounds(members[c], members[g]) for c, g in ((199, 200), (202, 203))]
        arrow_bottom = max(y + h - 1 for cell in cell_oams(members[184])[1:]
                           for x, y, w, h, tile in cell)
        # The decoder must inspect actual opaque pixels, not padded 64px OAMs.
        self.assertEqual(bounds, [(-18, 16), (-18, 16)])
        checks = r'''
int main(void){
    const int bottom[]={BOTTOM_LHS,BOTTOM_RHS};
    const int types[]={HP_BAR_TYPE_DOUBLE_PLAYER_LHS,HP_BAR_TYPE_DOUBLE_PLAYER_RHS};
    int previousY=0;(void)previousY;(void)bottom;
    for(int i=0;i<2;i++)for(int withArrow=0;withArrow<2;withArrow++){
        const ManagedSpriteTemplate *t=BattleHpBar_Util_GetHpBoxSpriteTemplate(types[i]);
        #ifdef SINGLE_SCREEN
        assert(t->x==(i?192:64) && t->y==116);
#else
        if(i && !withArrow)assert(t->y-previousY==29);
#endif
        if(!withArrow)previousY=t->y;
        Sprite arrow={0};ManagedSprite arrowObj={&arrow};
        BattleHpBar hp={.type=types[i],.boxObj=BattleHpBar_CreateBoxSprite(0,0,types[i]),
          .arrowObj=withArrow?&arrowObj:NULL};
        assert(hp.boxObj->sprite->x==t->x && hp.boxObj->sprite->y==t->y);
        BattleHpBar_SetOffset(&hp,0,0);
        for(int angle=0;angle<360;angle+=20){
            hp.bobAngle=angle;Task_BattleHpBarBob(NULL,&hp);
            assert(hp.boxObj->sprite->y>=t->y-1 && hp.boxObj->sprite->y<=t->y+1);
#ifdef SINGLE_SCREEN
            assert(hp.boxObj->sprite->y==116 && hp.boxObj->sprite->y+11==127);
            if(withArrow)assert(arrow.y+ARROW_BOTTOM<128);
#else
            assert(t->y==(i?132:103));
#endif
            if(withArrow)assert(arrow.x==hp.boxObj->sprite->x-
#ifdef SINGLE_SCREEN
                48
#else
                72
#endif
                && arrow.y==hp.boxObj->sprite->y);
        }
        hp.sysTask=&active;BattleHpBar_StopBobTask(&hp);
        assert(hp.boxObj->sprite->y==t->y && hp.bobAngle==0 && !hp.sysTask);
        for(int out=0;out<2;out++){
            BattleHpBar_StartSlide(&hp,out);int frames=0;
#ifdef SINGLE_SCREEN
            assert(hp.boxObj->sprite->x==t->x+(out?0:(i?256:-256)));
            if(!out)assert(i?hp.boxObj->sprite->x-64>255:hp.boxObj->sprite->x+63<0);
#endif
            int previousX=hp.boxObj->sprite->x;
            while(!hp.slideDone && frames++<20){
                Task_BattleHpBarSlide(&active,&hp);assert(hp.boxObj->sprite->y==t->y);
                int delta=hp.boxObj->sprite->x-previousX;
#ifdef SINGLE_SCREEN
                int direction=(i?1:-1)*(out?1:-1);
                assert(delta*direction>0 && delta*direction<=24);
#else
                assert(out?(delta>=0 && delta<=24):(delta<=0 && delta>=-24));
#endif
                previousX=hp.boxObj->sprite->x;
                if(withArrow)assert(arrow.y==t->y && arrow.x==hp.boxObj->sprite->x-
#ifdef SINGLE_SCREEN
                    48
#else
                    72
#endif
                    );
            }assert(hp.slideDone && frames<20);
            #ifdef SINGLE_SCREEN
            assert(hp.boxObj->sprite->x==t->x+(out?(i?256:-256):0));
            if(out)assert(i?hp.boxObj->sprite->x-64>255:hp.boxObj->sprite->x+63<0);
#else
            assert(hp.boxObj->sprite->x==t->x+(out?160:0));
#endif
        }
    }
    for(int i=0;i<2;i++){
        Sprite arrow={0};ManagedSprite arrowObj={&arrow};
        BattleHpBar hp={.type=types[i],.boxObj=BattleHpBar_CreateBoxSprite(0,0,types[i]),.arrowObj=&arrowObj};
        const ManagedSpriteTemplate *t=BattleHpBar_Util_GetHpBoxSpriteTemplate(types[i]);
        BattleHpBar_SetOffset(&hp,0,0);int before=taskCreates;
        BattleHpBar_StartActiveEffect(&hp);assert(arrow.animActive && arrow.draw);
#ifdef SINGLE_SCREEN
        assert(!hp.sysTask && taskCreates==before);
#else
        assert(hp.sysTask && taskCreates==before+1);
#endif
        BattleHpBar_StopActiveEffect(&hp);
        assert(!hp.sysTask && !arrow.animActive && !arrow.draw && !arrow.frame);
        assert(hp.boxObj->sprite->x==t->x && hp.boxObj->sprite->y==t->y);
    }
    const int unaffected[]={HP_BAR_TYPE_SINGLE_PLAYER,HP_BAR_TYPE_SINGLE_ENEMY,
      HP_BAR_TYPE_DOUBLE_ENEMY_LHS,HP_BAR_TYPE_DOUBLE_ENEMY_RHS,HP_BAR_TYPE_SAFARI,HP_BAR_TYPE_PALPARK};
    const int ordinaryY[]={116,36,16,45,116,116};
    const int singleY[]={106,28,16,45,116,116};
    for(int i=0;i<6;i++){
        const ManagedSpriteTemplate *t=BattleHpBar_Util_GetHpBoxSpriteTemplate(unaffected[i]);
#ifdef SINGLE_SCREEN
        assert(t->y==singleY[i]);
#else
        assert(t->y==ordinaryY[i]);
#endif
        BattleHpBar hp={.type=unaffected[i],.boxObj=BattleHpBar_CreateBoxSprite(0,0,unaffected[i])};
        BattleHpBar_SetOffset(&hp,7,-1);assert(hp.boxObj->sprite->x==t->x+7 && hp.boxObj->sprite->y==t->y-1);
    }return 0;
}
'''.replace('BOTTOM_LHS', str(bounds[0][1])).replace('BOTTOM_RHS', str(bounds[1][1])).replace('ARROW_BOTTOM', str(arrow_bottom))
        source = hp_source() + checks
        for flags in ((), ('-DSINGLE_SCREEN',)):
            with self.subTest(single_screen=bool(flags)):
                self.compile_run(source, *flags, '-Wno-unused-function', '-Wno-unused-variable')


if __name__ == '__main__':
    unittest.main()
