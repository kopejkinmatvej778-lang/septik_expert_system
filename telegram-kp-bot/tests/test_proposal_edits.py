from pathlib import Path
import unittest

from septik_kp_bot.catalog import load_catalog
from septik_kp_bot.proposal_edits import apply_human_correction_rules


BASE_DIR = Path(__file__).resolve().parents[1]


class ProposalEditRulesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.catalog = load_catalog(BASE_DIR / "assets" / "price-catalog.json")

    def base_payload(self):
        return {
            "client": {
                "name": "Тест",
                "address": "Нагаево",
                "phone": "+79990000000",
                "date": "2026-08-14",
            },
            "materials": [
                {"catalog_item_id": "station_aerolos_bio_4", "quantity": "1", "price_kind": "money"},
            ],
            "works": [
                {"catalog_item_id": "station_installation", "quantity": "1", "price_kind": "money"},
            ],
            "missing_data": [],
            "flags": {"preliminary": True},
        }

    def test_applies_manual_price_to_existing_line(self):
        payload, warnings = apply_human_correction_rules(
            self.base_payload(),
            self.catalog,
            "поставь монтаж станции по 35000",
        )

        installation = payload["works"][0]
        self.assertEqual(installation["catalog_item_id"], "station_installation")
        self.assertEqual(installation["manual_unit_price"], 35000)
        self.assertEqual(installation["price_kind"], "money")
        self.assertEqual(warnings[0]["rules"], ["manual_price"])

    def test_applies_target_percent_discount_to_line(self):
        payload, warnings = apply_human_correction_rules(
            self.base_payload(),
            self.catalog,
            "скидка на монтаж станции 10%",
        )

        installation = payload["works"][0]
        self.assertEqual(installation["manual_unit_price"], 27000)
        self.assertIn("discount", warnings[0]["rules"])

    def test_applies_global_money_discount_as_negative_line(self):
        payload, warnings = apply_human_correction_rules(
            self.base_payload(),
            self.catalog,
            "сделай скидку 15000",
        )

        discount_rows = [row for row in payload["works"] if row.get("note") == "manual_global_discount"]
        self.assertEqual(len(discount_rows), 1)
        self.assertEqual(discount_rows[0]["manual_unit_price"], -15000)
        self.assertEqual(discount_rows[0]["name"], "Скидка")
        self.assertIn("discount", warnings[0]["rules"])

    def test_adds_catalog_line_with_quantity_and_manual_price(self):
        payload, warnings = apply_human_correction_rules(
            self.base_payload(),
            self.catalog,
            "добавь труба ПВХ 110 8 м по 600",
        )

        pipe = next(row for row in payload["materials"] if row.get("catalog_item_id") == "pipe_pvc_110")
        self.assertEqual(pipe["quantity"], "8")
        self.assertEqual(pipe["manual_unit_price"], 600)
        self.assertIn("add_or_update_line", warnings[0]["rules"])


if __name__ == "__main__":
    unittest.main()
