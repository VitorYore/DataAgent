from pathlib import Path
import json
from src.ingestion.loader import carregar_tabelas_arquivo
df=next(iter(carregar_tabelas_arquivo(Path(r'C:\Users\User\Downloads\2017 a 2020.xlsx')).values()))
m=df.attrs['ingestao']['normalizacao']
out={'audit_headers':[x for x in m.get('auditoria_linhas',[]) if x.get('tipo')=='cabecalho' or x.get('linha') in range(3952,3962)],
     'evidence':m.get('evidencias_cabecalho_tardio'),
     'formulas_count':len(m.get('evidencias_excel',{}).get('formulas',[]))}
Path('.validation-header-debug.json').write_text(json.dumps(out,ensure_ascii=False,indent=2),encoding='utf-8')
