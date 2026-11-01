"""Execute the card helper with encoded labels from the production resources."""
from pathlib import Path
import unittest
import test_game_logic as game
import test_modern_moves
from game_text import game_text
from move_resources import PRESENTATION

ROOT = Path(__file__).resolve().parents[2]


class MoveCardTests(unittest.TestCase):
    compile_run = game.GameLogicTests.compile_run

    def test_actual_card_helper_reads_all_labels_and_keeps_original_fallback(self):
        actual = game.function_source('src/battle/battle_input.c', 'BattleInput_SingleScreen_MoveName')
        arrays, cases, checks = [], [], []
        for move_id, text in PRESENTATION.items():
            words = ','.join(map(str, game_text(text['card'], ROOT/'charmap.txt')))
            arrays.append(f'static const u16 card{move_id}[]={{ {words} }};')
            cases.append(f'case {move_id}: memcpy(storage.words,card{move_id},sizeof(card{move_id}));break;')
            checks.append(f'assert(!memcmp(BattleInput_SingleScreen_MoveName({move_id})->words,card{move_id},sizeof(card{move_id})));')
        source = test_modern_moves.ModernMoveTests().source() + r'''
#include "constants/charcode.h"
typedef struct { u16 words[32]; } String;
typedef struct { int bank; } MsgData;
enum { HEAP_ID_BATTLE, MSGDATA_LOAD_LAZY, NARC_msgdata_msg };
static String storage;
static MsgData messages;
static int opens,closes,unavailable;
static String *GetMoveName(int move,int heap) { storage.words[0]=move;storage.words[1]=EOS;return &storage; }
static MsgData *NewMsgDataFromNarc(int mode,int narc,int bank,int heap) {
    assert(bank==829);if(unavailable)return NULL;opens++;messages.bank=bank;return &messages;
}
static void DestroyMsgData(MsgData *msg) { closes++; }
''' + '\n'.join(arrays) + r'''
static String *NewString_ReadMsgData(MsgData *msg,int move) {
    assert(msg->bank==829);switch(move) {
''' + '\n'.join(cases) + r'''
    default:assert(0);
    }return &storage;
}
''' + actual + r'''
int main(void) {
    assert(BattleInput_SingleScreen_MoveName(33)->words[0]==33);
    assert(opens==0 && closes==0);
#if QOL_MODERN_MOVES
''' + '\n'.join(checks) + r'''
    assert(opens==QOL_EXTENDED_MOVE_COUNT && closes==opens);
    unavailable=1;
    assert(BattleInput_SingleScreen_MoveName(577)->words[0]==577);
    assert(closes==opens);
#else
    assert(BattleInput_SingleScreen_MoveName(577)->words[0]==577);
    assert(BattleInput_SingleScreen_MoveName(608)->words[0]==608);
    assert(opens==0 && closes==0);
#endif
    return 0;
}
'''
        for flags in ((), ('-DQOL_MODERN_MOVES=1',)):
            self.compile_run(source, *flags, '-Wno-unused-function')
        self.assertIn('BattleInput_SingleScreen_MoveName(menu->moveNo[i])',
                      game.function_source('src/battle/battle_input.c', 'BattleInput_SingleScreen_BuildItems'))


if __name__ == '__main__':
    unittest.main()
