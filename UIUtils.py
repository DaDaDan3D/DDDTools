# -*- encoding:utf-8 -*-

import bpy

def splitSwitch(layout, prop, propName):
    """
    Checks prop.propName and draw bool switch.

    Parameters
    ----------
    layout: bpy.types.UILayout
        Layout to draw UI.

    prop: bpy.types.PropertyGroup
        PropertyGroup which contains property(propName).

    propName: string
        Name of property to check if display.

    Returns
    -------
        display: bool
        split: UILayout
    """

    split = layout.split(factor=0.15, align=True)
    display = getattr(prop, propName)
    if display:
        split.prop(prop, propName,
                   text='', icon='DOWNARROW_HLT')
    else:
        split.prop(prop, propName,
                   text='', icon='RIGHTARROW')
    return display, split
