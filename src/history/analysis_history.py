"""Snapshots compactos e comparação de KPIs existentes, sem recalculá-los."""
import json
import math
import re
from datetime import datetime, timezone
from pathlib import Path
from tempfile import NamedTemporaryFile
from uuid import uuid4


PASTA_HISTORICO = Path(__file__).resolve().parents[2] / 'data/analysis_history'
ID_PATTERN = re.compile(r'analysis_\d{8}_\d{12}_[0-9a-f]{32}')
METRICAS = ('faturamento_total', 'lucro_total', 'custo_total', 'margem_lucro',
            'ticket_medio', 'quantidade_pedidos', 'quantidade_vendida', 'quantidade_registros',
            'valor_total', 'valor_com_desconto', 'margem_bruta', 'margem_bruta_percentual')


def salvar_analise_historico(resumo, arquivos=None, pasta=PASTA_HISTORICO):
    pasta = Path(pasta)
    agora = datetime.now(timezone.utc)
    identificador = resumo.get('analysis_id') or novo_analysis_id(agora)
    status = resumo.get('status_geral') or {}
    kpis = resumo.get('kpis') or {}
    registro = {
        'id': identificador,
        'data_analise': agora.isoformat(),
        'arquivos': list(arquivos or []),
        'kpis': {chave: kpis[chave] for chave in METRICAS if chave in kpis},
        'score': status.get('score'),
        'status': status.get('status'),
    }
    encoded = json.dumps(registro, ensure_ascii=False, indent=2, allow_nan=False)
    pasta.mkdir(parents=True, exist_ok=True)
    temporario = None
    try:
        with NamedTemporaryFile(mode='w', encoding='utf-8', dir=pasta, suffix='.tmp', delete=False) as arquivo:
            temporario = Path(arquivo.name)
            arquivo.write(encoded)
        temporario.replace(pasta / f'{identificador}.json')
    finally:
        if temporario is not None:
            temporario.unlink(missing_ok=True)
    return registro


def novo_analysis_id(agora=None):
    agora = agora or datetime.now(timezone.utc)
    return f"analysis_{agora:%Y%m%d_%H%M%S%f}_{uuid4().hex}"


def obter_analise(identificador, pasta=PASTA_HISTORICO):
    if not ID_PATTERN.fullmatch(identificador):
        raise FileNotFoundError('Análise não encontrada.')
    caminho = Path(pasta).resolve() / f'{identificador}.json'
    if caminho.resolve().parent != Path(pasta).resolve():
        raise FileNotFoundError('Análise não encontrada.')
    with caminho.open(encoding='utf-8') as arquivo:
        registro = json.load(arquivo)
    if not isinstance(registro, dict) or registro.get('id') != identificador:
        raise ValueError('Registro de histórico inválido.')
    return registro


def listar_historico(pasta=PASTA_HISTORICO):
    registros = [obter_analise(caminho.stem, pasta) for caminho in Path(pasta).glob('analysis_*.json')]
    return sorted(registros, key=lambda item: (item.get('data_analise') or '', item['id']), reverse=True)


def obter_ultima_analise(pasta=PASTA_HISTORICO):
    registros = listar_historico(pasta)
    return registros[0] if registros else None


def _numero(valor):
    return valor if isinstance(valor, (int, float)) and not isinstance(valor, bool) and math.isfinite(valor) else None


def comparar_analises(atual, anterior):
    if atual is None or anterior is None:
        return {'status': 'insuficiente', 'mensagem': 'Execute uma nova análise para visualizar comparações.', 'metricas': {}}
    metricas = {}
    atuais, anteriores = atual.get('kpis') or {}, anterior.get('kpis') or {}
    for nome in METRICAS:
        if nome not in atuais and nome not in anteriores:
            continue
        a, b = _numero(atuais.get(nome)), _numero(anteriores.get(nome))
        margem = nome in {'margem_lucro', 'margem_bruta_percentual'}
        variacao = None
        if a is not None and b is not None and (margem or b != 0):
            resultado = a - b if margem else (a - b) / b * 100
            variacao = round(resultado, 2) if math.isfinite(resultado) else None
        metricas[nome] = {'atual': a, 'anterior': b,
                         'variacao_pontos_percentuais' if margem else 'variacao_percentual': variacao}
    return {'status': 'disponivel', 'analise_atual': atual.get('id'),
            'analise_anterior': anterior.get('id'), 'metricas': metricas}
