"""Organização de conclusões já calculadas; sem recalcular métricas ou score."""
import re


PRIORIDADES = {"alta": 3, "media": 2, "baixa": 1}
TIPOS = {"atencao": "risco", "revisao": "risco", "positivo": "destaque"}
PRECEDENCIA = {"risco": 2, "oportunidade": 1, "destaque": 0, "informativo": 0}


def criar_insight(categoria, tipo, prioridade, texto, **contexto):
    return {
        "categoria": categoria,
        "tipo": TIPOS.get(tipo, tipo),
        "prioridade": prioridade,
        "texto": texto,
        **{chave: valor for chave, valor in contexto.items() if valor is not None},
    }


def _normalizar(item):
    return criar_insight(
        item["categoria"], item.get("tipo", "informativo"),
        item.get("prioridade", "baixa"), item.get("texto", item.get("mensagem", "")),
        **{chave: item[chave] for chave in ("valor", "metrica", "origem", "periodo") if chave in item},
    )


def _relevancia(item):
    contexto = sum(item.get(chave) is not None for chave in ("valor", "metrica", "periodo"))
    return (PRIORIDADES.get(item["prioridade"], 0), contexto,
            bool(re.search(r"\d", item["texto"])), len(item["texto"]))


def deduplicar_insights(insights):
    """Uma conclusão por categoria. Empates exatos preservam a ordem de origem."""
    categorias = {}
    for original in insights or []:
        item = _normalizar(original)
        if not item["texto"].strip():
            continue
        categoria = item["categoria"]
        if categoria not in categorias or _precedencia(item) > _precedencia(categorias[categoria]):
            categorias[categoria] = item
    return sorted(categorias.values(), key=_relevancia, reverse=True)


def _precedencia(item):
    return (PRECEDENCIA.get(item["tipo"], 0), *_relevancia(item))


def organizar_listas(insights):
    """Resolve identidade e destino globalmente, antes dos limites de cada seção."""
    candidatos = deduplicar_insights(insights)
    textos, unicos = set(), []
    for item in sorted(candidatos, key=_precedencia, reverse=True):
        texto = " ".join(item["texto"].split()).casefold()
        if texto not in textos:
            textos.add(texto)
            unicos.append(item)
    return {
        "principais_riscos": para_relatorio(unicos, tipo="risco", limite=5),
        "oportunidades": para_relatorio(unicos, tipo="oportunidade", limite=5),
        "principais_insights": para_relatorio(
            [item for item in unicos if item["tipo"] in ("destaque", "informativo")],
            limite=8, diversidade=True,
        ),
    }


def selecionar_insights(insights, limite=8):
    """Diversifica assuntos antes de completar o limite por relevância."""
    candidatos = deduplicar_insights(insights)
    selecionados, restantes, assuntos = [], [], set()
    for item in candidatos:
        categoria = item["categoria"]
        if categoria.startswith(("cliente_", "produto_", "estoque_")):
            assunto = categoria.split("_")[0]
        elif categoria.startswith(("tendencia_", "maior_", "melhor_periodo", "sequencia_")):
            assunto = "temporal"
        else:
            assunto = categoria
        if assunto in assuntos:
            restantes.append(item)
        else:
            assuntos.add(assunto)
            selecionados.append(item)
    return sorted((selecionados + restantes)[:limite], key=_relevancia, reverse=True)


def para_relatorio(insights, tipo=None, limite=8, diversidade=False):
    candidatos = deduplicar_insights(insights)
    if tipo:
        candidatos = [item for item in candidatos if item["tipo"] == tipo]
    candidatos = selecionar_insights(candidatos, limite) if diversidade else candidatos[:limite]
    # Contrato público existente: os cards e filtros usam estes metadados.
    tipos_publicos = {"risco": "atencao", "destaque": "positivo"}
    return [{
        "categoria": item["categoria"],
        "prioridade": item["prioridade"],
        "mensagem": item["texto"],
        **({"tipo": tipos_publicos.get(item["tipo"], item["tipo"])} if tipo is None else {}),
    } for item in candidatos]
