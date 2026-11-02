"""Parity and actual battle-command execution for Draining Kiss recovery."""
import importlib
from pathlib import Path
import struct
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / 'files/battledata/script/subscript/subscript_0024_DrainHalfDamageDealt.s'


class ModernDrainSourceTests(unittest.TestCase):
    def transform(self, source):
        scripts = importlib.import_module('battle_scripts')
        transform = getattr(scripts, 'modern_drain_source', None)
        self.assertTrue(callable(transform), 'modern drain source transform is missing')
        return transform(source)

    def test_only_initial_recovery_calculation_changes(self):
        original = SOURCE.read_text()
        modern = self.transform(original)
        self.assertEqual(original[original.index('_011:'):], modern[modern.index('_011:'):])
        self.assertIn('CompareVarToValue OPCODE_EQU, BSCRIPT_VAR_MOVE_NO_CUR, 580, _QolDrainingKiss', modern)
        self.assertIn('    DivideVarByValue BSCRIPT_VAR_HP_CALC, 2\n    GoTo _011\n', modern)
        self.assertIn('_QolDrainingKiss:\n    UpdateVar OPCODE_MUL, BSCRIPT_VAR_HP_CALC, 3\n    DivideVarByValue BSCRIPT_VAR_HP_CALC, 4\n', modern)

    def test_source_drift_and_double_application_are_rejected(self):
        original = SOURCE.read_text()
        changes = (
            ('DivideVarByValue BSCRIPT_VAR_HP_CALC, 2', 'DivideVarByValue BSCRIPT_VAR_HP_CALC, 3'),
            ('BSCRIPT_VAR_HP_CALC, 0, _011', 'BSCRIPT_VAR_HP_CALC, 0, _031'),
            ('HOLD_EFFECT_LEECH_BOOST', 'HOLD_EFFECT_NONE'),
            ('ABILITY_LIQUID_OOZE, _077', 'ABILITY_LIQUID_OOZE, _090'),
            ('BMON_DATA_HEAL_BLOCK_TURNS, 0, _064', 'BMON_DATA_HEAL_BLOCK_TURNS, 1, _064'),
            ('ABILITY_MAGIC_GUARD, _090', 'ABILITY_MAGIC_GUARD, _064'),
            ('UpdateVar OPCODE_DIV, BSCRIPT_VAR_HP_CALC, 100', 'UpdateVar OPCODE_DIV, BSCRIPT_VAR_HP_CALC, 130'),
        )
        for before, after in changes:
            with self.subTest(before=before), self.assertRaisesRegex(ValueError, 'expected source'):
                self.transform(original.replace(before, after))
        for changed in (original + original, original.replace('_031:', ''), self.transform(original)):
            with self.assertRaisesRegex(ValueError, 'expected source'):
                self.transform(changed)

    def test_original_parity_is_checked_before_compiling_transformed_source(self):
        scripts = importlib.import_module('battle_scripts')
        self.assertTrue(callable(getattr(scripts, 'modern_drain_script', None)), 'modern drain compiler is missing')
        with patch.object(scripts, 'compile_battle_script', return_value=b'wrong') as compile_script:
            with self.assertRaisesRegex(ValueError, 'unchanged.*match.*24'):
                scripts.modern_drain_script(b'original')
        compile_script.assert_called_once_with(SOURCE.read_text(), scripts.ROOT)
        with patch.object(scripts, 'compile_battle_script', side_effect=[b'original', b'modern']) as compile_script:
            self.assertEqual(scripts.modern_drain_script(b'original'), b'modern')
        self.assertEqual([call.args[0] for call in compile_script.call_args_list],
                         [SOURCE.read_text(), self.transform(SOURCE.read_text())])


class ModernDrainSdkTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import battle_scripts as scripts
        import nitro_data as nitro
        try:
            scripts.battle_script_tools()
        except FileNotFoundError as error:
            raise unittest.SkipTest(str(error))
        archive = ROOT / 'files/battledata/script/subscript.narc'
        if not archive.is_file():
            raise unittest.SkipTest('original battle subscript archive is absent')
        cls.original = nitro.unpack_narc(archive.read_bytes())[0][24]
        cls.unchanged = scripts.compile_battle_script(SOURCE.read_text())
        cls.modern = scripts.modern_drain_script(cls.original)

    def test_original_sdk_compilation_matches_narc_member(self):
        self.assertEqual(self.unchanged, self.original)
        self.assertEqual(len(self.modern), len(self.original) + 56)

    def test_real_commands_execute_drain_rounding_and_existing_special_paths(self):
        import test_game_logic as game
        def array(data):
            return ','.join(str(word) + 'u' for word in struct.unpack('<' + 'I' * (len(data) // 4), data))
        declarations = r'''
#include <assert.h>
#include <stddef.h>
#include <stdint.h>
#include <string.h>
#include "constants/battle.h"
#include "constants/battle_script.h"
#include "constants/battle_subscript.h"
#include "constants/abilities.h"
#include "constants/pokemon.h"
#include "constants/opcode.h"
#include "constants/items.h"
#include "constants/message_tags.h"
typedef int BOOL; typedef uint32_t u32; typedef uint16_t u16;
#define FALSE 0
#define TRUE 1
#define GF_ASSERT(x) assert(x)
typedef struct {int unused;} BattleSystem;
typedef struct {
 unsigned fieldSideConditionFlags[2];int scriptNarcId,scriptFileId,battlerIdAttacker;
 const u32 *words; int pos,length,vars[70],ability[2],battlerIdAbility;
 int bigRoot,healBlock,updates,applied,message;
} BattleContext;
enum {NARC_a_0_0_1};
#if QOL_MODERN_BATTLE
static int BattleSystem_GetFieldSide(BattleSystem *s,int b){return b&1;}
#endif
#if QOL_MODERN_BATTLE
static void Qol_QueueTailwindStart(BattleSystem *s,BattleContext *c,int side){assert(0);}
#endif
void BattleScriptIncrementPointer(BattleContext *c,int n){c->pos+=n;assert(c->pos>=0&&c->pos<=c->length);}
int BattleScriptReadWord(BattleContext *c){assert(c->pos<c->length);return c->words[c->pos++];}
int *BattleScriptGetVarPointer(BattleSystem *s,BattleContext *c,int v){assert(v>=0&&v<70);return &c->vars[v];}
int BattleSystem_GetBattlerIDBySide(BattleSystem *s,BattleContext *c,int side){
 assert(side==BATTLER_CATEGORY_ATTACKER||side==BATTLER_CATEGORY_DEFENDER);
 return side==BATTLER_CATEGORY_ATTACKER?0:1;}
int BattleSystem_GetMaxBattlers(BattleSystem *s){return 2;}
int GetBattlerAbility(BattleContext *c,int id){assert(id>=0&&id<2);return c->ability[id];}
int GetBattlerVar(BattleContext *c,int id,int field,void *unused){
 assert(id==0&&field==BMON_DATA_HEAL_BLOCK_TURNS);return c->healBlock;}
int GetBattlerHeldItemEffect(BattleContext *c,int id){assert(id==0);return c->bigRoot?HOLD_EFFECT_LEECH_BOOST:0;}
u16 GetBattlerHeldItem(BattleContext *c,int id){assert(id==0);return c->bigRoot;}
int GetItemVar(BattleContext *c,u16 item,int field){assert(field==ITEM_VAR_MODIFIER);return item?30:0;}
int MaskOfFlagNo(int n){return 1u<<n;}
'''
        functions = '\n'.join(game.function_source('src/battle/battle_command.c', name) for name in (
            'BtlCmd_CompareVarToValue', 'BtlCmd_CompareMonDataToValue', 'BtlCmd_UpdateVar',
            'BtlCmd_UpdateVar2', 'BtlCmd_Goto', 'BtlCmd_DivideVarByValue', 'BtlCmd_CheckAbility',
            'BtlCmd_CheckItemHoldEffect', 'BtlCmd_GetItemEffectParam'))
        functions = game.function_source('src/battle/battle_util.c', 'DamageDivide') + functions
        checks = r'''
static const u32 original[]={ORIGINAL};
static const u32 modern[]={MODERN};
static BattleContext run(int updated,int move,int damage,int root,int ooze,int block,int guard){
 BattleContext c={0};BattleSystem s={0};c.words=updated?modern:original;
 c.length=updated?sizeof(modern)/4:sizeof(original)/4;
 c.vars[BSCRIPT_VAR_HIT_DAMAGE]=-damage;c.vars[BSCRIPT_VAR_MOVE_NO_CUR]=move;
 c.vars[BSCRIPT_VAR_BATTLER_ATTACKER]=0;
 c.bigRoot=root;c.healBlock=block;c.ability[0]=guard?ABILITY_MAGIC_GUARD:ABILITY_NONE;
 c.ability[1]=ooze?ABILITY_LIQUID_OOZE:ABILITY_NONE;
 for(int steps=0;steps<100;steps++){
  assert(c.pos<c.length);
  switch(c.words[c.pos]){
  case 14:c.pos++;break;
  case 18:{c.pos++;c.message=BattleScriptReadWord(&c);int tag=BattleScriptReadWord(&c);
   c.pos+=(tag>0)+(tag>TAG_TRNAME)+(tag>TAG_TRCLASS_TRNAME)+(tag>TAG_TRCLASS_TRNAME_ITEM);break;}
  case 30:c.pos+=2;break;
  case 32:BtlCmd_CompareVarToValue(&s,&c);break;
  case 33:BtlCmd_CompareMonDataToValue(&s,&c);break;
  case 50:BtlCmd_UpdateVar(&s,&c);break;
  case 55:BtlCmd_CheckAbility(&s,&c);break;
  case 57:BtlCmd_UpdateVar2(&s,&c);break;
  case 59:BtlCmd_Goto(&s,&c);break;
  case 60:c.pos++;assert(BattleScriptReadWord(&c)==BATTLE_SUBSCRIPT_UPDATE_HP);
   c.updates++;c.applied=c.vars[BSCRIPT_VAR_HP_CALC];break;
  case 85:BtlCmd_DivideVarByValue(&s,&c);break;
  case 166:BtlCmd_CheckItemHoldEffect(&s,&c);break;
  case 168:BtlCmd_GetItemEffectParam(&s,&c);break;
  case 224:return c;
  default:assert(0);
  }
 }
 assert(0);return c;
}
int main(void){
 int damages[]={0,1,2,3,4,5,6,7,8,9,10,11,99,100,101,714,65535};
 int oldMoves[]={71,72,141,409,579,581,0};
 for(unsigned d=0;d<sizeof(damages)/sizeof(*damages);d++)
 for(int root=0;root<2;root++)for(int ooze=0;ooze<2;ooze++)
 for(int block=0;block<2;block++)for(int guard=0;guard<2;guard++){
  int damage=damages[d];
  for(unsigned m=0;m<sizeof(oldMoves)/sizeof(*oldMoves);m++){
   BattleContext a=run(0,oldMoves[m],damage,root,ooze,block,guard);
   BattleContext b=run(1,oldMoves[m],damage,root,ooze,block,guard);
   assert(memcmp(a.vars,b.vars,sizeof(a.vars))==0);
   assert(a.message==b.message&&a.updates==b.updates&&a.applied==b.applied);
   assert(a.battlerIdAbility==b.battlerIdAbility);
  }
  BattleContext c=run(1,580,damage,root,ooze,block,guard);
  int expected=damage*3/4;if(damage>0&&expected==0)expected=1;
  if(root)expected=expected*130/100;
  if(ooze&&guard){assert(c.updates==0&&c.message==0);}
  else if(ooze){assert(c.updates==1&&c.applied==-expected&&c.message==720);}
  else if(block){assert(c.updates==0&&c.message==1054);}
  else {assert(c.updates==1&&c.applied==expected&&c.message==82);}
  assert((c.vars[BSCRIPT_VAR_BATTLE_STATUS]&BATTLE_STATUS_NO_BLINK)!=0);
 }
 return 0;
}
'''.replace('ORIGINAL', array(self.original)).replace('MODERN', array(self.modern))
        game.GameLogicTests.compile_run(self, declarations + functions + checks)
