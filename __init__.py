"""
Copyright (c) 2022 DaDaDan3D
Released under the MIT license
https://opensource.org/licenses/mit-license.php

"""

import sys, importlib
import bpy

bl_info = {
    "name": "DDDTools",
    "description": "DaDaDan3D's miscellaneous tools for Blender.",
    "warning": "Not much error handling. Use at your own risk.",
    "support": "TESTING",
    "author": "DaDaDan3D",
    "version": (0, 1),
    "blender": (3, 1, 0),
    "doc_url": "https://github.com/DaDaDan3D/DDDTools",
    "tracker_url": "https://github.com/DaDaDan3D/DDDTools/issues",
    "category": "Object",
    "location": "View3D > Sidebar > DDDTools"
}

module_names = [
    'internalUtils',
    'fitting',
    'BoneTool',
    'ColliderTool',
    'MaterialTool',
    'WeightTool',
    'ExportVRM',
    'SelectTool',

    'UI_SelectTool',
    'UI_MaterialTool',
    'UI_ColliderTool',
    'UI_BoneTool',
    'UI_WeightTool',
    'CalcSphereFromSelectedVertices',
]

def import_or_reload_modules(module_names, package_name):
    ensure_starts_with = lambda s, prefix: s if s.startswith(prefix) else prefix + s
    module_names = [ensure_starts_with(name, f'{package_name}.') for name in module_names]
    modules = []
    for module_name in module_names:
        module = sys.modules.get(module_name)
        if module:
            module = importlib.reload(module)
        else:
            module = globals()[module_name] = importlib.import_module(module_name)
        modules.append(module)
    return modules

def reloadModules():
    unregister()
    register()

def register():
    import_or_reload_modules(module_names, __name__)

    for module_name in module_names:
        module = globals()[module_name]
        if 'registerClass' in dir(module):
            module.registerClass()

def unregister():
    for module_name in reversed(module_names):
        module = globals()[module_name]
        if 'unregisterClass' in dir(module):
            module.unregisterClass()

if __name__ == '__main__':
    register()
