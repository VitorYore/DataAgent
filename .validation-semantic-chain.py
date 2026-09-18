from pathlib import Path
import sys
sys.stdout.reconfigure(encoding='utf-8')
for f, spans in {
'src/analytics/column_mapper.py':[(220,250),(350,390),(810,970)],
'src/analytics/temporal.py':[(1,55)],
'src/analytics/business.py':[(80,210)],
'src/reports/executive_summary.py':[(35,110)],
'src/quality/type_inference.py':[(1,190)],
'main.py':[(630,740),(820,930)],
'api/analysis.py':[(113,185)],
}.items():
 lines=Path(f).read_text(encoding='utf-8-sig').splitlines()
 for a,b in spans:
  print(f'\n### {f}:{a}-{b}')
  for i in range(a-1,min(b,len(lines))): print(f'{i+1}: {lines[i]}')
