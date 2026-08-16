import types
import unittest

from septik_kp_bot.integrations import resolve_or_create_lead_for_proposal


class FakeAmoClient:
    def __init__(self):
        self.settings = types.SimpleNamespace(amocrm_base_url="https://example.amocrm.ru")
        self.created_contacts = []
        self.created_leads = []

    async def find_leads_by_phone(self, phone, limit=10):
        return []

    async def find_contacts(self, query, limit=10):
        return []

    async def find_leads_by_name(self, name, limit=10):
        return []

    async def add_contact(self, name, phone=""):
        self.created_contacts.append({"name": name, "phone": phone})
        return {"id": 1001, "name": name}

    async def add_lead(self, name, price=0, contact_id=None, source="Telegram bot"):
        self.created_leads.append({"name": name, "price": price, "contact_id": contact_id, "source": source})
        return {"id": 2002, "name": name, "price": price}


class AmoCrmLinkingTest(unittest.IsolatedAsyncioTestCase):
    async def test_creates_contact_and_lead_with_proposal_amount(self):
        client = FakeAmoClient()
        record = {
            "payload": {
                "client": {
                    "name": "Иван",
                    "phone": "+79990000000",
                    "address": "Нагаево",
                },
                "materials": [{"name": "Станция АЭРОЛОС БИО 4"}],
                "totals": {"grand_total": 250000},
            }
        }

        result = await resolve_or_create_lead_for_proposal(client, record)

        self.assertEqual(result["status"], "created_contact_and_lead")
        self.assertEqual(result["lead_id"], "2002")
        self.assertEqual(client.created_contacts[0]["phone"], "+79990000000")
        self.assertEqual(client.created_leads[0]["price"], 250000)
        self.assertEqual(client.created_leads[0]["contact_id"], 1001)


if __name__ == "__main__":
    unittest.main()
