# -*- encoding:utf-8 -*-

"""
Copyright (c) 2022-2023 DaDaDan3D
Released under the MIT license
https://opensource.org/licenses/mit-license.php
"""

import sys, importlib

bl_info = {
    'name': 'DDDTools',
    'description': 'DaDaDan3D\'s miscellaneous tools for Blender.',
    'warning': 'Not much error handling. Use at your own risk.',
    'support': 'COMMUNITY',
    'author': 'DaDaDan3D',
    'version': (0, 6, 0),
    'blender': (4, 1, 0),
    'doc_url': 'https://github.com/DaDaDan3D/DDDTools',
    'tracker_url': 'https://github.com/DaDaDan3D/DDDTools/issues',
    'category': 'Object',
    'location': 'View3D > Sidebar > DDDTools'
}

modules = [
    'I18N.dictionary',
    'i18nUtils',
    'internalUtils',
    'UIUtils',
    'mathUtils',
    'BoneTool',
    'VRMTool',
    'MaterialTool',
    'WeightTool',
    'SelectTool',
    'NormalTool',
    'UVTool',
    'TextTool',
    'ProportionalMover',

    'UI_MaterialTool',
    'UI_EditTool',
    'UI_VRMTool',
    'UI_BoneTool',
    'UI_WeightTool',
    'UI_NormalTool',
    'UI_UVTool',
    'UI_ShaderTool',
    'UI_TextTool',
]
modules = [f'{__package__}.{mn}' for mn in modules]

def reloadModules():
    unregister()
    register()

def register():
    for mn in modules:
        module = sys.modules.get(mn)
        if module:
            module = importlib.reload(module)
        else:
            module = importlib.import_module(mn)

        if 'registerClass' in dir(module):
            module.registerClass()

def unregister():
    for mn in reversed(modules):
        module = sys.modules.get(mn)
        if module and 'unregisterClass' in dir(module):
            module.unregisterClass()

if __name__ == '__main__':
    register()
