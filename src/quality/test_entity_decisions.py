import unittest
import pandas as pd
from pandas.testing import assert_frame_equal
from src.quality.entity_resolution import detectar_entidades
from src.quality.entity_decisions import preparar_revisao, registrar_decisao, aplicar_aliases
from src.analytics.customers import analisar_clientes
from src.analytics.products import analisar_produtos


class EntityDecisionTests(unittest.TestCase):
    def report(self, df, identifier="analysis-a"):
        return preparar_revisao(detectar_entidades(df), identifier, df)

    def test_merge_preserves_original_and_sums(self):
        df = pd.DataFrame({"Cliente": ["Empresa ABC", "EMPRESA ABC"], "Valor_Total": [100, 50]})
        original = df.copy()
        report = self.report(df)
        decision = {"candidate_id": report["candidates"][0]["candidate_id"], "decision": "merge"}
        result = registrar_decisao(df, report, decision)
        analytic = aplicar_aliases(df, result)
        self.assertEqual(analisar_clientes(analytic)["quantidade_clientes"], 1)
        self.assertEqual(analisar_clientes(analytic)["maior_valor_total"]["valor"], 150)
        self.assertEqual(result["summary"]["cliente"], {"total": 1, "pending": 0, "merged": 1, "kept_separate": 0})
        assert_frame_equal(df, original)
        self.assertEqual(report["candidates"][0]["status"], "pending")

    def test_keep_separate_is_persistent_and_idempotent(self):
        df = pd.DataFrame({"Cliente": ["Empresa ABC", "EMPRESA ABC"], "Valor_Total": [100, 50]})
        report = self.report(df)
        payload = {"candidate_id": report["candidates"][0]["candidate_id"], "decision": "keep_separate"}
        result = registrar_decisao(df, report, payload)
        assert_frame_equal(aplicar_aliases(df, result), df)
        self.assertEqual(result, registrar_decisao(df, result, payload))
        self.assertEqual(result["candidates"][0]["status"], "kept_separate")
        self.assertEqual(len(result["decisions"]), 1)

    def test_label_by_frequency_then_first_encounter_even_for_fuzzy_order(self):
        for labels, expected in [
            (["Empresa ABC"] * 5 + ["EMPRESA ABC"] * 20, "EMPRESA ABC"),
            (["Distribuidora Oliviera"] * 10 + ["Distribuidora Oliveira"] * 10, "Distribuidora Oliviera"),
        ]:
            df = pd.DataFrame({"Cliente": labels})
            c = self.report(df)["candidates"][0]
            self.assertEqual(c["recommended_value"], expected)

    def test_candidate_id_is_stable_scoped_and_not_list_position(self):
        df = pd.DataFrame({"Cliente": ["Empresa ABC", "EMPRESA ABC"]})
        a = self.report(df)
        b = self.report(df.iloc[::-1])
        self.assertEqual(a["candidates"][0]["candidate_id"], b["candidates"][0]["candidate_id"])
        self.assertNotEqual(a["candidates"][0]["candidate_id"], self.report(df, "analysis-b")["candidates"][0]["candidate_id"])

    def test_overlapping_merge_and_decision_changes_are_rejected(self):
        df = pd.DataFrame({"Cliente": ["Empresa ABC", "EMPRESA ABC", "empresa abc"]})
        report = self.report(df)
        a, b = report["candidates"]
        merged = registrar_decisao(df, report, {"candidate_id": a["candidate_id"], "decision": "merge"})
        with self.assertRaisesRegex(ValueError, "sobrepostas"):
            registrar_decisao(df, merged, {"candidate_id": b["candidate_id"], "decision": "merge"})
        with self.assertRaisesRegex(ValueError, "Alterar"):
            registrar_decisao(df, merged, {"candidate_id": a["candidate_id"], "decision": "keep_separate"})
        same = registrar_decisao(df, merged, {"candidate_id": a["candidate_id"], "decision": "merge"})
        self.assertEqual(same, merged)

    def test_product_uses_same_alias_logic(self):
        df = pd.DataFrame({"Produto": ["Papel Azul", "PAPEL AZUL"], "Faturamento": [100, 50]})
        r = self.report(df)
        r = registrar_decisao(df, r, {"candidate_id": r["candidates"][0]["candidate_id"], "decision": "merge"})
        self.assertEqual(analisar_produtos(aplicar_aliases(df, r))["quantidade_produtos"], 1)
        self.assertEqual(df["Produto"].nunique(), 2)

    def test_missing_entities_column_and_arbitrary_canonical_rejected(self):
        df = pd.DataFrame({"Cliente": ["Empresa ABC", "EMPRESA ABC"]})
        r = self.report(df)
        payload = {"candidate_id": r["candidates"][0]["candidate_id"], "decision": "merge"}
        for changed in [df.iloc[:1], df.rename(columns={"Cliente": "Outro"})]:
            with self.assertRaises(ValueError):
                registrar_decisao(changed, r, payload)
        with self.assertRaises(ValueError):
            registrar_decisao(df, r, {**payload, "canonical_value": "inexistente"})
        with self.assertRaises(ValueError):
            registrar_decisao(df, r, {**payload, "left": "inexistente"})
