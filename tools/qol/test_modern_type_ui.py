import unittest

import test_game_logic as game


class ModernTypeUiTests(unittest.TestCase):
    compile_run = game.GameLogicTests.compile_run

    def test_pokedex_separate_fairy_member_and_palette_keep_legacy_mapping(self):
        source = game.ROOT.joinpath('src/application/pokedex/pokedex_text_util.c').read_text()
        import re
        tables = '\n'.join(re.findall(r'static const u(?:8|32) sTypeIcon\w+\[18\] = \{.*?\};', source))
        functions = '\n'.join(game.function_source('src/application/pokedex/pokedex_text_util.c', name)
                              for name in ('PokedexApp_GetTypeIconCharFile', 'PokedexApp_GetTypeIconPalette'))
        for enabled in (0, 1):
            self.compile_run(f'#define QOL_MODERN_TYPES {enabled}\n#define TYPE_FAIRY 9\n'
                             'typedef unsigned int u32;typedef unsigned char u8;\n#include <assert.h>\n'
                             + tables + functions + '''
int main(void) {
 assert(PokedexApp_GetTypeIconCharFile(0)==36);
 assert(PokedexApp_GetTypeIconPalette(0)==0);
 assert(PokedexApp_GetTypeIconCharFile(9)==(QOL_MODERN_TYPES?123:36));
 assert(PokedexApp_GetTypeIconPalette(9)==(QOL_MODERN_TYPES?1:0));
 return 0;
}
''')

    def test_hall_matron_keeps_special_question_mark_label(self):
        function = game.function_source('src/frontier/battle_hall_app.c', 'BattleHallApp_ReadTypeName')
        for enabled in (0, 1):
            self.compile_run(f'#define QOL_MODERN_TYPES {enabled}\n' + '''
#include <assert.h>
typedef unsigned int u32;typedef unsigned short u16;
typedef int MsgData;typedef struct {u16 data[12];} String;
#define TYPE_MYSTERY 9
#define EOS 0xFFFF
void CopyU16ArrayToString(String *s,const u16 *v) {for(int i=0;;i++){s->data[i]=v[i];if(v[i]==EOS)break;}}
void ReadMsgDataIntoString(MsgData *m,u32 id,String *s) {(void)m;s->data[0]=id;s->data[1]=EOS;}
''' + function + '''
int main(void) {
 MsgData m=0;String s;
 BattleHallApp_ReadTypeName(&m,9,&s);
 assert(s.data[0]==(QOL_MODERN_TYPES?0x1AC:9));
 if(QOL_MODERN_TYPES)assert(s.data[1]==0x1AC&&s.data[2]==0x1AC&&s.data[3]==EOS);
 BattleHallApp_ReadTypeName(&m,1,&s);assert(s.data[0]==1&&s.data[1]==EOS);
 return 0;
}
''')
