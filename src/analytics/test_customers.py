import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

import pandas as pd

from src.analytics.customers import analisar_clientes
from src.reports.executive_summary import gerar_resumo_clientes


class CustomerAnalysisTests(unittest.TestCase):
    def setUp(self):
        self.data = pd.DataFrame({
            "Cliente_ID": [123, 123, 456, 789],
            "Cliente": ["Mesmo Nome", "Mesmo Nome", "Mesmo Nome", "Outro"],
            "Faturamento": [300.0, 100.0, 200.0, 100.0],
            "Lucro": [-100.0, 200.0, 200.0, -20.0],
        })

    def test_rankings_group_by_id_and_match_other_metric(self):
        result = analisar_clientes(self.data)
        self.assertEqual(result["quantidade_clientes"], 3)
        revenue = result["ranking_faturamento"]
        profit = result["ranking_lucro"]
        self.assertEqual([row["cliente_id"] for row in revenue], ["123", "456", "789"])
        self.assertEqual([row["cliente_id"] for row in profit], ["456", "123", "789"])
        self.assertEqual(revenue[0], {
            "posicao": 1, "cliente": "Mesmo Nome (ID 123)", "cliente_id": "123",
            "faturamento": 400.0, "lucro": 100.0,
        })
        self.assertEqual(revenue[1]["cliente"], "Mesmo Nome (ID 456)")
        self.assertEqual(profit[0]["faturamento"], 200.0)
        self.assertEqual(result["participacao_maior_cliente"], 57.14)
        self.assertEqual(result["concentracao_top_5"], 100.0)
        # Duas linhas negativas, mas somente um cliente com lucro agregado negativo.
        self.assertEqual(result["clientes_resultado_negativo"], 1)
        self.assertEqual(len(result["clientes_com_prejuizo"]), 1)
        self.assertEqual(len(result["insights_clientes"]), 4)
        self.assertEqual(len(set(result["insights_clientes"])), 4)
        self.assertIn("57,14%", result["insights_clientes"][1])

    def test_revenue_without_profit_and_without_id(self):
        result = analisar_clientes(self.data.drop(columns=["Lucro", "Cliente_ID"]))
        self.assertTrue(result["ranking_faturamento"])
        self.assertTrue(all(row["lucro"] is None for row in result["ranking_faturamento"]))
        self.assertTrue(all(row["cliente_id"] is None for row in result["ranking_faturamento"]))
        self.assertEqual(result["ranking_lucro"], [])
        self.assertIsNone(result["clientes_resultado_negativo"])
        self.assertEqual(len(result["insights_clientes"]), 2)

    def test_profit_without_revenue(self):
        result = analisar_clientes(self.data.drop(columns=["Faturamento"]))
        self.assertEqual(result["ranking_faturamento"], [])
        self.assertTrue(result["ranking_lucro"])
        self.assertTrue(all(row["faturamento"] is None for row in result["ranking_lucro"]))
        self.assertIsNone(result["participacao_maior_cliente"])
        self.assertEqual(result["clientes_resultado_negativo"], 1)

    def test_participation_uses_total_revenue_even_without_customer_id(self):
        data = pd.concat([self.data, pd.DataFrame({
            "Cliente_ID": [None], "Cliente": [None],
            "Faturamento": [300.0], "Lucro": [None],
        })], ignore_index=True)
        result = analisar_clientes(data)
        self.assertEqual(result["participacao_maior_cliente"], 40.0)
        self.assertEqual(result["concentracao_top_5"], 70.0)
        self.assertEqual(result["quantidade_clientes"], 3)

    def test_top_ten_limits_and_top_five_unchanged(self):
        data = pd.DataFrame({
            "Cliente_ID": range(1, 13),
            "Faturamento": range(1, 13),
            "Lucro": range(12, 0, -1),
        })
        result = analisar_clientes(data)
        self.assertEqual(len(result["ranking_faturamento"]), 10)
        self.assertEqual(len(result["ranking_lucro"]), 10)
        self.assertEqual([row["posicao"] for row in result["ranking_faturamento"]], list(range(1, 11)))
        self.assertEqual(result["ranking_faturamento"][0]["cliente_id"], "12")
        self.assertEqual(result["ranking_lucro"][0]["cliente_id"], "1")
        self.assertEqual(result["concentracao_top_5"], round(50 / 78 * 100, 2))
        self.assertEqual(result["participacao_maior_cliente"], round(12 / 78 * 100, 2))
        self.assertEqual(result["clientes_resultado_negativo"], 0)

    def test_zero_revenue_and_unavailable_values(self):
        data = self.data.copy()
        data["Faturamento"] = 0.0
        self.assertIsNone(analisar_clientes(data)["participacao_maior_cliente"])
        data["Faturamento"] = float("nan")
        data["Lucro"] = float("nan")
        result = analisar_clientes(data)
        self.assertEqual(result["ranking_faturamento"], [])
        self.assertEqual(result["ranking_lucro"], [])
        self.assertIsNone(result["clientes_resultado_negativo"])
        self.assertIsNone(result["participacao_maior_cliente"])
        self.assertEqual(result["insights_clientes"], [])
        data = self.data.copy()
        data.loc[data.Cliente_ID == 456, "Lucro"] = float("nan")
        row = analisar_clientes(data)["ranking_faturamento"][1]
        self.assertIsNone(row["lucro"])

    def test_summary_preserves_old_fields_and_accepts_old_analysis(self):
        analysis = analisar_clientes(self.data)
        summary = gerar_resumo_clientes(analysis)
        for field in ["ranking_faturamento", "ranking_lucro", "participacao_maior_cliente", "clientes_resultado_negativo", "insights_clientes"]:
            self.assertEqual(summary[field], analysis[field])
        self.assertEqual(summary["cliente_maior_faturamento"]["faturamento"], 400.0)
        self.assertEqual(summary["cliente_maior_lucro"]["lucro"], 200.0)
        old = gerar_resumo_clientes({"quantidade_clientes": 2, "concentracao_top_5": 100})
        self.assertEqual(old["ranking_faturamento"], [])
        self.assertEqual(old["insights_clientes"], [])
        self.assertIsNone(old["clientes_resultado_negativo"])

    def test_no_customer_is_safe_in_full_pipeline(self):
        from main import executar_dataagent
        data = self.data.drop(columns=["Cliente", "Cliente_ID"])
        data["data"] = ["2025-01-15", "2025-02-15", "2025-03-15", "2025-04-15"]
        result = analisar_clientes(data)
        self.assertIn("erro", result)
        self.assertEqual(gerar_resumo_clientes(result), {})
        with tempfile.TemporaryDirectory() as directory, redirect_stdout(io.StringIO()):
            root = Path(directory)
            inputs = root / "input"
            inputs.mkdir()
            data.to_csv(inputs / "vendas.csv", index=False)
            summary = executar_dataagent(inputs, root / "output", estrito=True)
        self.assertEqual(summary["clientes"], {})


if __name__ == "__main__":
    unittest.main()
