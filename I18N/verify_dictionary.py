# -*- encoding:utf-8 -*-
import csv
import glob
import re

# CSV ファイルを読み込んで key の一覧を集める
keys = set()
with open('I18N/i18n.csv', 'r', encoding='utf-8') as f:
    reader = csv.DictReader(f)
    for row in reader:
        keys.add(row['key'])

count = 0

# カレントフォルダの *.py ファイルを開いて処理
for pyfile in glob.glob('*.py'):
    with open(pyfile, 'r', encoding='utf-8') as f:
        src = f.read()

    # キーワードを検索
    for match in re.finditer(r"_\('(.*?)'\)", src):
        keyword = match.group(1)
        if keyword not in keys:
            print(f'Warning: key "{keyword}" not found in translation file, in file {pyfile}')
            count = 0
        else:
            print(keyword)

print(f'Done. Error={count}')
