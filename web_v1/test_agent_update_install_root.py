import ast
import io
import os
import subprocess
import tempfile
import types
import unittest
import zipfile
from pathlib import Path
from unittest.mock import Mock

ROOT = Path(__file__).resolve().parents[1]

def load_function(path, name, namespace):
    tree = ast.parse(path.read_text(encoding='utf-8-sig'))
    node = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == name)
    exec(compile(ast.Module(body=[node], type_ignores=[]), str(path), 'exec'), namespace)
    return namespace[name]

class AgentUpdateInstallRootTests(unittest.TestCase):
    def test_self_update_passes_existing_runtime_without_changing_parent_environment(self):
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder)
            runtime = base / 'Existing Agent Runtime'
            runtime.mkdir()
            unpack = base / 'update'
            unpack.mkdir()
            content = io.BytesIO()
            with zipfile.ZipFile(content, 'w') as archive:
                archive.writestr('setup.ps1', 'Write-Output ready')
            response = Mock(content=content.getvalue())
            start = Mock()
            namespace = {'Path': Path, 'PROJECT_ROOT': runtime, 'os': os,
                         'tempfile': types.SimpleNamespace(mkdtemp=lambda **kwargs: str(unpack)),
                         'zipfile': zipfile, 'requests': types.SimpleNamespace(get=lambda *a, **k: response),
                         'subprocess': types.SimpleNamespace(Popen=start), 'log': lambda text: None}
            before = dict(os.environ)
            update = load_function(ROOT / 'web_v1/agent/erp_agent.py', '_run_self_update', namespace)
            self.assertTrue(update('https://server.example', True))
            self.assertEqual(start.call_args.kwargs['env']['ACCOUNTING_WEB_INSTALL_ROOT'], str(runtime))
            self.assertEqual(dict(os.environ), before)

    def installer_root(self, env):
        script = load_function(ROOT / 'web_v1/backend/app.py', '_agent_installer_script', {})('https://server.example')
        prefix = script[:script.index('$PackageRoot')]
        command = '[Console]::OutputEncoding = [Text.UTF8Encoding]::new($false);\n' + prefix + '\nWrite-Output $InstallRoot'
        result = subprocess.run(['powershell.exe', '-NoProfile', '-Command', command],
                                env=env, capture_output=True, text=True, encoding='utf-8', check=True)
        return result.stdout.strip()

    def test_installer_respects_runtime_override_with_spaces(self):
        with tempfile.TemporaryDirectory() as folder:
            target = str(Path(folder) / 'Existing Agent Runtime')
            env = dict(os.environ, ACCOUNTING_WEB_INSTALL_ROOT=target)
            self.assertEqual(Path(self.installer_root(env)), Path(target))

    def test_manual_install_keeps_existing_default(self):
        env = dict(os.environ)
        env.pop('ACCOUNTING_WEB_INSTALL_ROOT', None)
        expected = Path(env['USERPROFILE']) / 'Desktop/개발파일/회계업무 자동화_WEB_Version'
        self.assertEqual(Path(self.installer_root(env)), expected)

if __name__ == '__main__':
    unittest.main()
