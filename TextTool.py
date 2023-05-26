# -*- encoding:utf-8 -*-
import bpy
import json

_ = lambda s: s
from bpy.app.translations import pgettext_iface as iface_

def check_json(text_block):
    error_msg = None
               
    if text_block is None:
        error_msg = iface_('Text is not opened in the editor.')
        return error_msg

    # テキストの内容を取得
    text_content = text_block.as_string()

    # JSONのチェック
    try:
        json.loads(text_content)

    except json.JSONDecodeError as e:
        line_number = e.doc.count('\n', 0, e.pos)
        column_number = e.pos - e.doc.rfind('\n', 0, e.pos)
        
        # エラー行にカーソルを移動
        text_block.cursor_set(line_number, character=column_number)
        text_block.select_set(line_number, column_number - 1,
                              line_number, column_number)

        error_msg = iface_('Invalid JSON string: {e_msg} at line {line_number} column {column_number}').format(
            e_msg=iface_(e.msg),
            line_number=line_number,
            column_number=column_number,
            )

    return error_msg
