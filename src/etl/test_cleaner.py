import unittest

import pandas as pd

from src.etl.cleaner import converter_colunas_numericas
from src.etl.transformation_log import TransformationLog


class NumericCleanerTests(unittest.TestCase):
    def test_converts_high_confidence_column_and_audits_invalid_values(self):
        frame = pd.DataFrame({'amount': [str(index + 0.25) for index in range(99)] + ['observa??o']})
        log = TransformationLog()
        result = converter_colunas_numericas(frame, ['amount'], log)
        self.assertTrue(pd.api.types.is_numeric_dtype(result['amount']))
        self.assertEqual(int(result['amount'].isna().sum()), 1)
        self.assertTrue(any(item['tipo_transformacao'] == 'conversao_numerica_parcial' for item in log.obter_logs()))
        self.assertEqual(frame.loc[99, 'amount'], 'observa??o')

    def test_keeps_low_confidence_mixed_column_unchanged(self):
        frame = pd.DataFrame({'amount': ['1', '2', 'texto', 'outro']})
        log = TransformationLog()
        result = converter_colunas_numericas(frame, ['amount'], log)
        self.assertEqual(result['amount'].tolist(), frame['amount'].tolist())
        self.assertTrue(any(item['tipo_transformacao'] == 'conversao_numerica_cancelada' for item in log.obter_logs()))


if __name__ == '__main__':
    unittest.main()
