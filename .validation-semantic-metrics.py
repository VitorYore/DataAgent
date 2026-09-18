from pathlib import Path
from openpyxl import load_workbook
from collections import Counter
from datetime import datetime,date
import re,json
p=Path(r'C:\Users\User\Downloads\2017 a 2020.xlsx')
wf=load_workbook(p,data_only=False,read_only=False).active
wd=load_workbook(p,data_only=True,read_only=True).active
def isdate(x): return isinstance(x,(datetime,date))
by=Counter(); ids=[]; id_date=[]; sums=Counter(); dates=[]
formula_den=Counter(); formula_examples={}
formula_rows=[]
for r in range(1,wf.max_row+1):
    vals=[wf.cell(r,c).value for c in range(1,9)]
    if isinstance(vals[0],(int,float)) and isdate(vals[1]):
        id_date.append(r); ids.append(vals[0]); dates.append(vals[1])
        seg='pre_header' if r<3956 else 'post_header'
        by[seg]+=1
        for c,name in [(3,'valor_total'),(4,'valor_desconto'),(7,'margem_bruta')]:
            if isinstance(vals[c-1],(int,float)): sums[(seg,name)]+=vals[c-1]
    f=vals[7]
    if isinstance(f,str) and f.startswith('='):
        m=re.fullmatch(r'=G\d+/([CD])\d+',f.upper())
        if m:
            den=m.group(1); formula_den[('pre' if r<3956 else 'post',den)]+=1
            formula_examples.setdefault(('pre' if r<3956 else 'post',den),(r,vals))
print('transactions by region',dict(by),'rows',len(id_date),'unique ids',len(set(ids)),'duplicates',len(ids)-len(set(ids)),'missing id',0)
print('id range',min(ids),max(ids),'date range',min(dates),max(dates))
print('metric sums',dict(sums))
print('formula denominator counts',dict(formula_den))
for k,(r,vals) in formula_examples.items():
    print('formula example',k,'row',r,'vals',json.dumps(vals,default=str,ensure_ascii=False))
# Explicitly check margin ratio within relative tolerance on numeric rows (C and D)
for region, lo, hi, denominator in [('pre',1,3955,3),('post',3957,wf.max_row,4)]:
    rows=[]
    for r in range(lo,hi+1):
        c=wf.cell(r,3).value; d=wf.cell(r,4).value; g=wf.cell(r,7).value; h=wf.cell(r,8).value
        if isinstance(g,(int,float)) and isinstance(denominator==3 and c or d,(int,float)):
            base=c if denominator==3 else d
            rows.append((100*g/base if base else None,h if isinstance(h,(int,float)) else None))
    compared=[(a,b) for a,b in rows if a is not None and b is not None]
    print('ratio',region,'eligible',len(rows),'cached_numeric_formula',len(compared),'sample',rows[:3])
# date cell counts and non-id date rows
for region, lo, hi in [('pre',1,3955),('post',3956,wf.max_row)]:
    ndate=sum(isdate(wf.cell(r,2).value) for r in range(lo,hi+1))
    print('dates col B',region,ndate)
