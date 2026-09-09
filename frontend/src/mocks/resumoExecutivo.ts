import type { ExecutiveSummary } from '../types/dataAgent'

export const resumoExecutivo: ExecutiveSummary = {
  status_geral: {
    score: 35,
    status: 'critico',
    motivos: [
      'Faturamento apresenta tendência de queda.',
      'Lucro apresenta tendência de queda.',
      'Existem registros com resultado negativo.',
    ],
  },
  kpis: {
    faturamento_total: 505159249.56,
    lucro_total: 474743291.13,
    custo_total: 30415958.43,
    margem_lucro: 93.98,
    ticket_medio: 25257.96,
    quantidade_pedidos: 20000,
    quantidade_vendida: 1009021.0,
  },
  temporal: {
    serie_temporal: [
      { periodo: '2015-01', faturamento: 4123456.78, lucro: 3890000.12 },
      { periodo: '2015-02', faturamento: 4000000.0, lucro: 3770000.0 },
    ],
    melhor_periodo: { periodo: '2018-07', faturamento: 5115750.38 },
    pior_periodo: { periodo: '2022-10', faturamento: 2890558.57 },
    tendencia_faturamento: 'queda',
    evolucao_faturamento: -6.59,
    maior_crescimento: { periodo: '2022-11', variacao: 42.34 },
    maior_queda: { periodo: '2016-11', variacao: -30.23 },
  },
  clientes: {
    quantidade_clientes: 1000,
    cliente_maior_faturamento: {
      cliente: 'Kyara Santos (ID 874)',
      faturamento: 1086012.31,
    },
    cliente_maior_lucro: {
      cliente: 'Kyara Santos (ID 874)',
      lucro: 1023409.47,
    },
    concentracao_top_5: 1.03,
  },
  produtos: {
    ranking_produtos: [
      {
        posicao: 1,
        produto: 'Quis (ID 541)',
        produto_id: 541,
        quantidade: 1800.0,
        faturamento: 952866.23,
        lucro: 921997.03,
        avaliacao_media: 4.2,
        estoque_atual: 50.0,
        taxa_devolucao: 1.3,
      },
    ],
    quantidade_produtos: 1000,
    produto_mais_vendido: { produto: 'Molestias (ID 425)', quantidade: 1935.0 },
    produto_maior_faturamento: { produto: 'Quis (ID 541)', faturamento: 952866.23 },
    produto_maior_lucro: { produto: 'Quis (ID 541)', lucro: 921997.03 },
    produtos_risco_ruptura: 0,
    produtos_estoque_excessivo: 0,
  },
  principais_riscos: [
    {
      categoria: 'faturamento',
      prioridade: 'alta',
      mensagem: 'O faturamento apresenta tendência de queda (-6.59%).',
    },
  ],
  oportunidades: [
    {
      categoria: 'produto',
      prioridade: 'media',
      mensagem: "O produto 'Officia (ID 724)' apresenta lucro acima da média e faturamento abaixo da média, indicando possível espaço para crescimento.",
    },
  ],
  principais_insights: [
    {
      tipo: 'atencao',
      categoria: 'crescimento',
      prioridade: 'alta',
      mensagem: 'A maior queda mensal ocorreu em 2016-11, com redução de 30.23%.',
    },
  ],
}
