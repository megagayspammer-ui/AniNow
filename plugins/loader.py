# Plugin loader and common utilities for AniNow
import importlib
import os
import glob

PLUGINS = []


def load_plugins():
    # load python files in plugins/ directory except __init__.py
    base = os.path.join(os.path.dirname(__file__), 'plugins')
    if not os.path.isdir(base):
        return []
    for p in glob.glob(os.path.join(base, '*.py')):
        name = os.path.splitext(os.path.basename(p))[0]
        if name == '__init__':
            continue
        module_name = f'plugins.{name}'
        try:
            mod = importlib.import_module(module_name)
            PLUGINS.append(mod)
        except Exception:
            continue
    return PLUGINS
