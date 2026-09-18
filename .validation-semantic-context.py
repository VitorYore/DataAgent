from pathlib import Path
import json
base=Path('data/uploads')
for p in base.glob('analysis-*/working/mapping_context.json'):
 try:
  x=json.loads(p.read_text(encoding='utf-8'))
  print('\n',p, 'status',x.get('status'),'created',x.get('created_at'))
  print('auto',x.get('automatic_mappings'))
  print('required',x.get('required_mappings'))
  for d in x.get('detected_columns',[]):
   if d.get('nome') in ('coluna_1','coluna_2','coluna_3','coluna_4','coluna_5','coluna_6','coluna_7','coluna_8'):
    print(d.get('nome'),d.get('papel_estrutural'),d.get('confianca_estrutural'),d.get('conceito_semantico'),d.get('exemplos'),d.get('percentual_nulos'))
 except Exception as e: print('ERR',p,e)
