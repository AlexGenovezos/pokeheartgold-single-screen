"""Host checks execute selected real game C functions with SDK edges stubbed."""
from pathlib import Path
import os
import re
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]


def function_source(relative_path, name):
    text = (ROOT / relative_path).read_text()
    match = re.search(r"^[\w *]+\b" + re.escape(name) + r"\([^;{}]*\)\s*\{",
                      text, re.MULTILINE)
    if not match:
        raise AssertionError(f"function definition not found: {name}")
    start = match.start()
    pos = match.end()
    depth = 1
    while depth:
        depth += (text[pos] == "{") - (text[pos] == "}")
        pos += 1
    return text[start:pos]


class GameLogicTests(unittest.TestCase):
    def compile_run(self, source, *flags):
        # Extracted legacy battle fixtures now call the shared pure Wind
        # predicate. Link its actual production C only when the fixture does
        # not already include it (modern-move fixtures include the whole TU).
        # This preserves their existing SDK edges without a Python wind model.
        if ('Qol_WindMoveCanBeAbsorbed(' in source
                and not re.search(r'BOOL\s+Qol_WindMoveCanBeAbsorbed\([^;{}]*\)\s*\{', source)):
            source = ('#include "constants/qol_moves.h"\n'
                      'int Qol_IsWindMove(unsigned short);\n'
                      'int Qol_WindMoveCanBeAbsorbed(unsigned short);\n' + source + '\n'
                      + function_source('src/qol_moves.c', 'Qol_IsWindMove') + '\n'
                      + function_source('src/qol_moves.c', 'Qol_WindMoveCanBeAbsorbed') + '\n')
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "check.c").write_text(source)
            compile_result = subprocess.run(
                [os.environ.get("CC", "cc"), "-std=c99", "-Wall", "-Wextra",
                 "-Werror", "-Wno-unused-parameter", "-Wno-switch", "-iquote", str(ROOT / "include"),
                 *flags, str(root / "check.c"), "-o", str(root / "check")],
                capture_output=True, text=True)
            self.assertEqual(compile_result.returncode, 0, compile_result.stderr)
            result = subprocess.run([str(root / "check")], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)

    def test_successful_teaching_preserves_tms_and_other_effects(self):
        declarations = r"""
#include <assert.h>
#include <stddef.h>
#include "constants/items.h"
#include "constants/moves.h"
#include "constants/pokemon.h"
typedef struct { int slots[512]; int friendship; int mood; } Pokemon;
typedef struct { int quantity; } Bag;
typedef struct { int moveId; int itemId; Bag *bag; } Args;
typedef struct { Args *args; } PartyMenu;
enum { HEAP_ID_PARTY_MENU, MON_MOOD_MODIFIER_LEARN_TMHM };
void SetMonData(Pokemon *mon, int field, const int *value) { mon->slots[field] = *value; }
int GetMoveMaxPP(int move, int ups) { return 17 + ups; }
int MoveIsHM(int move) { return move == MOVE_SURF; }
void Bag_TakeItem(Bag *bag, int item, int count, int heap) { bag->quantity -= count; }
int PartyMenu_GetCurrentMapSec(PartyMenu *menu) { return 42; }
void MonApplyFriendshipMod(Pokemon *mon, int event, int map) { mon->friendship++; }
void ApplyMonMoodModifier(Pokemon *mon, int event) { mon->mood++; }
"""
        actual = function_source("src/party_menu_items.c", "PartyMenu_LearnMoveToSlot")
        checks = r"""
int main(void) {
    for (int item = ITEM_TM01; item <= ITEM_TM92; item++) {
        for (int slot = 0; slot < 4; slot++) {
            Pokemon mon = {0}; Bag bag = {1}; Args args = {MOVE_TACKLE, item, &bag};
            PartyMenu menu = {&args};
            PartyMenu_LearnMoveToSlot(&menu, &mon, slot);
#if QOL_REUSABLE_TMS
            assert(bag.quantity == 1);
#else
            assert(bag.quantity == 0);
#endif
            assert(mon.slots[MON_DATA_MOVE1 + slot] == MOVE_TACKLE);
            assert(mon.slots[MON_DATA_MOVE1_PP + slot] == 17);
            assert(mon.slots[MON_DATA_MOVE1_PP_UPS + slot] == 0);
            assert(mon.friendship == 1 && mon.mood == 1);
        }
    }
    // Preserve HM reusability and unrelated item behavior.
    int items[] = {ITEM_HM03, ITEM_POTION, ITEM_NONE};
    for (unsigned i = 0; i < sizeof(items)/sizeof(items[0]); i++) {
        Pokemon mon = {0}; Bag bag = {1};
        Args args = {i == 0 ? MOVE_SURF : MOVE_TACKLE, items[i], &bag};
        PartyMenu menu = {&args};
        PartyMenu_LearnMoveToSlot(&menu, &mon, 0);
        assert(bag.quantity == (items[i] == ITEM_POTION ? 0 : 1));
        assert(mon.friendship == (items[i] != ITEM_NONE));
    }
    // The same remaining TM can teach a second party member.
#if QOL_REUSABLE_TMS
    Pokemon first = {0}, second = {0}; Bag bag = {1};
    Args args = {MOVE_TACKLE, ITEM_TM01, &bag}; PartyMenu menu = {&args};
    PartyMenu_LearnMoveToSlot(&menu, &first, 0);
    PartyMenu_LearnMoveToSlot(&menu, &second, 2);
    assert(bag.quantity == 1);
    assert(first.slots[MON_DATA_MOVE1] == MOVE_TACKLE);
    assert(second.slots[MON_DATA_MOVE3] == MOVE_TACKLE);
#endif
    return 0;
}
"""
        for enabled in (0, 1):
            with self.subTest(enabled=enabled):
                self.compile_run(declarations + actual + checks,
                                 f"-DQOL_REUSABLE_TMS={enabled}")



    def test_saved_text_speeds_keep_existing_values_and_add_instant(self):
        header = (ROOT / "include/options.h").read_text()
        start = header.index("typedef struct Options {")
        end = header.index("} Options;", start) + len("} Options;")
        declarations = """
#include <assert.h>
typedef unsigned short u16;
typedef unsigned int u32;
typedef unsigned char u8;
#define TEXT_SPEED_INSTANT_ASYNC 254
#include "qol_config.h"
""" + header[start:end]
        actual = "\n".join(function_source("src/options.c", name) for name in
                           ("Options_GetTextSpeed", "Options_SetTextSpeed",
                            "Options_GetTextFrameDelay"))
        checks = """
int main(void) {
    Options options = {0};
    assert(sizeof(options) == 2);
    int expected[] = {8, 4, 1, QOL_INSTANT_TEXT ? 254 : 1};
    for (int speed = 0; speed < 4; speed++) {
        Options_SetTextSpeed(&options, speed);
        assert(Options_GetTextSpeed(&options) == (unsigned)speed);
        assert(Options_GetTextFrameDelay(&options) == expected[speed]);
    }
    return 0;
}
"""
        for enabled in (0, 1):
            with self.subTest(enabled=enabled):
                self.compile_run(declarations + actual + checks,
                                 f"-DQOL_INSTANT_TEXT={enabled}")

    def test_instant_dialog_remains_asynchronous_and_preserves_waits(self):
        declarations = r"""
#include <assert.h>
#include <stddef.h>
#include <stdlib.h>
#include <string.h>
#include "qol_config.h"
typedef unsigned char u8;
typedef unsigned int u32;
typedef int BOOL;
typedef void SysTask;
typedef void (*SysTaskFunc)(SysTask *, void *);
enum { TRUE = 1, HEAP_ID_DEFAULT = 0, MAX_TEXT_PRINTERS = 8,
       TEXT_SPEED_INSTANT = 0, TEXT_SPEED_INSTANT_ASYNC = 254, TEXT_SPEED_NOTRANSFER = 255 };
typedef enum { RENDER_PRINT, RENDER_FINISH, RENDER_REPEAT, RENDER_UPDATE } RenderResult;
typedef struct {
    union { void *wrapped; const void *raw; } currentChar;
    int fgColor, bgColor, shadowColor;
    void *window;
} TextPrinterTemplate;
typedef BOOL (*PrinterCallback_t)(TextPrinterTemplate *, unsigned short);
typedef struct {
    int active, state, delayCounter, scrollDistance, callbackResult, id, callbackParam;
    u8 textSpeedBottom : 7;
    u8 textSpeedTop : 1;
    int subStructFields[7];
    TextPrinterTemplate template;
    PrinterCallback_t callback;
} TextPrinter;
static int _021D1F6C;
static void *sFonts = (void *)1;
static TextPrinter *current;
static int tasks, freed, copied, rendered, callbackCount, callbackBlock;
static RenderResult events[16];
static int eventCount, eventIndex;
static void RunTextPrinter(SysTask *, TextPrinter *);
static void *Heap_Alloc(int heap, size_t size) { return current = calloc(1, size); }
static void Heap_Free(void *p) { free(p); }
static const void *String_cstr(void *string) { return string; }
static void TextPrinter_InitFocusIndicatorGfx(TextPrinter *p) {}
static void TextPrinter_FreeFocusIndicatorGfx(TextPrinter *p) {}
static int CreateTextPrinterSysTask(SysTaskFunc fn, TextPrinter *p, int priority) { tasks++; return 0; }
static void DestroyTextPrinterSysTask(int id) { freed++; }
static void GenerateFontHalfRowLookupTable(int fg, int bg, int shadow) {}
static void CopyWindowToVram(void *window) { copied++; }
static RenderResult RenderFont(TextPrinter *p) {
    assert(eventIndex < eventCount);
    assert(p->textSpeedBottom == 0 || p->textSpeedBottom == 3);
    RenderResult result = events[eventIndex++];
    if (result == RENDER_PRINT) rendered++;
    if (result == RENDER_UPDATE) { p->state = 2; p->callbackParam = 42; }
    else p->state = 0;
    return result;
}
static BOOL Callback(TextPrinterTemplate *p, unsigned short param) {
    callbackCount++;
    if (param == 42 && callbackBlock) return 1;
    return 0;
}
static void Reset(void) {
    if (current) free(current);
    current = NULL; tasks = freed = copied = rendered = callbackCount = 0;
    eventIndex = eventCount = callbackBlock = 0;
    memset(events, 0, sizeof(events));
}
"""
        header = (ROOT / "include/render_text.h").read_text()
        start = header.index("typedef struct TextPrinterSubStruct {")
        end = header.index("} TextPrinterSubStruct;") + len("} TextPrinterSubStruct;")
        declarations += header[start:end]
        actual = (function_source("src/text.c", "AddTextPrinter") + "\n" +
                  function_source("src/text.c", "RunTextPrinter"))
        checks = r"""
int main(void) {
    TextPrinterTemplate template = {0};
    // A full page finishes in one tick, while its task still has a valid ID.
    Reset();
    events[0] = events[1] = events[2] = RENDER_PRINT;
    events[3] = RENDER_FINISH; eventCount = 4;
    int id = AddTextPrinter(&template, TEXT_SPEED_INSTANT_ASYNC, Callback);
    assert(id == 0 && tasks == 1 && rendered == 0 && freed == 0);
    assert(current->textSpeedBottom == 0 && current->textSpeedTop == 1);
    assert(((TextPrinterSubStruct *)current->subStructFields)->isInstant);
    RunTextPrinter(NULL, current);
    assert(rendered == 3 && callbackCount == 3 && freed == 1 && copied >= 1);
    // A control-code wait returns to the scheduler and blocks further text.
    Reset();
    events[0] = RENDER_PRINT; events[1] = RENDER_UPDATE;
    events[2] = RENDER_PRINT; events[3] = RENDER_FINISH; eventCount = 4;
    callbackBlock = 1;
    AddTextPrinter(&template, TEXT_SPEED_INSTANT_ASYNC, Callback);
    RunTextPrinter(NULL, current);
    assert(eventIndex == 2 && rendered == 1 && freed == 0);
    RunTextPrinter(NULL, current);
    assert(eventIndex == 2 && rendered == 1);
    callbackBlock = 0;
    RunTextPrinter(NULL, current); // resolves callback, without rendering ahead
    assert(eventIndex == 2);
    RunTextPrinter(NULL, current);
    assert(rendered == 2 && freed == 1);
    // An explicit page wait yields even without a callback.
    Reset();
    events[0] = RENDER_PRINT; events[1] = RENDER_UPDATE;
    events[2] = RENDER_FINISH; eventCount = 3;
    AddTextPrinter(&template, TEXT_SPEED_INSTANT_ASYNC, NULL);
    RunTextPrinter(NULL, current);
    assert(eventIndex == 2 && rendered == 1 && freed == 0);
    // Ordinary text still renders one glyph per scheduler tick.
    Reset();
    events[0] = events[1] = RENDER_PRINT; eventCount = 2;
    AddTextPrinter(&template, 4, Callback);
    RunTextPrinter(NULL, current);
    assert(eventIndex == 1 && rendered == 1 && freed == 0);
    // Internal synchronous/no-transfer printing keeps its old lifecycle.
    Reset();
    events[0] = RENDER_PRINT; events[1] = RENDER_FINISH; eventCount = 2;
    assert(AddTextPrinter(&template, TEXT_SPEED_INSTANT, NULL) == MAX_TEXT_PRINTERS);
    current = NULL; // AddTextPrinter released its temporary printer.
    assert(tasks == 0 && copied == 1);
    Reset();
    events[0] = RENDER_FINISH; eventCount = 1;
    AddTextPrinter(&template, TEXT_SPEED_NOTRANSFER, NULL);
    current = NULL;
    assert(tasks == 0 && copied == 0);
    return 0;
}
"""
        self.compile_run(declarations + actual + checks, "-DQOL_INSTANT_TEXT=1")


    def test_instant_option_menu_labels_hitboxes_and_selection_bounds(self):
        text = (ROOT / "src/options_app.c").read_text()
        def array(name):
            match = re.search(r"static const [^;=]*\b" + name + r"[^=]*= \{", text)
            self.assertIsNotNone(match, name)
            start = match.start()
            pos, depth = match.end(), 1
            while depth:
                depth += (text[pos] == "{") - (text[pos] == "}")
                pos += 1
            return text[start:pos + 1]
        declarations = r"""
#include <assert.h>
#include <stdlib.h>
#include "qol_config.h"
#include "constants/charcode.h"
typedef unsigned char u8; typedef signed char s8;
typedef unsigned short u16; typedef unsigned int u32;
enum { MENU_ENTRY_TEXT_SPEED, MENU_ENTRY_BATTLE_SCENE, MENU_ENTRY_BATTLE_STYLE,
       MENU_ENTRY_SOUND_METHOD, MENU_ENTRY_BUTTON_MODE, MENU_ENTRY_FRAME,
       MENU_ENTRY_6, MENU_ENTRY_COUNT };
typedef union { struct { u8 top, bottom, left, right; } rect; } TouchscreenHitbox;
#define TOUCHSCREEN_RECTLIST_END .rect = {255,0,0,0}
typedef struct { u16 chars[32]; unsigned size; unsigned msg; } String;
typedef struct { u16 numStrings, value; String *strings[20]; } OptionsApp_MenuEntry;
typedef struct {
    unsigned heapID; void *msgData;
    struct { unsigned textSpeed, battleScene, battleStyle, soundMethod, buttonMode, frame; } options;
    OptionsApp_MenuEntry menuEntries[MENU_ENTRY_COUNT];
} OptionsApp_Data;
enum { msg_0045_00009 = 9 };
static String *String_New(unsigned count, unsigned heap) { return calloc(1, sizeof(String)); }
static String *NewString_ReadMsgData(void *msg, unsigned number) {
    String *s = String_New(32, 0); s->msg = number; return s;
}
void String_AddChar(String *s, u16 c) { s->chars[s->size++] = c; }
"""
        arrays = "\n".join(array(name) for name in
                           ("sNumChoicesPerMenuEntry", "sOptionChoiceLabelXCoords",
                            "sActiveButtonXCoords", "sOptionsAppTouchscreenHitboxes",
                            "sOptionsAppHitboxEntryValues"))
        actual = function_source("src/options_app.c", "OptionsApp_LoadMenuEntriesData")
        checks = r"""
int main(void) {
    // A QoL save must also open safely in a build with the feature disabled.
    OptionsApp_Data data = {0}; data.options.textSpeed = 3;
    OptionsApp_LoadMenuEntriesData(&data);
    assert(data.menuEntries[0].numStrings == 3 + QOL_INSTANT_TEXT);
    assert(data.menuEntries[0].value == (QOL_INSTANT_TEXT ? 3 : 2));
    // Existing message IDs for later rows must not shift when adding a choice.
    assert(data.menuEntries[1].strings[0]->msg == 12);
    assert(data.menuEntries[5].strings[19]->msg == 39);
    assert(sNumChoicesPerMenuEntry[0] == 3);
#if QOL_INSTANT_TEXT
    assert(data.menuEntries[0].strings[3]->size == 7);
    assert(data.menuEntries[0].strings[3]->chars[0] == CHAR_I);
#endif
    for (int choice = 0; choice < 3 + QOL_INSTANT_TEXT; choice++) {
        assert(sOptionsAppHitboxEntryValues[choice][0] == MENU_ENTRY_TEXT_SPEED);
        assert(sOptionsAppHitboxEntryValues[choice][1] == (unsigned)choice);
        unsigned x = sOptionChoiceLabelXCoords[0][choice];
        int widths[] = {24, 18, 24, 42}; // font 0 widths of SLOW, MID, FAST, INSTANT
        assert((int)x - widths[choice] / 2 >= 0);
        assert((int)x - widths[choice] / 2 + widths[choice] <= 240);
        assert(x >= sOptionsAppTouchscreenHitboxes[choice].rect.left);
        assert(x < sOptionsAppTouchscreenHitboxes[choice].rect.right);
        assert(sActiveButtonXCoords[0][choice] <= (int)x);
    }
    assert(sOptionsAppHitboxEntryValues[13 + QOL_INSTANT_TEXT][0] == MENU_ENTRY_6);
    int quitIndex = 14 + QOL_INSTANT_TEXT;
    assert(sOptionsAppHitboxEntryValues[quitIndex][0] == MENU_ENTRY_6);
    for (unsigned row = 0; row < MENU_ENTRY_COUNT; row++)
        for (unsigned j = 0; j < data.menuEntries[row].numStrings; j++)
            free(data.menuEntries[row].strings[j]);
    return 0;
}
"""
        for enabled in (0, 1):
            with self.subTest(enabled=enabled):
                self.compile_run(declarations + arrays + actual + checks,
                                 f"-DQOL_INSTANT_TEXT={enabled}")


    def test_real_renderer_requires_new_input_at_instant_page_wait(self):
        header = (ROOT / "include/render_text.h").read_text()
        start = header.index("typedef struct TextFlags {")
        end = header.index("} TextPrinterSubStruct;") + len("} TextPrinterSubStruct;")
        fixture = (ROOT / "tools/qol/fixtures/text_page_wait.c").read_text()
        names = ("TextPrinter_ContinueInputHeld", "TextPrinter_ContinueInputNew",
                 "TextPrinter_Continue", "TextPrinter_WaitAutoMode",
                 "TextPrinter_WaitWithDownArrow", "TextPrinter_Wait",
                 "TextPrinter_InitDownArrowCounters", "RenderText")
        actual = "\n".join(function_source("src/render_text.c", name) for name in names)
        actual += "\n" + "\n".join(function_source("src/text.c", name) for name in
                                    ("RenderFont", "RunTextPrinter", "AddTextPrinter"))
        source = fixture.replace("/* REAL_SUBSTRUCTS */", header[start:end])
        source = source.replace("/* REAL_FUNCTIONS */", actual)
        self.compile_run(source, "-DQOL_INSTANT_TEXT=1", "-Wno-c23-extensions")


    def test_real_renderer_rejects_the_initiating_touch_as_page_continuation(self):
        header = (ROOT / "include/render_text.h").read_text()
        start = header.index("typedef struct TextFlags {")
        end = header.index("} TextPrinterSubStruct;") + len("} TextPrinterSubStruct;")
        fixture = (ROOT / "tools/qol/fixtures/text_page_wait.c").read_text()
        # Same regression with touchscreen input instead of A.
        fixture = fixture.replace("gSystem.newKeys = gSystem.heldKeys = PAD_BUTTON_A;",
                                  "sTextFlags.canTouchSpeedUpPrint = 1; gSystem.touchNew = gSystem.touchHeld = 1;")
        fixture = fixture.replace("gSystem.newKeys = gSystem.heldKeys = 0;",
                                  "gSystem.touchNew = gSystem.touchHeld = 0;")
        fixture = fixture.replace("gSystem.newKeys = 0;", "gSystem.touchNew = 0;")
        names = ("TextPrinter_ContinueInputHeld", "TextPrinter_ContinueInputNew",
                 "TextPrinter_Continue", "TextPrinter_WaitAutoMode",
                 "TextPrinter_WaitWithDownArrow", "TextPrinter_Wait",
                 "TextPrinter_InitDownArrowCounters", "RenderText")
        actual = "\n".join(function_source("src/render_text.c", name) for name in names)
        actual += "\n" + "\n".join(function_source("src/text.c", name) for name in
                                    ("RenderFont", "RunTextPrinter", "AddTextPrinter"))
        source = fixture.replace("/* REAL_SUBSTRUCTS */", header[start:end])
        source = source.replace("/* REAL_FUNCTIONS */", actual)
        self.compile_run(source, "-DQOL_INSTANT_TEXT=1", "-Wno-c23-extensions")

if __name__ == "__main__":
    unittest.main()

