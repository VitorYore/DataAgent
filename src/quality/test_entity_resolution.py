import json
import unittest
from unittest.mock import patch
from difflib import SequenceMatcher

import pandas as pd
from pandas.testing import assert_frame_equal
from src.quality.entity_resolution import detectar_entidades, normalizar_entidade, _pares, VIZINHOS_FUZZY
from src.analytics.customers import analisar_clientes
from src.analytics.products import analisar_produtos


class EntityResolutionTests(unittest.TestCase):
    def test_normalization(self):
        self.assertEqual(normalizar_entidade(" MINERAÇÃO  CAIEIRAS "), "mineracao caieiras")
        self.assertEqual(normalizar_entidade("Empresa ABC"), normalizar_entidade("EMPRESA ABC"))

    def test_positive_reasons_preserve_dataframe_and_analytics(self):
        for a, b, reason in [
            ("MINERAÇÃO CAIEIRAS", "MINERAÇAO CAIEIRAS", "diferenca_acentuacao"),
            ("MINERAÇÃO CAIEIRAS", "MINERACAO CAIEIRAS", "diferenca_acentuacao"),
            ("SUPERMERCADO X", " SUPERMERCADO X ", "diferenca_espacamento"),
            ("SUPERMERCADO X", "SUPERMERCADO  X", "diferenca_espacamento"),
            ("Empresa ABC", "EMPRESA ABC", "diferenca_caixa"),
        ]:
            with self.subTest(a=a, b=b):
                df = pd.DataFrame({"Cliente": [a, b], "Valor_Total": [100, 50]})
                df.attrs["audit"] = {"original": True}
                original, customers = df.copy(deep=True), analisar_clientes(df)
                report = detectar_entidades(df)
                self.assertEqual(len(report["candidates"]), 1)
                self.assertIn(reason, report["candidates"][0]["reasons"])
                assert_frame_equal(df, original)
                self.assertEqual(df.attrs, original.attrs)
                self.assertEqual(analisar_clientes(df), customers)

    def test_fuzzy_long_typo(self):
        candidate = detectar_entidades(pd.DataFrame({"Cliente": [
            "Distribuidora Oliveira", "Distribuidora Oliviera"]}))["candidates"][0]
        self.assertIn("grafia_muito_semelhante", candidate["reasons"])
        self.assertGreaterEqual(candidate["similarity"], .92)
        self.assertLessEqual(candidate["similarity"], 1)

    def test_false_positives_and_short_names(self):
        for a, b in [("EMPRESA ALFA", "EMPRESA BETA"), ("JOAO SILVA", "JOSE SILVA"),
                     ("ABC", "ABD"), ("XP", "XX"), ("A", "B"),
                     ("PRODUTO 100", "PRODUTO 101"), ("MERCADO CENTRAL", "FARMACIA CENTRAL"),
                     ("Empresa ABC LTDA", "Empresa ABC SA"),
                     ("3 SARRAFOS 10 CM", "3 SARRAFOS 10 M"),
                     ("Produto especial 1 23", "Produto especial 12 3"),
                     ("Distribuidora Oliveira LTDA", "Distribuidora Oliveira ME")]:
            with self.subTest(a=a):
                self.assertEqual(detectar_entidades(pd.DataFrame({"Cliente": [a, b]}))["candidates"], [])

    def test_stable_client_id_has_priority(self):
        df = pd.DataFrame({"Cliente_ID": [123, 123, 456], "Cliente": ["Nome A", "Nome B", "NOME A"],
                           "Faturamento": [100, 50, 20]})
        self.assertEqual(detectar_entidades(df)["candidates"], [])
        self.assertEqual(analisar_clientes(df)["quantidade_clientes"], 2)

    def test_stable_product_and_category_ids(self):
        df = pd.DataFrame({"Produto_ID": [1, 1], "Produto": ["Papel", "PAPEL"],
                           "Categoria_ID": [2, 2], "Categoria": ["Material", "MATERIAL"],
                           "Faturamento": [100, 50]})
        self.assertEqual(detectar_entidades(df)["candidates"], [])
        self.assertEqual(analisar_produtos(df)["quantidade_produtos"], 1)

    def test_shared_detector_for_products_categories_stores(self):
        for kind, column in [("produto", "Produto"), ("categoria", "Categoria"), ("loja", "Loja")]:
            with self.subTest(kind=kind):
                df = pd.DataFrame({column: ["Material Azul", "MATERIAL AZUL"]})
                self.assertEqual(detectar_entidades(df)["candidates"][0]["entity_type"], kind)

    def test_context_preserves_concept_orders_and_nulls(self):
        df = pd.DataFrame({"Cliente": ["Empresa ABC", "EMPRESA ABC", "Empresa ABC"],
                           "Pedido": [1, 2, 1], "Valor_Total": [100, 50, None]})
        c = detectar_entidades(df)["candidates"][0]
        self.assertEqual(c["metric"]["concept"], "valor_total")
        self.assertEqual(c["left"]["records"], 2)
        self.assertEqual(c["left"]["orders"], 1)
        self.assertEqual(c["combined_preview"], 150)
        self.assertEqual(c["right"]["metric_value"], 50)

    def test_without_metric_and_with_null_names(self):
        df = pd.DataFrame({"Cliente": [None, "", "  ", "Empresa ABC", "EMPRESA ABC"]})
        r = detectar_entidades(df)
        self.assertEqual(len(r["candidates"]), 1)
        self.assertIsNone(r["candidates"][0]["metric"])
        self.assertIsNone(r["candidates"][0]["combined_preview"])
        json.dumps(r, allow_nan=False)

    def test_unrelated_text_columns_are_not_scanned(self):
        df = pd.DataFrame({c: ["Empresa ABC", "EMPRESA ABC"] for c in [
            "Status", "Forma_pagamento", "Mes", "Observacao", "Canal_venda"]})
        self.assertEqual(detectar_entidades(df)["candidates"], [])

    def test_textual_metric_does_not_break_detection(self):
        df = pd.DataFrame({"Cliente": ["Empresa ABC", "EMPRESA ABC"], "Faturamento": ["pendente", "indefinido"]})
        self.assertIsNone(detectar_entidades(df)["candidates"][0]["metric"])

    def test_fuzzy_work_is_bounded_and_measured(self):
        names = ["Distribuidora " + chr(97 + i // 26) + chr(97 + i % 26) for i in range(500)]
        stats = {"blocked_pairs": 0, "fuzzy_comparisons": 0}
        with patch("src.quality.entity_resolution.SequenceMatcher", wraps=SequenceMatcher) as compare:
            list(_pares(names, stats))
            self.assertLessEqual(compare.call_count, len(names) * VIZINHOS_FUZZY)
            self.assertEqual(compare.call_count, stats["fuzzy_comparisons"])

    def test_candidate_cap_retains_total_counts(self):
        df = pd.DataFrame({"Cliente": ["EMPRESA ABC", "Empresa ABC", "empresa abc"]})
        with patch("src.quality.entity_resolution.LIMITE_CANDIDATOS", 1):
            r = detectar_entidades(df)
        self.assertEqual(len(r["candidates"]), 1)
        self.assertEqual(r["total_candidates"], 2)
        self.assertTrue(r["truncated"])

    def test_duplicate_index_does_not_multiply_metric_context(self):
        df = pd.DataFrame({"Cliente": ["Empresa ABC", "EMPRESA ABC"], "Valor_Total": [100, 50]}, index=[0, 0])
        original = df.copy()
        self.assertEqual(detectar_entidades(df)["candidates"][0]["combined_preview"], 150)
        assert_frame_equal(df, original)

    def test_unused_categorical_values_are_not_entities(self):
        df = pd.DataFrame({"Cliente": pd.Categorical(["Empresa ABC"], categories=["Empresa ABC", "EMPRESA ABC"])})
        self.assertEqual(detectar_entidades(df)["candidates"], [])
