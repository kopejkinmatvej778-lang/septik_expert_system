from pathlib import Path

from septik_kp_bot.catalog import build_payload, load_catalog
from septik_kp_bot.renderer import render_proposal_png


BASE_DIR = Path(__file__).resolve().parent


def main() -> None:
    catalog = load_catalog(BASE_DIR / "assets" / "price-catalog.json")
    ai_payload = {
        "client": {
            "name": "Тест",
            "address": "Нагаево",
            "phone": "+79990000000",
            "date": "2026-08-14",
        },
        "materials": [
            {"catalog_item_id": "station_aerolos_bio_4", "quantity": "1", "price_kind": "money"},
            {"catalog_item_id": "pipe_pvc_110", "quantity": "8", "price_kind": "money"},
        ],
        "works": [
            {"catalog_item_id": "station_installation", "quantity": "1", "price_kind": "money"},
        ],
        "missing_data": [],
        "flags": {"preliminary": True},
    }
    payload, warnings = build_payload(ai_payload, catalog)
    result = render_proposal_png(
        payload,
        BASE_DIR / "assets" / "septik-expert-kp-template-blank.png",
        BASE_DIR / "storage" / "rendered" / "smoke-test.png",
    )
    print({"warnings": warnings, "render": result})


if __name__ == "__main__":
    main()
