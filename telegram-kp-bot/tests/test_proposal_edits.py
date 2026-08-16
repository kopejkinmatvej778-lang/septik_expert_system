from pathlib import Path
import unittest

from septik_kp_bot.catalog import build_payload, load_catalog
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

    def payload_with_ring(self):
        payload = self.base_payload()
        payload["materials"].append({"catalog_item_id": "jbi_ring_d_1_5", "quantity": "2", "price_kind": "money"})
        return payload

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

    def test_adds_jbi_delivery_from_short_phrase(self):
        payload, warnings = apply_human_correction_rules(
            self.base_payload(),
            self.catalog,
            "добавь доставку ЖБИ",
        )

        delivery = next(row for row in payload["works"] if row.get("catalog_item_id") == "jbi_delivery")
        self.assertEqual(delivery["quantity"], "1")
        self.assertIn("add_or_update_line", warnings[0]["rules"])

    def test_removes_installation_line(self):
        payload, warnings = apply_human_correction_rules(
            self.base_payload(),
            self.catalog,
            "убери монтаж",
        )

        self.assertEqual(payload["works"], [])
        self.assertIn("remove_item", warnings[0]["rules"])
        self.assertEqual(warnings[0]["edits"][0]["type"], "remove_item")

    def test_replaces_station_with_catalog_item(self):
        payload, warnings = apply_human_correction_rules(
            self.base_payload(),
            self.catalog,
            "замени станцию на Про 4",
        )

        station = payload["materials"][0]
        self.assertEqual(station["catalog_item_id"], "station_aerolos_pro_4")
        self.assertEqual(station["quantity"], "1")
        self.assertIn("replace_item", warnings[0]["rules"])

    def test_ring_two_meters_becomes_missing_price_request(self):
        payload, warnings = apply_human_correction_rules(
            self.payload_with_ring(),
            self.catalog,
            "кольца 2 метра",
        )

        ring = payload["materials"][1]
        self.assertEqual(ring["catalog_item_id"], "")
        self.assertEqual(ring["name"], "ЖБИ кольцо D = 2 м")
        self.assertEqual(ring["quantity"], "2")
        self.assertIn("change_attribute", warnings[0]["rules"])

        _, build_warnings = build_payload(payload, self.catalog)
        missing_price = [warning for warning in build_warnings if warning.get("type") == "missing_price_request"]
        self.assertEqual(missing_price[0]["item_name"], "ЖБИ кольцо D = 2 м")
        self.assertTrue(missing_price[0]["blocking"])

    def test_global_percent_discount_as_negative_line(self):
        payload, warnings = apply_human_correction_rules(
            self.base_payload(),
            self.catalog,
            "скидка 10%",
        )

        discount_rows = [row for row in payload["works"] if row.get("note") == "manual_global_discount"]
        self.assertEqual(len(discount_rows), 1)
        self.assertEqual(discount_rows[0]["manual_unit_price"], -19500)
        self.assertIn("discount", warnings[0]["rules"])


if __name__ == "__main__":
    unittest.main()
