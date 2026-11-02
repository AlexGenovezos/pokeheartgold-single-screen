"""Repeatable preparation of owned Options labels; no game text is embedded."""
from pathlib import Path
import importlib.util
import re
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[2]
HELPER = ROOT / 'tools/qol/options_messages.py'
LABELS = ('LEVEL CAPS', 'LEVEL CAP', 'OFF', 'ON', 'NEXT BOSS', 'NO CAP',
          'CONFIRM TO APPLY', 'X: CAPS', 'X: OPTIONS',
          '{STRVAR_1 0, 0, 0}  Lv. {STRVAR_1 52, 1, 0}')


def row(index, text):
    return (f'\t<row id="msg_0045_{index:05}" index="{index}">\n'
            '\t\t<attribute name="window_context_name">used</attribute>\n'
            f'\t\t<language name="English">{text}</language>\n\t</row>\n').encode()


def stock():
    # Synthetic original content, preserving the real bank's 60-ID shape.
    return b'<?xml version="1.0"?>\n<body language="English">\n' + b''.join(
        row(i, f'base message {i}') for i in range(60)) + b'</body>\n'


def append(source, rows):
    return source.replace(b'</body>', b''.join(rows) + b'</body>', 1)


class OptionsMessagesTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        if HELPER.exists():
            spec = importlib.util.spec_from_file_location('options_messages', HELPER)
            cls.helper = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(cls.helper)
        else:
            # Before integration a fresh imported bank stays stock and none of
            # the compiler flags causes owned message preparation.
            class Unprepared:
                prepare_options_messages = staticmethod(lambda source, enabled: source)
                resolve_level_caps = staticmethod(lambda arguments, environ=None: False)
            cls.helper = Unprepared

    def test_enabled_appends_fixed_owned_ids_and_preserves_every_prefix_byte(self):
        original = stock()
        prepared = self.helper.prepare_options_messages(original, True)
        rows = ET.fromstring(prepared).findall('row')
        self.assertEqual([int(r.attrib['index']) for r in rows], list(range(70)))
        self.assertEqual(prepared[:prepared.index(b'\t<row id="msg_0045_00060"')],
                         original[:original.index(b'</body>')])
        self.assertEqual([r.find("language[@name='English']").text for r in rows[60:]], list(LABELS))

    def test_enable_is_idempotent_and_disable_restores_exact_original_bytes(self):
        original = stock()
        prepared = append(original, [row(i, text) for i, text in enumerate(LABELS, 60)])
        self.assertEqual(self.helper.prepare_options_messages(prepared, True), prepared)
        self.assertEqual(self.helper.prepare_options_messages(prepared, False), original)
        self.assertEqual(self.helper.prepare_options_messages(original, False), original)

    def test_valid_closing_layouts_restore_every_original_byte(self):
        original = stock()
        layouts = (
            original.replace(b'</body>', b'  </body>'),
            original.replace(b'\t</row>\n</body>', b'\t</row></body>'),
            original.replace(b'</body>', b'\t </body >'),
        )
        for layout in layouts:
            for source in (layout, layout.replace(b'\n', b'\r\n')):
                with self.subTest(source=source[-70:]):
                    try:
                        prepared = self.helper.prepare_options_messages(source, True)
                        repeated = self.helper.prepare_options_messages(prepared, True)
                        restored = self.helper.prepare_options_messages(prepared, False)
                    except ValueError as error:
                        self.fail(f'Valid XML layout must round-trip: {error}')
                    self.assertEqual(len(ET.fromstring(prepared).findall('row')), 70)
                    self.assertEqual(repeated, prepared)
                    self.assertEqual(restored, source)

    def test_unowned_text_between_or_after_rows_is_never_removed(self):
        prepared = append(stock(), [row(i, text) for i, text in enumerate(LABELS, 60)])
        cases = (
            prepared.replace(b'</body>', b'unowned text</body>'),
            prepared.replace(b'\t<row id="msg_0045_00061"', b'unowned text\t<row id="msg_0045_00061"'),
            prepared.replace(b'\t<row id="msg_0045_00061"', '\u00a0\t<row id="msg_0045_00061"'.encode()),
            stock().replace(b'<body language="English">', b'<body language="English">unowned text'),
        )
        for source in cases:
            for enabled in (False, True):
                with self.subTest(source=source[-80:], enabled=enabled):
                    with self.assertRaises(ValueError):
                        self.helper.prepare_options_messages(source, enabled)

    def test_only_the_actual_root_closing_tag_receives_generated_rows(self):
        original = stock().replace(b'<body language="English">',
                                   b'<!-- </body> -->\n<body language="English">')
        original += b'<!-- </body> -->\n'
        prepared = self.helper.prepare_options_messages(original, True)
        self.assertEqual(len(ET.fromstring(prepared).findall('row')), 70)
        self.assertEqual(self.helper.prepare_options_messages(prepared, True), prepared)
        self.assertEqual(self.helper.prepare_options_messages(prepared, False), original)

    def test_partial_drifted_unknown_and_duplicate_tails_fail_without_rewriting(self):
        original = stock()
        owned = [row(i, text) for i, text in enumerate(LABELS, 60)]
        cases = [append(original, owned[:5]),
                 append(original, owned).replace(b'NEXT BOSS', b'changed label'),
                 append(original, owned + [row(70, 'unknown owner')]),
                 append(original, owned).replace(b'index="61"', b'index="60"'),
                 append(original, owned).replace(b'>LEVEL CAPS</language>', b'>LEVEL CAPS<unknown/></language>'),
                 append(original, owned).replace(b'>LEVEL CAPS</language>', b'>LEVEL CAPS</language>unowned text'),
                 append(original, owned).replace(b'</body>', b'<!-- another owner -->\n</body>'),
                 append(original, owned).replace(b'name="window_context_name">used</attribute>\n\t\t<language name="English">LEVEL CAPS',
                                                b'name="unknown">used</attribute>\n\t\t<language name="English">LEVEL CAPS')]
        for source in cases:
            for enabled in (False, True):
                with self.subTest(source=source[-150:], enabled=enabled):
                    with self.assertRaises(ValueError):
                        self.helper.prepare_options_messages(source, enabled)

    def test_rejects_wrong_stock_shape_and_keeps_crlf_prefix_intact(self):
        original = stock()
        for source in (original.replace(b'index="1"', b'index="99"'),
                       original.replace(b'msg_0045_00010', b'msg_9999_00010')):
            with self.assertRaises(ValueError):
                self.helper.prepare_options_messages(source, True)
        crlf = original.replace(b'\n', b'\r\n')
        prepared = self.helper.prepare_options_messages(crlf, True)
        self.assertEqual(self.helper.prepare_options_messages(prepared, False), crlf)

    def test_explicit_flags_defaults_environment_and_last_define_match_the_compiler(self):
        cases = [([], {}, False),
                 (['CLI_DEFINES=-DQOL_MODS=1'], {}, True),
                 (['CLI_DEFINES=-DQOL_MODS=1 -DQOL_LEVEL_CAPS=0'], {}, False),
                 (['CLI_DEFINES=-DQOL_MODS=0 -DQOL_INSTANT_TEXT=0 -DQOL_LEVEL_CAPS=1'], {}, True),
                 (['CLI_DEFINES=-DQOL_MODERN_TYPES=1 -DQOL_MODERN_BATTLE=1 -DQOL_MODERN_MOVES=1'], {}, False),
                 ([], {'CLI_DEFINES': '-DQOL_MODS=1'}, True),
                 (['CLI_DEFINES='], {'CLI_DEFINES': '-DQOL_MODS=1'}, False),
                 (['CLI_DEFINES=-DQOL_LEVEL_CAPS=1 -DQOL_LEVEL_CAPS=0'], {}, False),
                 (['CLI_DEFINES=-D QOL_LEVEL_CAPS'], {}, True),
                 (['CLI_DEFINES=-DQOL_MODS=1 -DQOL_LEVEL_CAPS=0 -UQOL_LEVEL_CAPS'], {}, True),
                 (['CLI_DEFINES=-DQOL_LEVEL_CAPS=QOL_MODS -DQOL_MODS=1'], {}, True),
                 (['CLI_DEFINES=-DQOL_LEVEL_CAPS=0', 'CLI_DEFINES=-DQOL_MODS=1'], {}, True)]
        for arguments, environ, expected in cases:
            with self.subTest(arguments=arguments, environ=environ):
                self.assertEqual(self.helper.resolve_level_caps(arguments, environ), expected)

    def test_invalid_or_unevaluated_feature_defines_fail_before_resource_edits(self):
        for flags in ('-DQOL_LEVEL_CAPS=2', '-DQOL_LEVEL_CAPS=garbage',
                      '-DQOL_MODS=2', '-DQOL_LEVEL_CAPS=$(CAP_SUPPORT)'):
            with self.subTest(flags=flags):
                with self.assertRaises(ValueError):
                    self.helper.resolve_level_caps(['CLI_DEFINES=' + flags], {})

    def test_build_preparation_precedes_make_and_options_has_a_first_build_header_dependency(self):
        wrapper = (ROOT / 'scripts/build.sh').read_text()
        self.assertLess(wrapper.index('python3 tools/qol/options_messages.py -- "$@"'),
                        wrapper.index('exec "$make_bin"'))
        makefile = (ROOT / 'Makefile').read_text()
        self.assertIn('$(BUILD_DIR)/src/options_app.o: files/msgdata/msg/msg_0045.h', makefile)
        resource_rules = (ROOT / 'files/msgdata/msg.mk').read_text()
        self.assertIn('$(MSGFILE_H): %.h: %.bin', resource_rules)
        self.assertIn('files/msgdata/msg/msg_0045.bin: MSGENCFLAGS += -k 0xB90F', resource_rules)


if __name__ == '__main__':
    unittest.main()
