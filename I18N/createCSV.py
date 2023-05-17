# -*- encoding:utf-8 -*-

import csv
import os
import re

# フォルダのパスを指定します
folder_path = '.'

# CSVファイル名を指定します
csv_filename = 'i18n.csv'

# _() で囲まれた文字列を得る正規表現
regex = re.compile(r"_\(\s*(?P<single_quote>'([^'\\]*(\\.[^'\\]*)*)')|(?P<double_quote>\"([^\"\\]*(\\.[^\"\\]*)*)\")\s*\)")

# ASCII以外の文字か、100文字以上の文字列を検索する正規表現
non_ascii_or_long = re.compile(r'[^\x00-\x7F]|.{100,}')

# CSVファイルを開きます
with open(csv_filename, 'w', newline='', encoding='utf-8') as csvfile:
    writer = csv.writer(csvfile, quoting=csv.QUOTE_MINIMAL)

    # フォルダ内の全てのPythonファイルを検索します
    for root, dirs, files in os.walk(folder_path):
        for file in files:
            if file.endswith('.py'):
                with open(os.path.join(root, file), 'r', encoding='utf-8') as f:
                    lines = f.readlines()
                    for i, line in enumerate(lines):
                        for match in regex.findall(line):
                            literal = match[1] or match[4]
                            if non_ascii_or_long.search(literal):
                                writer.writerow([literal, os.path.join(root, file), i+1])
