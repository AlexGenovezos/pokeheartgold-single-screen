"""Long modern names fit the battle party dialog's real String_Cat boundary."""
import unittest
import test_game_logic as game


class MoveNameCapacityTests(unittest.TestCase):
    compile_run = game.GameLogicTests.compile_run

    def test_battle_party_name_buffer_accepts_sixteen_glyph_name_and_preserves_legacy_size(self):
        declarations = r'''
#include <assert.h>
#include <stddef.h>
#include <string.h>
#include "qol_config.h"
typedef unsigned short u16;
typedef unsigned int u32;
typedef struct {int size,maxsize;u16 data[32];} String;
typedef struct {int unused;} Window;
typedef struct {struct {int heapID;} *context;Window pageWindows[3];int *msgData,*msgFormat;} BattlePartyMenu;
typedef int (*AddTextPrinterWithColorFunc)(Window *,int,String *,int,int,int,int,void *);
#define ASSERT_STRING(x) assert(x)
#define GF_ASSERT assert
#define FALSE 0
enum {TEXT_SPEED_NOTRANSFER};
static String output,full;
static int printed,allocated;
static String *String_New(int capacity,int heap){memset(&output,0,sizeof(output));output.maxsize=capacity;allocated=capacity;return &output;}
static String *NewString_ReadMsgData(int *data,int id){return &full;}
static void BufferMoveName(int *format,int field,int move){}
'''
        actual_cat = game.function_source('src/pm_string.c', 'String_Cat')
        edges = r'''
// The relevant templates contain only the move placeholder. Keep the actual
// engine's concatenation bounds check, with message loading/rendering stubbed.
static void StringExpandPlaceholders(int *format,String *out,String *source){String_Cat(out,source);}
static int GetWindowWidth(Window *w){return 16;}
static int FontID_String_GetWidth(int font,String *s,int spacing){return s->size*5;}
static int AddTextPrinterParameterizedWithColor(Window *w,int font,String *s,int x,int y,int speed,int color,void *callback){assert(s->size==full.size);printed++;return 0;}
static void String_Delete(String *s){}
static void ScheduleWindowCopyToVram(Window *w){}
'''
        actual = game.function_source('src/battle/battle_party_menu.c', 'BattlePartyMenu_PrintMoveName')
        checks = r'''
int main(void){
    BattlePartyMenu menu={0};struct {int heapID;} context={0};menu.context=(void *)&context;
    full.size=QOL_MODERN_MOVES?16:15;full.maxsize=32;
    for(int i=0;i<full.size;i++)full.data[i]=300+i;full.data[full.size]=65535;
    BattlePartyMenu_PrintMoveName(&menu,622,0,61,4,0,0);
    assert(printed==1 && allocated==(QOL_MODERN_MOVES?32:16));
    assert(!memcmp(full.data,output.data,(full.size+1)*sizeof(u16)));
    return 0;
}
'''
        for flags in ((), ('-DQOL_MODERN_MOVES=1',)):
            self.compile_run(declarations+actual_cat+edges+actual+checks, *flags)
