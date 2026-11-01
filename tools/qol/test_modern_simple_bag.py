"""Exercise the real player bag path through stage recovery and consumption."""
import unittest

import test_game_logic as game
import test_modern_simple as simple


class SimplePlayerBagTests(unittest.TestCase):
    def test_player_xitems_apply_once_and_consume_only_after_success(self):
        source = simple.xitem_source() + r'''
typedef int String;
typedef int MsgData;
typedef int Party;
typedef int PCStorage;
enum HeapID { TEST_HEAP = 1 };
enum {
 BATTLE_BAG_STATE_FADE_OUT,BATTLE_BAG_STATE_CLOSE_MESSAGE,BATTLE_BAG_STATE_WAIT_MESSAGE,
 MSGDATA_LOAD_LAZY,NARC_msgdata_msg,NARC_msg_msg_0040_bin,
 msg_0005_00046,msg_0040_00037,msg_0005_00034,msg_0005_00044,msg_0005_00047,
 msg_0005_00048,msg_0005_00045,PARTY_SIZE=6
};
typedef struct {
 BattleSystem *battleSystem;
 int battlerId,selectedItem,heapID,embargo,twoTargets,targetSemiInvulnerable,targetSubstitute;
 void *profile;
} BattleBagContext;
typedef struct {
 BattleBagContext *context;
 int pocket,nextState;
 void *msgFormat;
 String *string;
 MsgData *msgData;
} BattleBagMenu;
static int quantity,consumeCalls,cursorItem,cursorPocket,messages,expectedItem;
static BattleContext *BattleSystem_GetBattleContext(BattleSystem *s){return s->ctx;}
static int *BattleSystem_GetBag(BattleSystem *s){return &quantity;}
static int *BattleSystem_GetBagCursor(BattleSystem *s){return &cursorItem;}
static int Bag_TakeItem(int *bag,int item,int amount,enum HeapID heap) {
 assert(bag==&quantity&&item==expectedItem&&amount==1&&quantity>0);
 consumeCalls++;quantity-=amount;return 1;
}
static void BagCursor_Battle_SetLastUsedItem(int *cursor,int item,int pocket) {
 assert(cursor==&cursorItem);cursorItem=item;cursorPocket=pocket;
}
static void ReadMsgDataIntoString(MsgData *m,int id,String *s){assert(id==msg_0005_00034);}
static void BattleBagMenu_ShowMessage(BattleBagMenu *m){messages++;}
// These SDK/UI boundaries belong to other pockets or the separate Embargo path.
static String *NewString_ReadMsgData(MsgData *m,int id){assert(0);return NULL;}
static void *Mon_GetBoxMon(Pokemon *m){assert(0);return NULL;}
static void BufferBoxMonNickname(void *m,int i,void *mon){assert(0);}
static void BufferMoveName(void *m,int i,int move){assert(0);}
static void StringExpandPlaceholders(void *m,String *out,String *in){assert(0);}
static void String_Delete(String *s){assert(0);}
static MsgData *NewMsgDataFromNarc(int a,int b,int c,int d){assert(0);return NULL;}
static void BufferPlayersName(void *m,int i,void *profile){assert(0);}
static void DestroyMsgData(MsgData *m){assert(0);}
static Party *BattleSystem_GetParty(BattleSystem *s,int b){assert(0);return NULL;}
static PCStorage *BattleSystem_GetPcStorage(BattleSystem *s){assert(0);return NULL;}
static int Party_GetCount(Party *p){assert(0);return 0;}
static int PCStorage_FindFirstBoxWithEmptySlot(PCStorage *p){assert(0);return 0;}
'''
        for name in ('BattleBagMenu_GetBattlerSelectedMonIndex',
                     'BattleBagMenu_ConsumeItem', 'BattleBagMenu_TryUseItem'):
            source += game.function_source('src/battle/battle_bag_menu.c', name) + '\n'
        source += r'''
int main(void) {
 for(int item=0;item<6;item++)for(int before=0;before<=12;before++)
 for(int hasSimple=0;hasSimple<2;hasSimple++)for(int suppress=0;suppress<2;suppress++) {
  BattleContext c=fixture();BattleSystem s={&c};int stat=xstats[item];
  c.battleMons[0].ability=ABILITY_MOLD_BREAKER;
  c.battleMons[1].ability=hasSimple?ABILITY_SIMPLE:ABILITY_NONE;
  c.battleMons[1].moveEffectFlags=suppress?MOVE_EFFECT_FLAG_ABILITY_SUPPRESSED:0;
  c.battleMons[1].statChanges[stat]=before;c.selectedMonIndex[1]=activeSlot;
  BattleBagContext context={0};context.battleSystem=&s;context.battlerId=1;
  context.selectedItem=xitems[item];context.heapID=TEST_HEAP;
  BattleBagMenu menu={0};menu.context=&context;menu.pocket=BTLPOCKETLIST_BATTLE_ITEMS;
  quantity=3;consumeCalls=cursorItem=cursorPocket=messages=0;expectedItem=xitems[item];
  int oldMoods=moods;
  int gain=QOL_MODERN_BATTLE?(hasSimple&&!suppress?4:2):1;
  if(before+gain>12)gain=12-before;
  int result=BattleBagMenu_TryUseItem(&menu);
  assert(c.battleMons[1].statChanges[stat]==before+gain);
  assert(moods==oldMoods+!!gain); // Recovery happened exactly once.
  assert(quantity==3-!!gain&&consumeCalls==!!gain);
  assert(!c.selfTurnData[0].moldBreakerFlag);
  if(gain) {
   assert(result==BATTLE_BAG_STATE_FADE_OUT&&!messages);
   assert(cursorItem==xitems[item]&&cursorPocket==BTLPOCKETLIST_BATTLE_ITEMS);
  } else {
   assert(result==BATTLE_BAG_STATE_WAIT_MESSAGE&&messages==1);
   assert(menu.nextState==BATTLE_BAG_STATE_CLOSE_MESSAGE&&!cursorItem&&!cursorPocket);
  }
 }
 return 0;
}
'''
        for flags in ((), ('-DQOL_MODERN_BATTLE=1',)):
            game.GameLogicTests.compile_run(self, source, *flags,
                                            '-Wno-unused-function',
                                            '-Wno-misleading-indentation')


if __name__ == '__main__':
    unittest.main()
