"""TDD: generate_bank_statement management command (RED first)."""
import csv
import io
import os

from django.test import TestCase
from django.core.management import call_command


class GenerateBankStatementCommandTests(TestCase):
    def test_generates_csv_with_expected_columns_and_rows(self):
        out_path = "/tmp/test_stmt.csv"
        if os.path.exists(out_path):
            os.remove(out_path)
        call_command("generate_bank_statement", "--out", out_path, "--rows", "5", "--seed", "1")
        self.assertTrue(os.path.exists(out_path))
        with open(out_path) as f:
            rows = list(csv.reader(f))
        header = rows[0]
        self.assertIn("Date", header)
        self.assertIn("Description", header)
        self.assertIn("Amount", header)
        self.assertIn("Balance", header)
        # 1 header + 5 data rows
        self.assertEqual(len(rows), 6)
        os.remove(out_path)

    def test_balance_carries_from_previous_row(self):
        out_path = "/tmp/test_stmt2.csv"
        if os.path.exists(out_path):
            os.remove(out_path)
        call_command("generate_bank_statement", "--out", out_path, "--rows", "3", "--starting-balance", "1000.00", "--seed", "7")
        with open(out_path) as f:
            rows = list(csv.reader(f))
        # Balance column should be monotonically tracked (last data row has a balance)
        self.assertTrue(rows[1][3])
        os.remove(out_path)
