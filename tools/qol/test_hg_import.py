import unittest

import hg_import


class HgImportTests(unittest.TestCase):
    def test_gen9_profile_overrides_all_champions_switches_and_rejects_drift(self):
        config = '#ifndef CONFIG_H\n#define CONFIG_H\n' + ''.join(
            f'#define CHAMPIONS_{field}_CHANGES 1\n' for field in ('POWER', 'TYPE', 'ACC', 'PP', 'EFFECT_CHANCE')) + '#endif\n'
        result = hg_import.gen9_config(config)
        for field in ('POWER', 'TYPE', 'ACC', 'PP', 'EFFECT_CHANCE'):
            self.assertIn(f'#define CHAMPIONS_{field}_CHANGES 0', result)
        with self.assertRaises(ValueError):
            hg_import.gen9_config(config.replace('CHAMPIONS_PP_CHANGES', 'RENAMED_PP_OPTION'))

    def test_ability_ids_fit_existing_save_bytes_without_collisions(self):
        mapping = hg_import.ability_mapping({0, 26, 123, 130, 172, 256, 274, 292})
        self.assertEqual(mapping[123], 123)
        self.assertEqual(mapping[256], 240)
        self.assertEqual(mapping[274], 241)
        self.assertEqual(mapping[292], 242)
        self.assertEqual(len(set(mapping.values())), len(mapping))
        with self.assertRaises(ValueError):
            hg_import.ability_mapping({240, 256})
        with self.assertRaises(ValueError):
            hg_import.ability_mapping({300})

    def test_import_does_not_mistake_upstream_unimplemented_bit_for_flinch(self):
        self.assertEqual(hg_import.translate_move_flags(0x73, legacy_flags=0x53), 0x53)
        self.assertEqual(hg_import.translate_move_flags(0x53, legacy_flags=0x73), 0x73)
        self.assertEqual(hg_import.translate_move_flags(0x73), 0x53)

    def test_level_data_can_represent_new_move_ids_and_validates_inputs(self):
        self.assertEqual(hg_import.pack_level_entries([(1, 33), (44, 588)]),
                         [0x10021, 0x2C024C, 0xFFFFFFFF])
        for entries in ([(101, 33)], [(1, 65536)], [(5, 33), (1, 45)]):
            with self.assertRaises(ValueError):
                hg_import.pack_level_entries(entries)
