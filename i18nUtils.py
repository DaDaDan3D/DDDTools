# -*- encoding:utf-8 -*-
import bpy
from .I18N.dictionary import translations_dict

def registerClass():
    bpy.app.translations.register(__package__, translations_dict)
    
def unregisterClass():
    bpy.app.translations.unregister(__package__)

if __name__ == '__main__':
    registerClass()
