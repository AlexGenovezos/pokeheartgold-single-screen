"""Host state/input transactions for the real Options handlers.

Rendering edges are stubs. Actual BG/sprite composition and localized text
fit remain an explicit later runtime gate, not a claim made by this fixture.
"""
import re
import hashlib
import json
import unittest
import xml.etree.ElementTree as ET

from test_level_cap_save import ROOT, HOST_TYPES, function_source, host_run, without_includes


OPTIONS_EDGES = r'''
#ifndef QOL_INSTANT_TEXT
#define QOL_INSTANT_TEXT 1
#endif
typedef int s16;
typedef signed char s8;
typedef void String;
typedef void MessageFormat;
typedef struct Window {
    unsigned bg, x, y, width, height, palette, base;
    u8 pixels[240 * 144];
} Window;
typedef struct { unsigned value, numStrings; } OptionsApp_MenuEntry;
enum { MENU_ENTRY_TEXT_SPEED, MENU_ENTRY_BATTLE_SCENE, MENU_ENTRY_BATTLE_STYLE,
    MENU_ENTRY_SOUND_METHOD, MENU_ENTRY_BUTTON_MODE, MENU_ENTRY_FRAME, MENU_ENTRY_6, MENU_ENTRY_COUNT };
enum { PAD_KEY_RIGHT=1, PAD_KEY_LEFT=2, PAD_KEY_UP=4, PAD_KEY_DOWN=8,
    PAD_BUTTON_A=16, PAD_BUTTON_B=32, PAD_BUTTON_X=64,
    MENU_INPUT_STATE_BUTTONS=0, MENU_INPUT_STATE_TOUCH=1,
    SEQ_SE_DP_SELECT=1, SEQ_SE_DP_SAVE, SEQ_SE_GS_GEARCANCEL,
    GF_BG_LYR_MAIN_0=0, GF_BG_LYR_MAIN_1, GF_BG_LYR_MAIN_2, GF_BG_LYR_SUB_1=5,
    GF_PAL_LOCATION_MAIN_BG=0, GF_PAL_LOCATION_SUB_BG, GF_PAL_SLOT_13_OFFSET=416, GF_PAL_SLOT_12_OFFSET=384,
    GF_PLANE_TOGGLE_OFF=0, GF_PLANE_TOGGLE_ON=1, BG_POS_OP_SET_Y=0 };
typedef struct { u32 textSpeed, battleScene, battleStyle, soundMethod, buttonMode, frame; } Options;
typedef struct { BOOL enabled; } SaveData;
typedef struct { unsigned top, bottom, left, right; } Rect;
typedef struct { Rect rect; } TouchscreenHitbox;
#define TOUCHSCREEN_RECTLIST_END {255,255,255,255}
typedef struct OptionsApp_Data {
    unsigned exitChoice, currentMenuEntryId, menuInputState;
    unsigned capPage, firstPageMenuEntry, capMenuEntry;
    BOOL pendingCap;
    void *bgConfig, *menuInputPtr, *sprites[9];
    unsigned heapID;
    String *frameNumText, *capFormatTemplate, *capFormatResult;
    MessageFormat *capMessageFormat;
    void *msgData;
    struct { Window optionsTitle, selectedOption, frameAndTextSpeedTest, quitButton, confirmButton, pageHint; } windows;
    Options options, *playerOptions, *playerOptionsUnused;
    OptionsApp_MenuEntry menuEntries[MENU_ENTRY_COUNT];
} OptionsApp_Data;
typedef struct { OptionsApp_Data *data; } OverlayManager;
static struct { u32 newKeys, touchNew, touchX, touchY; } gSystem;
static SaveData saved;
static unsigned settingReads, settingWrites, originalWrites, draws, pageHints, legacyUpdates;
static unsigned spriteDraw[9], bgVisibility[3];
static unsigned spriteSequence[9];
static unsigned windowCount, paletteLoads;
static unsigned stringsAllocated, stringsDeleted, formatsAllocated, formatsDeleted;
static const int sMenuEntryBorderYCoords[7] = {-8,-32,-56,-80,-104,-128,-156};
SaveData *SaveData_Get(void) { return &saved; }
BOOL Qol_LevelCapEnabledForSave(SaveData *save) { settingReads++; return save->enabled; }
void Qol_LevelCapSetEnabledForSave(SaveData *save, BOOL enabled) { settingWrites++; save->enabled = enabled; }
void PlaySE(unsigned sound) {}
void MenuInputStateMgr_SetState(void *mgr, unsigned state) {}
void Sprite_SetAnimCtrlSeq(void *sprite, unsigned sequence) { spriteSequence[(uintptr_t)sprite] = sequence; }
void Sprite_SetDrawFlag(void *sprite, BOOL draw) { spriteDraw[(uintptr_t)sprite] = draw; }
void ToggleBgLayer(unsigned layer, unsigned visibility) { bgVisibility[layer] = visibility; }
void BgSetPosTextAndCommit(void *bg, unsigned layer, unsigned operation, int y) {}
void OptionsApp_SetActiveButtonsXPosition(OptionsApp_Data *data) {}
void OptionsApp_UpdateSelectionHighlight(OptionsApp_Data *data, u32 row) {}
void OptionsApp_HideBorderOnConfirmRow(OptionsApp_Data *data) {}
void OptionsApp_SetupInterfaceText(OptionsApp_Data *data) { draws++; }
void OptionsApp_DrawCapPage(OptionsApp_Data *data) { draws++; }
void OptionsApp_DrawPageHint(OptionsApp_Data *data) { pageHints++; }
void OptionsApp_UpdateMenuEntry(OptionsApp_Data *data, unsigned row) { legacyUpdates++; }
void OptionsApp_UpdateMenuEntryCarousel(OptionsApp_Data *data, unsigned row, OptionsApp_MenuEntry *entry, int delta) {
    entry->value = (entry->value + entry->numStrings + delta) % entry->numStrings;
}
int TouchscreenHitbox_FindRectAtTouchNew(const TouchscreenHitbox *boxes) {
    for (unsigned i = 0; boxes[i].rect.top != 255; i++) {
        Rect r = boxes[i].rect;
        if (gSystem.touchNew && gSystem.touchX >= r.left && gSystem.touchX < r.right
            && gSystem.touchY >= r.top && gSystem.touchY < r.bottom) return i;
    }
    return -1;
}
BOOL TouchscreenHitbox_PointIsInRect(const TouchscreenHitbox *box, u32 x, u32 y) {
    return x >= box->rect.left && x < box->rect.right && y >= box->rect.top && y < box->rect.bottom;
}
OptionsApp_Data *OverlayManager_GetData(OverlayManager *manager) { return manager->data; }
#define OPTION_SETTER(name, field) void Options_Set##name(Options *o, unsigned value) { originalWrites++; o->field = value; }
OPTION_SETTER(TextSpeed, textSpeed)
OPTION_SETTER(BattleScene, battleScene)
OPTION_SETTER(BattleStyle, battleStyle)
OPTION_SETTER(SoundMethod, soundMethod)
OPTION_SETTER(ButtonMode, buttonMode)
OPTION_SETTER(Frame, frame)
void GF_SndSetMonoFlag(unsigned mode) {}
void Options_SetButtonModeOnMain(void *unused, unsigned mode) {}
void String_Delete(String *string) { stringsDeleted++; }
void MessageFormat_Delete(MessageFormat *format) { formatsDeleted++; }
void TextFlags_SetCanABSpeedUpPrint(BOOL enabled) {}
void TextFlags_SetCanTouchSpeedUpPrint(BOOL enabled) {}
void OverlayManager_FreeData(OverlayManager *manager) {}
void Heap_Destroy(unsigned heap) {}
#define GX_RGB(r,g,b) ((r) | ((g)<<5) | ((b)<<10))
void AddWindowParameterized(void *bg, Window *window, unsigned layer, unsigned x, unsigned y,
        unsigned width, unsigned height, unsigned palette, unsigned base) {
    window->bg=layer; window->x=x; window->y=y; window->width=width; window->height=height;
    window->palette=palette; window->base=base; windowCount++;
}
void LoadUserFrameGfx2(void *bg, unsigned layer, unsigned base, unsigned palette, unsigned frame, unsigned heap) {}
void LoadFontPal0(unsigned location, unsigned offset, unsigned heap) {}
void LoadFontPal1(unsigned location, unsigned offset, unsigned heap) {}
void BG_LoadPlttData(unsigned bg, const u16 *data, unsigned size, unsigned offset) {
    assert(bg == GF_BG_LYR_MAIN_1 && size == 6 && offset == (13*16+3)*2); paletteLoads++;
}
void FillWindowPixelBuffer(Window *window, unsigned color) { memset(window->pixels, color, sizeof(window->pixels)); }
void ClearWindowTilemap(Window *window) {}
void DrawFrameAndWindow2(Window *window, BOOL transfer, unsigned base, unsigned palette) {}
static OptionsApp_Data data;
static Options originalOptions;
static OverlayManager manager = {&data};
static void init(void) {
    memset(&data, 0, sizeof(data)); memset(&gSystem, 0, sizeof(gSystem));
    memset(&originalOptions, 0, sizeof(originalOptions));
    memset(spriteDraw, 0, sizeof(spriteDraw)); memset(bgVisibility, 0, sizeof(bgVisibility));
    memset(spriteSequence, 0, sizeof(spriteSequence));
    saved.enabled = FALSE; data.playerOptions = &originalOptions;
    for (unsigned i = 0; i < 7; i++) data.menuEntries[i].numStrings = 2;
    data.menuEntries[0].numStrings = 4; data.menuEntries[5].numStrings = 20;
    for (unsigned i = 0; i < 9; i++) data.sprites[i] = (void *)(uintptr_t)i;
    settingReads = settingWrites = originalWrites = draws = pageHints = legacyUpdates = windowCount = paletteLoads = 0;
    stringsAllocated = stringsDeleted = formatsAllocated = formatsDeleted = 0;
}
'''

LIFECYCLE_EDGES = r'''
typedef struct { Options *options; void *menuInputStateMgr; } OptionsApp_Args;
static OptionsApp_Args args;
enum { HEAP_ID_3, HEAP_ID_OPTIONS_APP, PM_LCD_TOP, PM_LCD_BOTTOM, RGB_BLACK };
void Heap_Create(unsigned parent, unsigned heap, unsigned size) {}
OptionsApp_Args *OverlayManager_GetArgs(OverlayManager *manager) { return &args; }
OptionsApp_Data *OverlayManager_CreateAndGetData(OverlayManager *manager, unsigned size, unsigned heap) { return manager->data; }
#define OPTION_GETTER(name, field) unsigned Options_Get##name(Options *o) { return o->field; }
OPTION_GETTER(TextSpeed, textSpeed)
OPTION_GETTER(BattleScene, battleScene)
OPTION_GETTER(BattleStyle, battleStyle)
OPTION_GETTER(SoundMethod, soundMethod)
OPTION_GETTER(ButtonMode, buttonMode)
OPTION_GETTER(Frame, frame)
unsigned MenuInputStateMgr_GetState(void *manager) { return 0; }
String *String_New(unsigned size, unsigned heap) { static u32 slots[8]; return &slots[stringsAllocated++]; }
MessageFormat *MessageFormat_New(unsigned heap) { static int format; formatsAllocated++; return &format; }
void SetMasterBrightnessByColor(unsigned lcd, unsigned color) {}
'''

RENDER_EDGES = r'''
enum { TEXT_SPEED_INSTANT=0, TEXT_SPEED_NOTRANSFER=255, PRINTING_MODE_LEFT_ALIGN=0 };
#define MAKE_TEXT_COLOR(fg,shadow,bg) ((fg) | ((shadow)<<8) | ((bg)<<16))
static QolLevelCap prospective = {TRAINER_LEADER_FALKNER_FALKNER, 13};
static unsigned capResolutions, trainerBuffers, lastTrainer, levelBuffers, lastLevel, expansions;
static unsigned printed[70], printedX[70], printedY[70];
QolLevelCap Qol_LevelCapForSave(SaveData *save) { capResolutions++; return prospective; }
void ReadMsgDataIntoString(void *data, unsigned id, String *string) { assert(id < 70); *(u32 *)string = id; }
void AddTextPrinterParameterizedWithColor(Window *window, unsigned font, String *string,
        unsigned x, unsigned y, unsigned speed, unsigned color, void *callback) {
    unsigned id = *(u32 *)string; assert(id < 70); printed[id]++; printedX[id] = x; printedY[id] = y;
}
void CopyWindowToVram(Window *window) {}
void FillWindowPixelRect(Window *window, unsigned color, unsigned x, unsigned y, unsigned width, unsigned height) {
    assert(x+width <= 240 && y+height <= 144);
    for (unsigned row=y;row<y+height;row++) for (unsigned col=x;col<x+width;col++) window->pixels[row*240+col] = color;
}
void BufferTrainerName(MessageFormat *format, unsigned index, unsigned trainer) {
    assert(index == 0 && trainer != TRAINER_NONE); trainerBuffers++; lastTrainer = trainer;
}
void BufferIntegerAsString(MessageFormat *format, unsigned index, unsigned level, unsigned width, unsigned mode, BOOL sign) {
    assert(index == 1 && width == 3 && mode == PRINTING_MODE_LEFT_ALIGN); levelBuffers++; lastLevel = level;
}
void StringExpandPlaceholders(MessageFormat *format, String *dest, String *source) { expansions++; *(u32 *)dest = *(u32 *)source; }
'''


def handlers():
    source = (ROOT / 'src/options_app.c').read_text()
    names = ['sOptionsAppTouchscreenHitboxes', 'sOptionsAppHitboxEntryValues']
    names += [name for name in ('sLevelCapPageHintHitboxes', 'sLevelCapTouchscreenHitboxes') if name in source]
    arrays = '\n'.join(re.search(
        r'static const [^\n]*\b' + name + r'\[.*?\n\};', source, re.S)[0]
        for name in names)
    # Graphics stub signatures use static to match existing overlay linkage.
    edges = re.sub(r'^void (OptionsApp_\w+)\(', r'static void \1(', OPTIONS_EDGES, flags=re.M)
    helpers = ''
    for name in ('OptionsApp_SwitchPage', 'OptionsApp_HandleCapTouch'):
        if re.search(r'^[\w *]+\b' + name + r'\([^;{}]*\)\s*\{', source, re.M):
            helpers += function_source('src/options_app.c', name) + '\n'
    actual = '\n'.join(function_source('src/options_app.c', name) for name in
                       ('OptionsApp_HandleKeyInput', 'OptionsApp_HandleInput', 'OptionsMenu_Exit'))
    return HOST_TYPES + edges + arrays + helpers + actual


class LevelCapOptionsTests(unittest.TestCase):
    def run_checks(self, checks, enabled=1, instant=1):
        host_run(self, handlers() + '\nint main(void) {\n' + checks + '\nreturn 0;}',
                 enabled, (f'-DQOL_INSTANT_TEXT={instant}',))

    def test_x_reaches_cap_page_and_preserves_pending_across_page_flips(self):
        self.run_checks(r'''
init(); data.currentMenuEntryId = MENU_ENTRY_FRAME;
/* X remains available when L=A has remapped shoulder keys. */
gSystem.newKeys = PAD_BUTTON_X; OptionsApp_HandleInput(&data);
assert(data.capPage == 1 && data.currentMenuEntryId == 0 && data.firstPageMenuEntry == MENU_ENTRY_FRAME);
assert(data.exitChoice == 0 && settingWrites == 0 && legacyUpdates == 0);
gSystem.newKeys = PAD_KEY_RIGHT; OptionsApp_HandleInput(&data);
assert(data.pendingCap && data.menuEntries[0].value == 0);
gSystem.newKeys = PAD_BUTTON_X; OptionsApp_HandleInput(&data);
assert(data.capPage == 0 && data.currentMenuEntryId == MENU_ENTRY_FRAME && data.pendingCap);
OptionsApp_HandleInput(&data); assert(data.capPage == 1 && data.pendingCap);
''')

    def test_cap_navigation_has_only_toggle_and_exit_rows_and_b_cancels(self):
        self.run_checks(r'''
init(); data.capPage = 1;
gSystem.newKeys = PAD_KEY_UP; OptionsApp_HandleInput(&data);
assert(data.currentMenuEntryId == MENU_ENTRY_6);
gSystem.newKeys = PAD_KEY_DOWN; OptionsApp_HandleInput(&data);
assert(data.currentMenuEntryId == 0);
gSystem.newKeys = PAD_BUTTON_A; OptionsApp_HandleInput(&data);
assert(data.pendingCap && data.exitChoice == 0);
gSystem.newKeys = PAD_BUTTON_B; OptionsApp_HandleInput(&data);
assert(data.exitChoice == 2);
OptionsMenu_Exit(&manager, NULL);
assert(!saved.enabled && settingWrites == 0);
''')

    def test_cap_touch_and_header_never_change_original_values(self):
        self.run_checks(r'''
init(); gSystem.touchNew = 1; gSystem.touchX = 200; gSystem.touchY = 10;
OptionsApp_HandleInput(&data); assert(data.capPage == 1 && legacyUpdates == 0);
gSystem.touchX = 200; gSystem.touchY = 35;
OptionsApp_HandleInput(&data); assert(data.pendingCap && data.menuEntries[0].value == 0);
gSystem.touchX = 140; OptionsApp_HandleInput(&data); assert(!data.pendingCap);
gSystem.touchX = 210; gSystem.touchY = 155; OptionsApp_HandleInput(&data);
assert(data.menuEntries[5].value == 0 && data.exitChoice == 0 && legacyUpdates == 0);
''')

    def test_confirm_commits_pending_once_and_quit_cancel_preserves_config(self):
        for page in (0, 1):
            with self.subTest(page=page):
                self.run_checks(f'''
init(); data.capPage = {page}; data.pendingCap = TRUE; data.exitChoice = 1;
OptionsMenu_Exit(&manager, NULL);
assert(saved.enabled && settingWrites == 1 && originalWrites == 6);
init(); saved.enabled = TRUE; data.capPage = {page}; data.pendingCap = FALSE; data.exitChoice = 2;
OptionsMenu_Exit(&manager, NULL); assert(saved.enabled && settingWrites == 0);
''')

    def test_disabled_support_keeps_original_handlers_and_never_accesses_cap_setting(self):
        self.run_checks(r'''
init(); gSystem.newKeys = PAD_BUTTON_X; OptionsApp_HandleInput(&data);
assert(data.capPage == 0 && settingWrites == 0 && settingReads == 0);
gSystem.newKeys = PAD_KEY_DOWN; OptionsApp_HandleInput(&data);
assert(data.currentMenuEntryId == 1);
data.pendingCap = TRUE; data.exitChoice = 1; OptionsMenu_Exit(&manager, NULL);
assert(!saved.enabled && settingWrites == 0 && settingReads == 0 && originalWrites == 6);
''', enabled=0)

    def test_cap_only_build_can_navigate_without_instant_text(self):
        self.run_checks(r'''
init(); gSystem.newKeys = PAD_BUTTON_X; OptionsApp_HandleInput(&data);
assert(data.capPage == 1);
gSystem.newKeys = PAD_KEY_RIGHT; OptionsApp_HandleInput(&data); assert(data.pendingCap);
''', instant=0)

    def test_localized_rows_append_without_renumbering_existing_messages(self):
        body = ET.parse(ROOT / 'files/msgdata/msg/msg_0045.gmm').getroot()
        rows = body.findall('.//row')
        actual = {int(row.attrib['index']): row for row in rows}
        self.assertEqual(sorted(actual), list(range(70)))
        labels = ['LEVEL CAPS', 'LEVEL CAP', 'OFF', 'ON', 'NEXT BOSS', 'NO CAP',
                  'CONFIRM TO APPLY', 'X: CAPS', 'X: OPTIONS',
                  '{STRVAR_1 0, 0, 0}  Lv. {STRVAR_1 52, 1, 0}']
        for index, text in enumerate(labels, 60):
            self.assertEqual(actual[index].attrib['id'], f'msg_0045_{index:05}')
            self.assertEqual(actual[index].find("language[@name='English']").text, text)
        legacy = [(i, actual[i].attrib['id'], actual[i].find("language[@name='English']").text)
                  for i in range(60)]
        self.assertEqual(hashlib.sha256(json.dumps(legacy).encode()).hexdigest(), LEGACY_MESSAGE_HASH)

    def test_window_tiles_and_cap_only_palette_are_valid_for_support_matrix(self):
        setup = function_source('src/options_app.c', 'OptionsApp_SetupWindows')
        for enabled in (0, 1):
            for instant in (0, 1):
                with self.subTest(enabled=enabled, instant=instant):
                    host_run(self, HOST_TYPES + OPTIONS_EDGES + setup + r'''
int main(void) {
    init(); OptionsApp_SetupWindows(&data);
    assert(windowCount == 5 + QOL_LEVEL_CAPS);
    assert(paletteLoads == !!(QOL_INSTANT_TEXT || QOL_LEVEL_CAPS));
    Window *original[] = {&data.windows.optionsTitle, &data.windows.selectedOption,
        &data.windows.quitButton, &data.windows.confirmButton};
    const unsigned bases[] = {0xa,0x2e,0x24a,0x25f};
    for (unsigned i = 0; i < 4; i++) {
        assert(original[i]->base == bases[i]);
        assert(original[i]->base + original[i]->width*original[i]->height <= 0x274);
        if(i<3) assert(original[i]->base + original[i]->width*original[i]->height == bases[i+1]);
    }
#if QOL_LEVEL_CAPS
    Window *hint=&data.windows.pageHint;
    assert(hint->bg == GF_BG_LYR_MAIN_1 && hint->x == 14 && hint->y == 0);
    assert(hint->width == 17 && hint->height == 3 && hint->palette == 13 && hint->base == 0x274);
    assert(hint->base + hint->width*hint->height == 0x2a7 && 0x2a7 <= 1024);
#endif
    return 0;
}
''', enabled, (f'-DQOL_INSTANT_TEXT={instant}',))

    def test_open_preview_and_exit_allocate_once_and_commit_only_confirmation(self):
        actual = function_source('src/options_app.c', 'OptionsMenu_Init')
        for enabled in (0, 1):
            with self.subTest(enabled=enabled):
                host_run(self, handlers() + LIFECYCLE_EDGES + actual + r'''
int main(void) {
    init(); saved.enabled = TRUE; args.options = &originalOptions;
    assert(OptionsMenu_Init(&manager, NULL));
    assert(settingWrites == 0 && settingReads == QOL_LEVEL_CAPS);
    assert(stringsAllocated == 1 + 2*QOL_LEVEL_CAPS && formatsAllocated == QOL_LEVEL_CAPS);
    assert(!data.capPage && data.firstPageMenuEntry == 0 && data.capMenuEntry == 0);
#if QOL_LEVEL_CAPS
    assert(data.pendingCap);
    gSystem.newKeys = PAD_BUTTON_X; OptionsApp_HandleInput(&data);
    gSystem.newKeys = PAD_KEY_LEFT; OptionsApp_HandleInput(&data);
    assert(!data.pendingCap && settingWrites == 0 && saved.enabled);
#endif
    data.exitChoice = 2; OptionsMenu_Exit(&manager, NULL);
    assert(settingWrites == 0 && saved.enabled);
    assert(stringsDeleted == stringsAllocated && formatsDeleted == formatsAllocated);
    return 0;
}
''', enabled)

    def test_renderer_uses_prospective_localized_boss_and_never_formats_trainer_zero(self):
        declarations = without_includes((ROOT / 'include/qol_level_caps.h').read_text())
        source = (ROOT / 'src/options_app.c').read_text()
        program = handlers()
        for name in ('OptionsApp_DrawCapPage', 'OptionsApp_DrawPageHint'):
            stub = re.search(r'static void ' + name + r'\([^\n]*\) \{[^\n]*\}\n', program)
            self.assertIsNotNone(stub)
            program = program.replace(stub[0], f'static void {name}(OptionsApp_Data *data);\n', 1)
        messages = ''.join(f'#define {row.attrib["id"]} {row.attrib["index"]}\n'
                           for row in ET.fromstring((ROOT / 'files/msgdata/msg/msg_0045.gmm').read_text()).findall('row'))
        actual = '\n'.join(function_source('src/options_app.c', name)
                           for name in ('OptionsApp_DrawCapPage', 'OptionsApp_DrawPageHint'))
        host_run(self, program + '\n' + declarations + messages + RENDER_EDGES + actual + r'''
int main(void) {
    init(); u32 template=0, result=0; data.capFormatTemplate=&template; data.capFormatResult=&result;
    data.pendingCap = FALSE; data.capPage = 1;
    OptionsApp_DrawCapPage(&data); OptionsApp_DrawPageHint(&data);
    assert(capResolutions == 1 && trainerBuffers == 1 && lastTrainer == TRAINER_LEADER_FALKNER_FALKNER);
    assert(levelBuffers == 1 && lastLevel == 13 && expansions == 1 && settingWrites == 0);
    for (unsigned id=60;id<=64;id++) assert(printed[id] == 1);
    assert(printed[66] == 1 && printed[68] == 1 && printed[69] == 1 && printed[65] == 0);
    assert(printedX[62] == 120 && printedX[63] == 176 && printedY[69] == 61);
    assert(data.windows.selectedOption.pixels[10*240+118] == 15);
    assert(data.windows.selectedOption.pixels[10*240+174] == 3);
    prospective.trainerId = TRAINER_NONE; prospective.level = MAX_LEVEL;
    data.pendingCap = TRUE; OptionsApp_DrawCapPage(&data);
    assert(capResolutions == 2 && trainerBuffers == 1 && expansions == 1 && printed[65] == 1);
    assert(data.windows.selectedOption.pixels[10*240+118] == 3);
    assert(data.windows.selectedOption.pixels[10*240+174] == 15);
    data.capPage = 0; OptionsApp_DrawPageHint(&data); assert(printed[67] == 1);
    return 0;
}
''')

    def test_page_switch_restores_layers_and_original_sprite_rules_and_actual_confirm_input(self):
        program = handlers()
        for name in ('OptionsApp_UpdateSelectionHighlight', 'OptionsApp_HideBorderOnConfirmRow'):
            stub = re.search(r'static void ' + name + r'\([^\n]*\) \{[^\n]*\}\n', program)
            self.assertIsNotNone(stub)
            actual = function_source('src/options_app.c', name)
            program = program.replace(stub[0], 'static void OptionsApp_DrawCapPage(OptionsApp_Data *data);\n' + actual + '\n', 1)
        host_run(self, program + r'''
int main(void) {
    init(); data.currentMenuEntryId=MENU_ENTRY_FRAME; spriteDraw[7]=spriteDraw[8]=1;
    bgVisibility[0]=bgVisibility[2]=1;
    gSystem.newKeys=PAD_BUTTON_X; OptionsApp_HandleInput(&data);
    assert(!bgVisibility[0] && !bgVisibility[2] && spriteDraw[7] && spriteDraw[8]);
    for(unsigned i=0;i<7;i++) assert(!spriteDraw[i]);
    OptionsApp_HandleInput(&data); /* Return to frame row without recreation. */
    assert(bgVisibility[0] && bgVisibility[2] && data.currentMenuEntryId==MENU_ENTRY_FRAME);
    for(unsigned i=1;i<7;i++) assert(spriteDraw[i]);
    assert(spriteDraw[0]==!QOL_INSTANT_TEXT);
    OptionsApp_HandleInput(&data); data.pendingCap=TRUE;
    gSystem.newKeys=PAD_KEY_DOWN; OptionsApp_HandleInput(&data);
    assert(data.currentMenuEntryId==MENU_ENTRY_6 && spriteSequence[7]==1 && spriteSequence[8]==0);
    gSystem.newKeys=PAD_KEY_LEFT; OptionsApp_HandleInput(&data);
    assert(spriteSequence[7]==0 && spriteSequence[8]==1);
    gSystem.newKeys=PAD_BUTTON_A; OptionsApp_HandleInput(&data);
    assert(data.exitChoice==1 && spriteSequence[8]==3 && settingWrites==0);
    OptionsMenu_Exit(&manager,NULL); assert(saved.enabled && settingWrites==1);
    init(); data.capPage=1; data.pendingCap=TRUE; gSystem.touchNew=1;
    gSystem.touchX=220; gSystem.touchY=180; OptionsApp_HandleInput(&data);
    assert(data.exitChoice==2 && spriteSequence[7]==3 && data.menuInputState==1);
    OptionsMenu_Exit(&manager,NULL); assert(!saved.enabled && settingWrites==0);
    return 0;
}
''')


LEGACY_MESSAGE_HASH = '9d553c55082f75d8ed80a43e5f1c96800fcde8a9fa97920ebc10f1089abcbdd8'


if __name__ == '__main__':
    unittest.main()
