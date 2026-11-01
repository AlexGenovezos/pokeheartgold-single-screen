"""The fourth speed needs actual button geometry, not shifted text alone."""
from pathlib import Path
import re
import unittest
import test_game_logic as game

ROOT = Path(__file__).resolve().parents[2]


class OptionsButtonTests(unittest.TestCase):
    compile_run = game.GameLogicTests.compile_run

    def test_four_buttons_cover_old_art_and_keep_labels_inside_their_boxes(self):
        source = (ROOT / "src/options_app.c").read_text()
        actual = game.function_source("src/options_app.c", "OptionsApp_DrawTextSpeedButtons")
        array = re.search(r"static const u16 sTextSpeedButtonRects\[4\]\[2\] = \{.*?\n\};", source, re.S)
        self.assertIsNotNone(array)
        declarations = r'''
#include <assert.h>
#include <string.h>
typedef unsigned short u16;
typedef unsigned char u8;
typedef struct { u8 pixels[240*24]; } Window;
typedef struct { struct { Window selectedOption; } windows;
                 struct { unsigned value; } menuEntries[1]; } OptionsApp_Data;
#define MENU_ENTRY_TEXT_SPEED 0
void FillWindowPixelRect(Window *window, unsigned color, unsigned x, unsigned y, unsigned w, unsigned h) {
    assert(x+w <= 240 && y+h <= 24);
    for(unsigned row=y;row<y+h;row++) for(unsigned col=x;col<x+w;col++) window->pixels[row*240+col]=color;
}
'''
        checks = r'''
int main(void) {
    const unsigned widths[] = {24,18,24,42};
    for(unsigned selected=0;selected<4;selected++) {
        OptionsApp_Data data; memset(&data,0,sizeof(data));data.menuEntries[0].value=selected;
        OptionsApp_DrawTextSpeedButtons(&data);
        for(unsigned x=92;x<240;x++) for(unsigned y=0;y<24;y++)
            assert(data.windows.selectedOption.pixels[y*240+x] != 0);
        for(unsigned choice=0;choice<4;choice++) {
            unsigned left=sTextSpeedButtonRects[choice][0], width=sTextSpeedButtonRects[choice][1];
            assert(width >= widths[choice]+6);
            assert(left+width<=240);
            assert(data.windows.selectedOption.pixels[10*240+left+2] == (choice==selected?15:3));
            assert(data.windows.selectedOption.pixels[2*240+left] == 4);
            if(choice<3) assert(left+width < sTextSpeedButtonRects[choice+1][0]);
        }
    }
    return 0;
}
'''
        self.compile_run(declarations + array[0] + actual + checks)
