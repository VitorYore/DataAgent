from pathlib import Path
p=Path('src/analytics/assisted_mapping.py')
s=p.read_text(encoding='utf-8')
old='''    ask = normalizado and not business_mapped and bool(required)
'''
new='''    required_names = {item["coluna"] for item in required}
    suggested_ambiguous = any(
        item["nome"] in required_names
        and item.get("sugestao_semantica")
        and not item.get("conceito_semantico")
        for item in detected
    )
    ask = normalizado and bool(required) and (not business_mapped or suggested_ambiguous)
'''
assert s.count(old)==1
p.write_text(s.replace(old,new),encoding='utf-8')

p=Path('src/analytics/business.py')
s=p.read_text(encoding='utf-8')
needle='''        if not labels_by_position:
            continue
        source_rows ='''
replacement='''        for field, concept in {**df.attrs.get("mapeamentos_automaticos", {}), **df.attrs.get("mapeamentos_confirmados", {})}.items():
            match_column = re.fullmatch(r"coluna_(\\d+)", str(field))
            if match_column:
                labels_by_position[int(match_column.group(1))] = concept
        if not labels_by_position:
            continue
        source_rows ='''
assert s.count(needle)==1
p.write_text(s.replace(needle,replacement),encoding='utf-8')
