#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY, TA_LEFT, TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import BaseDocTemplate, Frame, PageBreak, PageTemplate, Paragraph, Spacer, Table, TableStyle


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def checksum(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def find_font(candidates: list[str]) -> str:
    for candidate in candidates:
        if Path(candidate).exists():
            return candidate
    raise FileNotFoundError("No suitable TTF font found. Pass --font-regular and --font-bold.")


def register_fonts(font_regular: str | None, font_bold: str | None) -> tuple[str, str]:
    regular = font_regular or find_font(
        [
            "/System/Library/Fonts/Supplemental/Times New Roman.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSerif.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSerif-Regular.ttf",
        ]
    )
    bold = font_bold or find_font(
        [
            "/System/Library/Fonts/Supplemental/Times New Roman Bold.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSerif-Bold.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSerif-Bold.ttf",
        ]
    )
    pdfmetrics.registerFont(TTFont("ContractSerif", regular))
    pdfmetrics.registerFont(TTFont("ContractSerif-Bold", bold))
    return "ContractSerif", "ContractSerif-Bold"


def esc(text: Any) -> str:
    return str(text if text is not None else "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def money(value: Any) -> str:
    if value in (None, ""):
        return "0,00 р."
    if isinstance(value, str):
        return value
    return f"{int(value):,}".replace(",", " ") + ",00 р."


def short_name(full_name: str) -> str:
    parts = [part for part in str(full_name).split() if part]
    if len(parts) < 2:
        return full_name
    initials = "".join(f"{part[0]}." for part in parts[1:] if part)
    return f"{parts[0]} {initials}".strip()


def line(label: str, value: Any) -> str:
    value = str(value or "").strip()
    return f"{label}: {value}" if value else ""


def join_html_lines(lines: list[str]) -> str:
    return "<br/>".join(esc(item) for item in lines if str(item or "").strip())


def normalize_rows(rows: list[dict[str, Any]]) -> list[list[str]]:
    normalized = []
    for idx, row in enumerate(rows, start=1):
        normalized.append(
            [
                str(row.get("number") or idx),
                str(row.get("name") or ""),
                str(row.get("unit") or ""),
                str(row.get("quantity") or ""),
                str(row.get("display_unit_price") or money(row.get("unit_price"))),
                str(row.get("display_total") or money(row.get("total"))),
            ]
        )
    return normalized


class ContractPdfRenderer:
    def __init__(self, data: dict[str, Any], output: Path, font_regular: str | None = None, font_bold: str | None = None):
        self.data = data.get("contract_data", data)
        self.output = output
        self.font_regular, self.font_bold = register_fonts(font_regular, font_bold)
        self.styles = self._build_styles()

    def _build_styles(self):
        styles = getSampleStyleSheet()
        styles.add(ParagraphStyle("TitleRus", parent=styles["Normal"], fontName=self.font_bold, fontSize=13, leading=15, alignment=TA_CENTER, spaceAfter=9))
        styles.add(ParagraphStyle("BodyRus", parent=styles["Normal"], fontName=self.font_regular, fontSize=10.4, leading=12.7, alignment=TA_JUSTIFY, firstLineIndent=8 * mm, spaceAfter=3.5))
        styles.add(ParagraphStyle("BodyNoIndent", parent=styles["BodyRus"], firstLineIndent=0))
        styles.add(ParagraphStyle("Section", parent=styles["Normal"], fontName=self.font_bold, fontSize=11.5, leading=14, alignment=TA_CENTER, spaceBefore=7, spaceAfter=5))
        styles.add(ParagraphStyle("TableText", parent=styles["Normal"], fontName=self.font_regular, fontSize=8.0, leading=9.5, alignment=TA_LEFT))
        styles.add(ParagraphStyle("TableCenter", parent=styles["TableText"], alignment=TA_CENTER))
        styles.add(ParagraphStyle("TableRight", parent=styles["TableText"], alignment=TA_RIGHT))
        styles.add(ParagraphStyle("TableHead", parent=styles["TableText"], fontName=self.font_bold, alignment=TA_CENTER))
        styles.add(ParagraphStyle("Sign", parent=styles["Normal"], fontName=self.font_regular, fontSize=9.0, leading=10.5, alignment=TA_LEFT))
        return styles

    def p(self, text: Any, style: str = "BodyRus") -> Paragraph:
        return Paragraph(esc(text), self.styles[style])

    def p_html(self, text: str, style: str = "BodyRus") -> Paragraph:
        return Paragraph(text, self.styles[style])

    def cell(self, text: Any, style: str = "TableText") -> Paragraph:
        return Paragraph(esc(text), self.styles[style])

    def make_section_table(self, title: str, rows: list[list[str]], total: Any) -> Table:
        table_rows = [[self.cell(title, "TableHead"), "", "", "", "", ""]]
        table_rows.append(
            [
                self.cell("№", "TableHead"),
                self.cell("Наименование", "TableHead"),
                self.cell("Ед. изм.", "TableHead"),
                self.cell("Кол-во", "TableHead"),
                self.cell("Цена за ед.", "TableHead"),
                self.cell("Сумма (руб.)", "TableHead"),
            ]
        )
        for row in rows:
            table_rows.append(
                [
                    self.cell(row[0], "TableCenter"),
                    self.cell(row[1]),
                    self.cell(row[2], "TableCenter"),
                    self.cell(row[3], "TableCenter"),
                    self.cell(row[4], "TableRight"),
                    self.cell(row[5], "TableRight"),
                ]
            )
        table_rows.append([self.cell("Итого:", "TableHead"), "", "", "", "", self.cell(money(total), "TableRight")])
        table = Table(table_rows, colWidths=[9 * mm, 73 * mm, 18 * mm, 17 * mm, 30 * mm, 33 * mm], repeatRows=2, splitByRow=1)
        table.setStyle(
            TableStyle(
                [
                    ("GRID", (0, 0), (-1, -1), 0.45, colors.black),
                    ("SPAN", (0, 0), (-1, 0)),
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#366092")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("BACKGROUND", (0, 1), (-1, 1), colors.HexColor("#E8EEF5")),
                    ("SPAN", (0, -1), (4, -1)),
                    ("ALIGN", (0, 0), (-1, 1), "CENTER"),
                    ("ALIGN", (0, 2), (0, -1), "CENTER"),
                    ("ALIGN", (2, 2), (3, -1), "CENTER"),
                    ("ALIGN", (4, 2), (5, -1), "RIGHT"),
                    ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 3.5),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 3.5),
                    ("TOPPADDING", (0, 0), (-1, -1), 3),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ]
            )
        )
        return table

    def buyer_text(self) -> tuple[str, str, str]:
        buyer = self.data.get("buyer", {})
        if buyer.get("type") == "company":
            company = buyer.get("company", {})
            full = company.get("full_name") or buyer.get("full_name") or ""
            short = company.get("short_name") or buyer.get("short_name") or full
            signer = company.get("signer_full_name") or ""
            basis = company.get("signer_basis") or "основании Устава"
            intro = f"{full}, именуемое в дальнейшем «Покупатель», в лице {signer}, действующего на {basis}"
            return full, short, intro
        full = buyer.get("full_name") or ""
        short = buyer.get("short_name") or short_name(full)
        return full, short, f"гражданин РФ {full}, именуемый в дальнейшем «Покупатель»"

    def seller_requisites_lines(self, seller: dict[str, Any], seller_short: str, seller_director_short: str) -> list[str]:
        requisites = seller.get("requisites", {})
        return [
            seller_short,
            requisites.get("legal_address") or requisites.get("address") or seller.get("address"),
            line("ИНН/КПП", " / ".join(part for part in [requisites.get("inn"), requisites.get("kpp")] if part)),
            line("ОГРН", requisites.get("ogrn")),
            line("р/с", requisites.get("settlement_account")),
            line("к/с", requisites.get("correspondent_account")),
            requisites.get("bank_name"),
            line("БИК", requisites.get("bik")),
            line("Телефон", requisites.get("phone") or seller.get("phone")),
            "",
            seller.get("director_position") or "Директор",
            "",
            f"__________________ / {seller_director_short}",
        ]

    def buyer_requisites_lines(self, buyer: dict[str, Any], object_address: str, buyer_full: str, buyer_short: str) -> list[str]:
        if buyer.get("type") == "company":
            company = buyer.get("company", {})
            return [
                company.get("short_name") or buyer_short,
                company.get("legal_address"),
                line("ИНН/КПП", " / ".join(part for part in [company.get("inn"), company.get("kpp")] if part)),
                line("ОГРН", company.get("ogrn")),
                line("ОКПО", company.get("okpo")),
                line("р/с", company.get("settlement_account")),
                line("к/с", company.get("correspondent_account")),
                company.get("bank_name"),
                line("БИК", company.get("bik")),
                line(company.get("signer_position") or "Подписант", company.get("signer_full_name")),
                line("Основание", company.get("signer_basis")),
                line("Контакт", company.get("contact_name")),
                line("Телефон", company.get("contact_phone") or buyer.get("phone")),
                line("Адрес монтажа/доставки", object_address),
                "",
                f"__________________ / {company.get('signer_short_name') or buyer_short}",
            ]

        passport = buyer.get("passport", {})
        passport_series = passport.get("passport_series") or buyer.get("passport_series")
        passport_number = passport.get("passport_number") or buyer.get("passport_number")
        passport_line = ""
        if passport_series or passport_number:
            passport_line = f"Паспорт: серия {passport_series or '____'} № {passport_number or '______'}"
        return [
            line("ФИО", buyer_full),
            passport_line,
            line("Выдан", passport.get("issued_by") or buyer.get("issued_by")),
            line("Дата выдачи", passport.get("issued_at") or buyer.get("issued_at")),
            line("Код подразделения", passport.get("department_code") or buyer.get("department_code")),
            line("Дата рождения", passport.get("birth_date") or buyer.get("birth_date")),
            line("Место рождения", passport.get("birth_place") or buyer.get("birth_place")),
            line("Прописка", passport.get("registration_address") or buyer.get("registration_address")),
            line("Адрес монтажа/доставки", object_address),
            line("Телефон", buyer.get("phone")),
            "",
            f"__________________ / {buyer_short}",
        ]

    def make_requisites_table(self, seller_lines: list[str], buyer_lines: list[str]) -> Table:
        table = Table(
            [
                [self.cell("Поставщик", "TableHead"), self.cell("Покупатель", "TableHead")],
                [
                    self.p_html(join_html_lines(seller_lines), "Sign"),
                    self.p_html(join_html_lines(buyer_lines), "Sign"),
                ],
            ],
            colWidths=[90 * mm, 90 * mm],
        )
        table.setStyle(
            TableStyle(
                [
                    ("GRID", (0, 0), (-1, -1), 0.45, colors.black),
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#F2F4F7")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 5),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ]
            )
        )
        return table

    def footer(self, canvas, doc):
        canvas.saveState()
        canvas.setFont(self.font_regular, 8)
        canvas.drawCentredString(A4[0] / 2, 10 * mm, str(doc.page))
        canvas.restoreState()

    def story(self) -> list[Any]:
        seller = self.data.get("seller", {})
        totals = self.data.get("totals", {})
        contract_number = self.data.get("contract_number") or "_____"
        contract_date_text = self.data.get("contract_date_text") or self.data.get("contract_date") or "________________"
        object_address = self.data.get("object_address") or "________________"
        seller_full = seller.get("full_name") or "Общество с ограниченной ответственностью «Септик Эксперт»"
        seller_short = seller.get("short_name") or "ООО «Септик Эксперт»"
        seller_director = seller.get("director") or "Копейкин Егор Дмитриевич"
        seller_director_short = seller.get("director_short") or "Копейкин Е.Д."
        seller_basis = seller.get("basis") or "Устава"
        buyer_full, buyer_short, buyer_intro = self.buyer_text()
        materials = normalize_rows(self.data.get("materials", []))
        works = normalize_rows(self.data.get("works", []))

        story: list[Any] = []
        story.append(self.p(f"Договор поставки оборудования с монтажом № {contract_number}", "TitleRus"))
        story.append(self.p(str(contract_date_text), "BodyNoIndent"))
        story.append(
            self.p(
                f"{seller_full}, именуемое в дальнейшем «Поставщик», в лице Директора {seller_director}, "
                f"действующего на основании {seller_basis}, с одной стороны, и {buyer_intro}, с другой стороны, "
                "заключили настоящий Договор о нижеследующем:"
            )
        )
        story.append(self.p("1. Предмет договора", "Section"))
        story.append(
            self.p(
                "1.1. По настоящему Договору Поставщик обязуется передать в собственность Покупателя оборудование "
                "и материалы, указанные в п. 1.2 настоящего Договора, а также осуществить работы по монтажу "
                f"по адресу Заказчика: {object_address}, а Покупатель обязуется принять и оплатить оборудование, "
                "материалы и работы в порядке, установленном настоящим Договором."
            )
        )
        story.append(self.p("1.2. По настоящему Договору поставляется следующее оборудование и выполняются работы:", "BodyNoIndent"))
        story.append(self.make_section_table("Материалы", materials, totals.get("materials")))
        story.append(Spacer(1, 5 * mm))
        story.append(self.make_section_table("Работы", works, totals.get("works")))
        story.append(Spacer(1, 4 * mm))
        grand = money(totals.get("grand_total_display") or totals.get("grand_total"))
        grand_words = totals.get("grand_total_words") or "________________"
        story.append(
            Table(
                [[self.cell('Итого "Работы" и "Материалы":', "TableHead"), self.cell(grand, "TableRight")]],
                colWidths=[120 * mm, 60 * mm],
                style=[("GRID", (0, 0), (-1, -1), 0.45, colors.black), ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#E8EEF5"))],
            )
        )
        story.append(self.p("2. Цена договора и порядок расчетов", "Section"))
        story.append(self.p(f"2.1. Общая цена Договора составляет {grand} ({grand_words}) рублей. Цена договора включает стоимость поставляемого оборудования, материалов и выполняемых работ."))
        payment_text = self.data.get("payment_terms", {}).get("text") or "2.2. Покупатель производит оплату в порядке, согласованном Сторонами."
        story.append(self.p(payment_text))
        story.append(self.p("3. Качество и комплектность оборудования", "Section"))
        story.append(self.p("3.1. Оборудование и материалы передаются Покупателю в комплектности, указанной в настоящем Договоре и приложениях."))
        story.append(self.p("4. Выполнение и приемка работ", "Section"))
        montage_terms = self.data.get("montage_terms", {})
        deadline = montage_terms.get("deadline_text") or montage_terms.get("montage_date") or "по согласованию Сторон"
        story.append(self.p(f"4.1. Срок выполнения работ: {deadline}."))
        story.append(self.p("4.2. Приемка оборудования и работ осуществляется с подписанием Сторонами актов приема-передачи."))
        story.append(PageBreak())
        story.append(self.p("5. Реквизиты и подписи сторон", "Section"))
        story.append(self.make_requisites_table(self.seller_requisites_lines(seller, seller_short, seller_director_short), self.buyer_requisites_lines(self.data.get("buyer", {}), object_address, buyer_full, buyer_short)))
        story.append(PageBreak())
        story.append(self.p_html(f"Приложение №1 к договору поставки оборудования с монтажом № {contract_number}<br/>от {contract_date_text}", "BodyNoIndent"))
        story.append(self.p("Акт приема-передачи оборудования и материалов", "TitleRus"))
        story.append(self.make_section_table("Материалы", materials, totals.get("materials")))
        story.append(PageBreak())
        story.append(self.p_html(f"Приложение №2 к договору поставки оборудования с монтажом № {contract_number}<br/>от {contract_date_text}", "BodyNoIndent"))
        story.append(self.p("Акт приема-передачи работ по монтажу оборудования", "TitleRus"))
        story.append(self.make_section_table("Работы", works, totals.get("works")))
        return story

    def render(self) -> dict[str, Any]:
        self.output.parent.mkdir(parents=True, exist_ok=True)
        doc = BaseDocTemplate(str(self.output), pagesize=A4, leftMargin=15 * mm, rightMargin=15 * mm, topMargin=13 * mm, bottomMargin=15 * mm)
        frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="normal")
        doc.addPageTemplates([PageTemplate(id="main", frames=[frame], onPage=self.footer)])
        doc.build(self.story())
        return {"ok": True, "file_type": "contract_pdf", "local_path": str(self.output), "sha256": checksum(self.output), "warnings": []}


def main() -> None:
    parser = argparse.ArgumentParser(description="Render Septik Expert contract PDF from JSON contract_data.")
    parser.add_argument("--payload", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--font-regular")
    parser.add_argument("--font-bold")
    args = parser.parse_args()
    renderer = ContractPdfRenderer(load_json(args.payload), args.output, args.font_regular, args.font_bold)
    print(json.dumps(renderer.render(), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
