"""Card names use short labels only where full names would overlap the badge."""
from pathlib import Path
import unittest
import test_game_logic as game
from game_text import game_text
from move_resources import PRESENTATION

ROOT = Path(__file__).resolve().parents[2]


class MoveCardTests(unittest.TestCase):
    compile_run = game.GameLogicTests.compile_run

    def test_actual_card_helper_keeps_original_names_and_abbreviates_long_new_names(self):
        actual = game.function_source('src/battle/battle_input.c', 'BattleInput_SingleScreen_MoveName')
        checks = []
        for move_id, text in PRESENTATION.items():
            words = ','.join(map(str, game_text(text['card'], ROOT/'charmap.txt')))
            checks.append(f'const u16 expected{move_id}[]={{ {words} }};\n'
                          f'assert(!memcmp(BattleInput_SingleScreen_MoveName({move_id})->words,expected{move_id},sizeof(expected{move_id})));')
        source = r'''
#include <assert.h>
#include <string.h>
#include "qol_config.h"
#include "constants/qol_moves.h"
#include "constants/charcode.h"
typedef unsigned short u16;
typedef struct { u16 words[16]; } String;
enum {HEAP_ID_BATTLE};
static String full;
static String *GetMoveName(int move,int heap) { full.words[0]=move;full.words[1]=EOS;return &full; }
static void CopyU16ArrayToString(String *s,const u16 *p) { int i=0;do{s->words[i]=p[i];}while(p[i++]!=EOS); }
''' + actual + r'''
int main(void) {
    assert(BattleInput_SingleScreen_MoveName(33)->words[0]==33);
''' + '\n'.join(f'#if QOL_MODERN_MOVES\n{c}\n#endif' for c in (checks[0],checks[-1])) + r'''
    // Other move cards and feature-off names come straight from the message bank.
    const int ordinary[]={580,586,588};
    for(int i=0;i<3;i++) assert(BattleInput_SingleScreen_MoveName(ordinary[i])->words[0]==ordinary[i]);
#if !QOL_MODERN_MOVES
    assert(BattleInput_SingleScreen_MoveName(577)->words[0]==577);
    assert(BattleInput_SingleScreen_MoveName(608)->words[0]==608);
#endif
    return 0;
}
'''
        for flags in ((),('-DQOL_MODERN_MOVES=1',)):
            self.compile_run(source,*flags,'-Wno-unused-function')
        self.assertIn('BattleInput_SingleScreen_MoveName(menu->moveNo[i])',
                      game.function_source('src/battle/battle_input.c','BattleInput_SingleScreen_BuildItems'))


if __name__ == '__main__':
    unittest.main()
