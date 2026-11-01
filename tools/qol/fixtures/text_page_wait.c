/* Host edges only: printer and input state machines are inserted from game C. */
#include <assert.h>
#include <stddef.h>
#include <stdlib.h>
#include "qol_config.h"
#include "constants/charcode.h"
typedef unsigned char u8; typedef unsigned short u16; typedef unsigned int u32;
typedef int s32; typedef int BOOL; typedef void SysTask;
typedef void (*SysTaskFunc)(SysTask *, void *);
enum { FALSE, TRUE, HEAP_ID_DEFAULT = 0, MAX_TEXT_PRINTERS = 8,
       TEXT_SPEED_INSTANT = 0, TEXT_SPEED_INSTANT_ASYNC = 254, TEXT_SPEED_NOTRANSFER = 255,
       PAD_BUTTON_A = 1, PAD_BUTTON_B = 2, SEQ_SE_DP_SELECT = 0 };
typedef struct { int dummy; } Window;
typedef struct { int dummy; } TouchscreenHitbox;
typedef struct { u8 data[128]; u8 width, height; } GlyphInfo;
typedef struct {
    union { void *wrapped; const u16 *raw; } currentChar;
    Window *window;
    int fontId, x, y, currentX, currentY, lineSpacing, letterSpacing;
    int fgColor, bgColor, shadowColor, savedColor, glyphTable, unk1A;
} TextPrinterTemplate;
typedef BOOL (*PrinterCallback_t)(TextPrinterTemplate *, u16);
typedef struct {
    TextPrinterTemplate template;
    PrinterCallback_t callback;
    u8 subStructFields[7], active, state;
    u8 textSpeedBottom : 7, textSpeedTop : 1;
    u8 delayCounter, scrollDistance, id, callbackResult;
    u16 callbackParam;
} TextPrinter;
typedef enum { RENDER_PRINT, RENDER_FINISH, RENDER_REPEAT, RENDER_UPDATE } RenderResult;
/* REAL_SUBSTRUCTS */
struct { unsigned newKeys, heldKeys; int touchNew, touchHeld; } gSystem;
TextFlags sTextFlags;
TouchscreenHitbox sTouchScreenHitbox;
int _021D1F6C, sDownArrowBaseTile;
static int cleared, finished;
static void *sFonts = (void *)1;
static TextPrinter *activePrinter;
static void RunTextPrinter(SysTask *, TextPrinter *);
static RenderResult RenderText(TextPrinter *);
static RenderResult RenderFont(TextPrinter *);
static BOOL TextPrinter_WaitAutoMode(TextPrinter *);
static BOOL TextPrinter_WaitWithDownArrow(TextPrinter *);
static u8 TextPrinter_Wait(TextPrinter *);
#define TouchscreenHitbox_TouchHeldIsIn(h) (1)
#define TouchscreenHitbox_TouchNewIsIn(h) (1)
#define GenerateFontHalfRowLookupTable(a,b,c) ((void)0)
#define RenderScreenFocusIndicatorTile(a,b,c,d) ((void)0)
#define CopyWindowToVram(w) ((void)0)
#define CopyGlyphToWindow(...) ((void)0)
#define ScrollWindow(...) ((void)0)
#define PlaySE(seq) ((void)0)
#define LoadDownArrowTiles(w,t) ((void)0)
#define TextPrinter_DrawDownArrow(p) ((void)0)
#define TextPrinter_ClearDownArrow(p) ((void)0)
#define FillWindowPixelBuffer(w,c) (++cleared)
#define GF_ASSERT(c) assert(c)
static int GetFontAttribute(int font, int attribute) { return 8; }
static int GetWindowWidth(Window *w) { return 30; }
static int FontID_FlatArray_GetWidthFirstLine(int font, const u16 *s, int spacing) { return 8; }
static GlyphInfo *FontID_TryLoadGlyph(int font, u16 c) {
    static GlyphInfo glyph = {{0}, 6, 8}; return &glyph;
}
static int MsgArray_GetControlCode(const u16 *p) { return p[1]; }
static u16 MsgArray_ControlCodeGetField(const u16 *p, int field) { return p[2 + field]; }
static const u16 *MsgArray_SkipControlCode(const u16 *p) { return p + 3; }
static RenderResult FontID_RenderText(int font, TextPrinter *p) { return RenderText(p); }
static void *Heap_Alloc(int heap, size_t size) { return activePrinter = calloc(1, size); }
static void Heap_Free(void *p) { free(p); }
static const u16 *String_cstr(void *string) { return string; }
static void TextPrinter_InitFocusIndicatorGfx(TextPrinter *p) {}
static void TextPrinter_FreeFocusIndicatorGfx(TextPrinter *p) {}
static int CreateTextPrinterSysTask(SysTaskFunc fn, TextPrinter *p, int priority) { return 0; }
static void DestroyTextPrinterSysTask(int id) { finished++; }
/* REAL_FUNCTIONS */
int main(void) {
    const u16 message[] = {CHAR_A, CHAR_B, 0x25BC, CHAR_C, EOS};
    TextPrinterTemplate template = {0};
    template.currentChar.wrapped = (void *)message;
    AddTextPrinter(&template, TEXT_SPEED_INSTANT_ASYNC, NULL);
    assert(sizeof(TextPrinterSubStruct) == 3);
    gSystem.newKeys = gSystem.heldKeys = PAD_BUTTON_A;
    RunTextPrinter(NULL, activePrinter);
    assert(activePrinter->state == 2 && cleared == 0);
    /* main.c runs the print queue twice before another input read. */
    RunTextPrinter(NULL, activePrinter);
    assert(activePrinter->state == 2 && cleared == 0);
    gSystem.newKeys = gSystem.heldKeys = 0; /* release */
    RunTextPrinter(NULL, activePrinter);
    assert(activePrinter->state == 2 && cleared == 0);
    gSystem.newKeys = gSystem.heldKeys = PAD_BUTTON_A; /* deliberate continuation */
    RunTextPrinter(NULL, activePrinter);
    assert(activePrinter->state == 0 && cleared == 1);
    gSystem.newKeys = 0;
    RunTextPrinter(NULL, activePrinter);
    assert(finished == 1);
    free(activePrinter);
    return 0;
}

