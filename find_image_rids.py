import zipfile

with zipfile.ZipFile('documents/系統手冊_1.docx', 'r') as z:
    rels = z.read('word/_rels/document.xml.rels').decode('utf-8')
    for line in rels.split('<Relationship '):
        for rid in ['rId25', 'rId28', 'rId35']:
            if f'Id="{rid}"' in line:
                print(rid, "-->", line)
