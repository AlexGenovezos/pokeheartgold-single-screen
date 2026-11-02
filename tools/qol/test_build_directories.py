"""Output enrollment for finite SDK producers, without invoking the SDK."""
import ast
import inspect
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
PRODUCERS = (
    ('msl-new-partition', 'src', 'to91_msl_array_new', 'new.mk'),
    ('msl-d1-partition', 'src', 'to91_msl_shared_ptr_char_d1', 'd1.mk'),
    ('dwc-iterator-advance', 'lib/NitroDWC/src', 'to91_ov45_iterator_advance108', 'iterator.mk'),
)


def producer_tree(folder):
    return ast.parse((ROOT / 'tools' / folder / 'build.py').read_text())


def real_guard(folder, root):
    tree = producer_tree(folder)
    functions = {node.name: node for node in tree.body if isinstance(node, ast.FunctionDef)}
    if 'registered_object' in functions:
        function = functions['registered_object']
    else:
        # Execute the old production assertion before the explicit-root API
        # exists. This keeps baseline RED about rejected output, not imports.
        check = next(node for node in ast.walk(functions['build'])
                     if isinstance(node, ast.Assert) and isinstance(node.msg, ast.Constant)
                     and node.msg.value == 'unregistered object or dishonest basename')
        function = ast.parse('def registered_object(source, obj, game, build_dir=None):\n pass').body[0]
        function.body = [check, ast.Return(value=ast.Name(id='obj', ctx=ast.Load()))]
    namespace = dict(ROOT=root, Path=Path)
    module = ast.fix_missing_locations(ast.Module(body=[function], type_ignores=[]))
    exec(compile(module, folder + '/build.py', 'exec'), namespace)
    return namespace['registered_object']


class BuildDirectoryTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name).resolve()
        (self.root / 'build').mkdir()

    def test_legacy_default_keeps_exact_game_output_and_basename(self):
        for folder, subdir, stem, _ in PRODUCERS:
            guard = real_guard(folder, self.root)
            source = self.root / subdir / (stem + '.cpp')
            for game in ('heartgold', 'soulsilver'):
                target = self.root / 'build' / (game + '.us') / subdir / (stem + '.o')
                with self.subTest(producer=folder, game=game):
                    self.assertEqual(guard(source, target, game), target)
                    with self.assertRaises(AssertionError):
                        guard(source, target.with_name('another.o'), game)

    def test_explicit_relative_and_absolute_build_roots_accept_only_the_enrolled_child(self):
        for folder, subdir, stem, _ in PRODUCERS:
            guard = real_guard(folder, self.root)
            source = self.root / subdir / (stem + '.cpp')
            for game in ('heartgold', 'soulsilver'):
                relative = Path('build') / (game + '-qol-ui.us')
                target = self.root / relative / subdir / (stem + '.o')
                for selected in (relative, self.root / relative):
                    with self.subTest(producer=folder, game=game, selected=str(selected)):
                        try:
                            result = guard(source, target, game, selected)
                        except AssertionError as error:
                            self.fail(f'Explicit isolated SDK output was rejected: {error}')
                        self.assertEqual(result, target)

    def test_custom_roots_remain_opt_in_and_wrong_children_are_rejected(self):
        for folder, subdir, stem, _ in PRODUCERS:
            guard = real_guard(folder, self.root)
            source = self.root / subdir / (stem + '.cpp')
            selected = self.root / 'build' / 'isolated'
            target = selected / subdir / (stem + '.o')
            with self.subTest(producer=folder):
                with self.assertRaises(AssertionError):
                    guard(source, target, 'soulsilver')
                for wrong in (target.with_name('another.o'), selected / 'other' / target.name,
                              self.root / 'build' / 'elsewhere' / subdir / target.name):
                    with self.assertRaises(AssertionError):
                        guard(source, wrong, 'soulsilver', selected)

    def test_legacy_default_resolves_a_symlink_within_the_build_tree(self):
        selected = self.root / 'build' / 'actual'
        selected.mkdir()
        (self.root / 'build' / 'soulsilver.us').symlink_to(selected, target_is_directory=True)
        for folder, subdir, stem, _ in PRODUCERS:
            guard = real_guard(folder, self.root)
            source = self.root / subdir / (stem + '.cpp')
            target = selected / subdir / (stem + '.o')
            with self.subTest(producer=folder):
                try:
                    result = guard(source, target, 'soulsilver')
                except AssertionError as error:
                    self.fail(f'Existing owned default symlink was rejected: {error}')
                self.assertEqual(result, target)

    def test_outside_roots_parent_traversal_and_symlink_escapes_are_rejected(self):
        for folder, subdir, stem, _ in PRODUCERS:
            guard = real_guard(folder, self.root)
            source = self.root / subdir / (stem + '.cpp')
            roots = [self.root / 'outside', Path('build/../../outside'), self.root / 'build']
            external = self.root / 'external'; external.mkdir(exist_ok=True)
            link = self.root / 'build' / ('link-' + folder); link.symlink_to(external, target_is_directory=True)
            roots.append(link)
            for selected in roots:
                target = (self.root / selected / subdir / (stem + '.o')).resolve()
                with self.subTest(producer=folder, selected=str(selected)):
                    with self.assertRaises(AssertionError):
                        guard(source, target, 'soulsilver', selected)
            selected = self.root / 'build' / ('internal-' + folder)
            child = selected / subdir; child.parent.mkdir(parents=True)
            child.symlink_to(external, target_is_directory=True)
            with self.assertRaises(AssertionError):
                guard(source, (child / (stem + '.o')).resolve(), 'soulsilver', selected)

    def test_make_and_command_line_forward_the_explicit_root(self):
        for folder, _, _, makefile in PRODUCERS:
            with self.subTest(producer=folder):
                recipe = (ROOT / 'tools' / folder / makefile).read_text()
                self.assertIn('--build-dir "$(BUILD_DIR)"', recipe)
                result = subprocess.run([sys.executable, str(ROOT / 'tools' / folder / 'build.py'), '--help'],
                                        capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn('--build-dir', result.stdout)

    def test_real_build_rejects_an_unregistered_output_before_deleting_it(self):
        for folder, subdir, stem, _ in PRODUCERS:
            tree = producer_tree(folder)
            selected = [node for node in tree.body if isinstance(node, ast.FunctionDef)
                        and node.name in ('registered_object', 'paths', 'remove', 'build')]
            source = self.root / subdir / (stem + '.cpp')
            target = self.root / 'outside' / (folder + '.o')
            target.parent.mkdir(exist_ok=True)
            target.write_bytes(b'unregistered output must survive')
            namespace = dict(ROOT=self.root, Path=Path,
                             config=lambda *args: dict(source=str(source.relative_to(self.root)), source_sha256='pin'),
                             digest=lambda path: 'pin')
            exec(compile(ast.fix_missing_locations(ast.Module(body=selected, type_ignores=[])),
                         folder + '/build.py', 'exec'), namespace)
            arguments = [source, target, 'soulsilver', False, 'SDK forbidden']
            if folder == 'msl-new-partition':
                arguments.append('array')
            keywords = dict(build_dir='build/isolated') if 'build_dir' in inspect.signature(namespace['build']).parameters else {}
            with self.subTest(producer=folder):
                with self.assertRaises(AssertionError):
                    namespace['build'](*arguments, **keywords)
                self.assertTrue(target.exists(), 'Unregistered output was deleted before path validation')
                self.assertEqual(target.read_bytes(), b'unregistered output must survive')


if __name__ == '__main__':
    unittest.main()
