import unittest

from septik_kp_bot.deal_task_agent import (
    active_task_lead_ids,
    build_deal_analysis,
    leads_without_active_tasks,
)


class DealTaskAgentTest(unittest.TestCase):
    def test_selects_only_open_leads_without_active_tasks(self):
        leads = [
            {"id": 1, "status_id": 123},
            {"id": 2, "status_id": 123},
            {"id": 3, "status_id": 142},
        ]
        tasks = [
            {"entity_id": 1, "entity_type": "leads", "is_completed": False},
            {"entity_id": 4, "entity_type": "leads", "is_completed": False},
            {"entity_id": 2, "entity_type": "leads", "is_completed": True},
        ]

        self.assertEqual(active_task_lead_ids(tasks), {1, 4})
        self.assertEqual([lead["id"] for lead in leads_without_active_tasks(leads, tasks)], [2])

    def test_builds_next_step_for_proposal_follow_up(self):
        card = {
            "lead": {
                "id": 42,
                "name": "КП Иван Нагаево",
                "responsible_user_id": 7,
                "price": 250000,
                "updated_at": 1786812000,
            },
            "contacts": [
                {
                    "name": "Иван",
                    "custom_fields_values": [
                        {
                            "field_code": "PHONE",
                            "values": [{"value": "+79990000000"}],
                        }
                    ],
                }
            ],
            "notes": [
                {
                    "params": {
                        "text": "КП PNG сформировано в Telegram-боте. Клиент получил коммерческое предложение."
                    }
                }
            ],
        }

        analysis = build_deal_analysis(card, {7: "Алия"}, "https://example.amocrm.ru")

        self.assertEqual(analysis["lead_id"], "42")
        self.assertIn("Связаться с клиентом по отправленному КП", analysis["task_text"])
        self.assertIn("+79990000000", analysis["task_text"])
        self.assertIn("https://example.amocrm.ru/leads/detail/42", analysis["report_line"])


if __name__ == "__main__":
    unittest.main()
