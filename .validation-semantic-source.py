from pathlib import Path
ranges={
'main.py':[(580,630),(2080,2385)],
'api/analysis.py':[(1,180)],
'src/analytics/business.py':[(1,225)],
'src/analytics/temporal.py':[(1,170)],
'src/etl/cleaner.py':[(1,250)],
'src/analytics/assisted_mapping.py':[(1,280)],
'src/analytics/column_mapper.py':[(860,995)],
}
for file, spans in ranges.items():
 lines=Path(file).read_text(encoding='utf-8-sig').splitlines()
 for a,b in spans:
  print(f'\n### {file}:{a}-{b}')
  for i in range(a-1,min(b,len(lines))): print(f'{i+1}: {lines[i]}')
