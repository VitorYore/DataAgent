from pathlib import Path
import json
from src.ingestion.loader import carregar_tabelas_arquivo
from src.analytics.assisted_mapping import perfilar_colunas, precisa_mapeamento
p=Path(r'C:\Users\User\Downloads\2017 a 2020.xlsx')
tables=carregar_tabelas_arquivo(p)
out={}
for name,df in tables.items():
 detected,required,auto=perfilar_colunas(df)
 out[name]={'shape':list(df.shape),'columns':[str(x) for x in df.columns],
 'auto':auto,'required':required,'profiles':[{'name':d['nome'],'role':d['papel_estrutural'],'semantic':d['conceito_semantico'],'suggestion':d['sugestao_semantica'],'origin':d['origem_mapeamento'],'confidence':d['confianca_mapeamento'],'non_null':int(df[d['nome']].notna().sum())} for d in detected],
 'header_evidence':df.attrs.get('ingestao',{}).get('normalizacao',{}).get('evidencias_cabecalho_tardio',[]),
 'metadata':{k:v for k,v in df.attrs.get('ingestao',{}).get('normalizacao',{}).items() if k not in ('auditoria_linhas','resumos','evidencias_excel','blocos','formulas_indisponiveis')}}
Path('.validation-loaded-profile.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
