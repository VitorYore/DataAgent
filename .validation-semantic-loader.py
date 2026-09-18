import sys
sys.stdout.reconfigure(encoding='utf-8')
from pathlib import Path
from src.ingestion.loader import carregar_tabelas_arquivo
from src.analytics.assisted_mapping import perfilar_colunas, precisa_mapeamento
from src.analytics.column_mapper import mapear_colunas
p=Path(r'C:\Users\User\Downloads\2017 a 2020.xlsx')
t=carregar_tabelas_arquivo(p)
print('TABLES',list(t))
for name,df in t.items():
 print('DF',name,df.shape,df.columns.tolist(),df.dtypes.astype(str).to_dict())
 print('INGESTAO keys',df.attrs.get('ingestao',{}).keys())
 print('MAPPING_REQUIRED',precisa_mapeamento(df)[0])
 print('AUTO',precisa_mapeamento(df)[3])
 for d in precisa_mapeamento(df)[1]:
  print('PROFILE',d)
 print('nulls',df.isna().sum().to_dict())
 for c in df.columns:
  if str(c) in ('coluna_1','coluna_2','coluna_3','coluna_4','coluna_5','coluna_6','coluna_7','coluna_8'):
   s=df[c]
   print('COL',c,'dtype',s.dtype,'non_null',int(s.notna().sum()),'nunique',int(s.nunique(dropna=True)),'examples',s.dropna().head(5).tolist(),'auto_semantic',mapear_colunas(df)[c])
