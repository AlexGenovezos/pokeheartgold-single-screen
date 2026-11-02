"""Execute the real single-screen X-menu gate and bottom-app transitions."""
from pathlib import Path
import re
import unittest

import test_game_logic as game
from test_game_logic import function_source

ROOT = Path(__file__).resolve().parents[2]


class StartMenuRecoveryTests(unittest.TestCase):
    compile_run = game.GameLogicTests.compile_run
    def run_case(self, checks):
        header = (ROOT / 'include/field/bottom_screen_app.h').read_text()
        apps = re.search(r'enum BottomScreenAppId \{.*?\};', header, re.S).group()
        states = re.search(r'enum BottomScreenAppState \{.*?\};', header, re.S).group()
        header = (ROOT / 'include/start_menu.h').read_text()
        menu_states = re.search(r'typedef enum StartMenuState \{.*?\} StartMenuState;', header, re.S).group()
        declarations = r'''
#include <assert.h>
#include <stddef.h>
#include <string.h>
typedef int BOOL;
typedef unsigned int u32;
enum { FALSE, TRUE, PAD_BUTTON_A=1, PAD_BUTTON_B=2, PAD_BUTTON_X=1024,
       PAD_KEY_UP=64, PAD_KEY_DOWN=128, PAD_KEY_LEFT=32, PAD_KEY_RIGHT=16,
       SEQ_SE_DP_SELECT, FADE_SUB_ONLY, FADE_TYPE_BRIGHTNESS_OUT,
       FADE_TYPE_BRIGHTNESS_IN, HEAP_ID_FIELD1 };
/* ENUMS */
typedef struct FieldSystem FieldSystem;
typedef struct BottomScreenAppManager {
    unsigned char appId, state, nextAppId;
    void *app; FieldSystem *fieldSystem; void *args;
} BottomScreenAppManager;
typedef struct SysTask { BottomScreenAppManager *data; } SysTask;
struct FieldSystem { SysTask *bottomScreenTask; int startMenuCursorPos; };
struct TaskManager;
typedef struct { int state, panelActive, panelCursor, slotValue[8]; void *spriteList; int cursorActive, itemCheckUseData, fieldMoveCheckData; void *exitTaskEnvironment; BOOL (*exitTaskFunc)(struct TaskManager *); } StartMenuTaskData;
typedef struct TaskManager { FieldSystem *fieldSystem; StartMenuTaskData *env; } TaskManager;
static struct { u32 newKeys; } gSystem;
static BottomScreenAppManager manager;
static SysTask bottomTask;
static FieldSystem fieldSystem;
static StartMenuTaskData startMenu;
static TaskManager taskManager;
static int actions, frames, initialized, exited, drawn, destroyed;
static FieldSystem *TaskManager_GetFieldSystem(TaskManager *t) { return t->fieldSystem; }
static void *TaskManager_GetEnvironment(TaskManager *t) { return t->env; }
static void *SysTask_GetData(SysTask *t) { return t->data; }
static unsigned char FieldSystem_GetBottomScreenAppId(FieldSystem *f) { return ((BottomScreenAppManager *)SysTask_GetData(f->bottomScreenTask))->appId; }
static unsigned char FieldSystem_GetBottomScreenAppState(FieldSystem *f) { return ((BottomScreenAppManager *)SysTask_GetData(f->bottomScreenTask))->state; }
static void PlaySE(int seq) {}
static void SpriteList_RenderAndAnimateSprites(void *list) { frames++; }
static BOOL StartMenu_HandleKeyInput(TaskManager *t, FieldSystem *f, StartMenuTaskData *m) { actions++; return TRUE; }
static void FieldSystem_ResetGearRingManagerIfNotSelectingSaveOrPokegear(FieldSystem *f) {}
static void StartMenu_MovePanelCursor(StartMenuTaskData *m, int x, int y) {}
static void BeginNormalPaletteFade(int a,int b,int c,int d,int e,int f,int g) {}
static BOOL IsPaletteFadeFinished(void) { return TRUE; }
static void BottomScreenApps_InitApp(BottomScreenAppManager *m) { initialized++; }
static void BottomScreenApps_UnloadApp(BottomScreenAppManager *m) {}
static void ExitApp(void *bg, void *app) { exited++; }
static BOOL ExitDone(void *bg) { return TRUE; }
static const struct { void (*exit)(void *, void *); BOOL (*isExitDone)(void *); } sBottomScreenApps[9] = {
    {ExitApp,ExitDone},{ExitApp,ExitDone},{ExitApp,ExitDone},{ExitApp,ExitDone},
    {ExitApp,ExitDone},{ExitApp,ExitDone},{ExitApp,ExitDone},{ExitApp,ExitDone},{ExitApp,ExitDone}
};
#define MapObjectManager_PauseAllMovement(...) ((void)0)
#define MapObjectManager_UnpauseAllMovement(...) ((void)0)
#define ItemCheckUseData_Init(...) ((void)0)
#define FieldMove_InitCheckData(...) ((void)0)
#define Task_StartMenu_WaitFade(...) ((void)0)
#define Task_StartMenu_WaitApp(...) ((void)0)
#define Task_StartMenu_WaitSaveAppOpen(...) ((void)0)
#define Task_StartMenu_WaitSaveAppClose(...) ((void)0)
#define Task_StartMenu_Evolution(...) ((void)0)
#define Task_StartMenu_WaitEvolution(...) ((void)0)
#define FieldSystem_IsOverworldRestored(...) (TRUE)
#define FieldMap_FadeScreen(...) ((void)0)
#define StartMenu_ResumeUnionRoomSearch(...) ((void)0)
#define Heap_Free(...) ((void)0)
#define TaskManager_Jump(...) ((void)0)
#define ScheduleBgTilemapBufferTransfer(...) ((void)0)
#define Task_StartMenu_State19_Advance(...) ((void)0)
#define Task_StartMenu_State20_Close(...) ((void)0)
#define StartMenu_State19_Advance(...) ((void)0)
#define StartMenu_State20_Close(...) ((void)0)
#define GF_BG_LYR_MAIN_3 3
static void Task_StartMenu_DrawCursor(TaskManager *t) { assert(!t->env->panelActive); t->env->panelActive=TRUE; drawn++; }
static void StartMenu_RemoveCursorAndIcons(StartMenuTaskData *m, FieldSystem *f) { if(m->panelActive) { destroyed++; m->panelActive=FALSE; } }
static BOOL Task_StartMenu_HandleInput(TaskManager *);
static BOOL StartMenu_HandleListInput(TaskManager *, FieldSystem *, StartMenuTaskData *);
static void FieldSystem_SwitchBottomScreenApp(FieldSystem *,int,void *);
static void Reset(int app, int phase) {
    memset(&manager,0,sizeof(manager)); memset(&fieldSystem,0,sizeof(fieldSystem));
    memset(&startMenu,0,sizeof(startMenu));
    bottomTask.data=&manager;fieldSystem.bottomScreenTask=&bottomTask;
    manager.appId=app;manager.state=phase;manager.fieldSystem=&fieldSystem;
    taskManager.fieldSystem=&fieldSystem;taskManager.env=&startMenu;
    startMenu.state=START_MENU_STATE_HANDLE_INPUT;startMenu.panelActive=TRUE;
    actions=frames=initialized=exited=drawn=destroyed=0;gSystem.newKeys=0;
}
'''
        # The real manager reads bgConfig only at its graphics SDK boundary.
        declarations = declarations.replace('SysTask *bottomScreenTask; int startMenuCursorPos;',
                                            'SysTask *bottomScreenTask; int startMenuCursorPos; void *bgConfig; void *mapObjectManager; int startMenuState;')
        declarations = declarations.replace('/* ENUMS */', apps + '\n' + states + '\n' + menu_states)
        actual = '\n'.join((
            function_source('src/start_menu.c', 'Task_StartMenu'),
            function_source('src/start_menu.c', 'Task_StartMenu_HandleInput'),
            function_source('src/start_menu.c', 'StartMenu_HandleListInput'),
            function_source('src/field/bottom_screen_app.c', 'FieldSystem_SwitchBottomScreenApp'),
            function_source('src/field/bottom_screen_app.c', 'Task_BottomScreenApps'),
        ))
        self.compile_run(declarations + actual + '\nint main(void) {\n(void)Task_StartMenu; (void)Task_BottomScreenApps; (void)FieldSystem_SwitchBottomScreenApp;\n' + checks + '\nreturn 0;\n}', '-DSINGLE_SCREEN=1')

    def test_back_and_x_close_even_while_bottom_app_is_busy(self):
        self.run_case(r'''
for (int app=0;app<9;app++) for (int phase=0;phase<8;phase++) {
    int keys[]={PAD_BUTTON_B,PAD_BUTTON_X};
    for (int i=0;i<2;i++) {
        Reset(app,phase);gSystem.newKeys=keys[i];
        Task_StartMenu_HandleInput(&taskManager);
        assert(startMenu.state==START_MENU_STATE_CLOSE);
        assert(actions==0 && manager.state==phase && manager.appId==app);
    }
}
''')

    def test_retries_return_to_menu_after_switch_request_was_ignored(self):
        self.run_case(r'''
Reset(3,BOTTOM_SCREEN_APP_STATE_FADE_IN);
startMenu.state=START_MENU_STATE_INIT;startMenu.panelActive=FALSE;
/* Real menu initialization requests app0 while the preceding fade is busy. */
Task_StartMenu(&taskManager);
assert(manager.state==BOTTOM_SCREEN_APP_STATE_FADE_IN && manager.appId==3);
Task_BottomScreenApps(&bottomTask,&manager);
assert(manager.state==BOTTOM_SCREEN_APP_STATE_RUNNING && manager.appId==3);
Task_StartMenu(&taskManager);
assert(startMenu.state==START_MENU_STATE_HANDLE_INPUT && !startMenu.panelActive);
Task_StartMenu(&taskManager);
assert(manager.state==BOTTOM_SCREEN_APP_STATE_SWITCH_REQUESTED && manager.nextAppId==0);
assert(startMenu.state==START_MENU_STATE_2);
/* Resume the real menu initialization handshake, including creating its panel.
 * No action may execute against another app or during the return fade. */
for(int i=0;i<12 && (manager.appId!=0 || manager.state!=BOTTOM_SCREEN_APP_STATE_RUNNING || startMenu.state!=START_MENU_STATE_HANDLE_INPUT);i++) {
    Task_StartMenu(&taskManager);assert(actions==0);
    Task_BottomScreenApps(&bottomTask,&manager);
}
assert(manager.appId==0 && manager.state==BOTTOM_SCREEN_APP_STATE_RUNNING);
assert(startMenu.panelActive && drawn==1);
gSystem.newKeys=PAD_BUTTON_A;Task_StartMenu(&taskManager);
assert(actions==1 && initialized==1 && exited==1);
''')

    def test_recovery_releases_an_existing_panel_before_recreating_it(self):
        self.run_case(r'''
Reset(4,BOTTOM_SCREEN_APP_STATE_FADE_OUT);
manager.nextAppId=3;startMenu.state=START_MENU_STATE_INIT;startMenu.panelActive=FALSE;
Task_StartMenu(&taskManager);
for(int i=0;i<24 && (manager.appId!=0 || manager.state!=BOTTOM_SCREEN_APP_STATE_RUNNING || startMenu.state!=START_MENU_STATE_HANDLE_INPUT);i++) {
    Task_StartMenu(&taskManager);assert(actions==0);
    Task_BottomScreenApps(&bottomTask,&manager);
}
assert(manager.appId==0 && manager.state==BOTTOM_SCREEN_APP_STATE_RUNNING);
assert(startMenu.state==START_MENU_STATE_HANDLE_INPUT && startMenu.panelActive);
assert(drawn==2 && destroyed==1);
gSystem.newKeys=PAD_BUTTON_A;Task_StartMenu(&taskManager);assert(actions==1);
gSystem.newKeys=PAD_BUTTON_B;Task_StartMenu(&taskManager);
assert(startMenu.state==START_MENU_STATE_CLOSE);
gSystem.newKeys=0;assert(Task_StartMenu(&taskManager)==TRUE);
assert(!startMenu.panelActive && drawn==destroyed);
''')

    def test_ready_app_keeps_normal_navigation_and_actions(self):
        self.run_case(r'''
Reset(0,BOTTOM_SCREEN_APP_STATE_RUNNING);
startMenu.panelCursor=2;startMenu.slotValue[2]=5;
Task_StartMenu_HandleInput(&taskManager);
assert(fieldSystem.startMenuCursorPos==5 && actions==0);
gSystem.newKeys=PAD_BUTTON_A;Task_StartMenu_HandleInput(&taskManager);
assert(actions==1 && manager.state==BOTTOM_SCREEN_APP_STATE_RUNNING);
''')


if __name__ == '__main__':
    unittest.main()
