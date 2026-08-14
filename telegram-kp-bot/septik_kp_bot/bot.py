from __future__ import annotations

import asyncio
import logging
from pathlib import Path

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.constants import ChatAction
from telegram.ext import (
    Application,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from .catalog import load_catalog
from .config import load_settings
from .integrations import GoogleSync, sync_rendered_proposal
from .openai_client import make_proposal, transcribe_audio
from .renderer import render_proposal_png
from .storage import ProposalStore, now_iso


logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logger = logging.getLogger("septik_kp_bot")

SETTINGS = load_settings()
CATALOG = load_catalog(SETTINGS.price_catalog_path)
STORE = ProposalStore(SETTINGS.data_dir)


def is_allowed(user_id: int | None) -> bool:
    if user_id is None:
        return False
    return not SETTINGS.allowed_telegram_user_ids or user_id in SETTINGS.allowed_telegram_user_ids


def keyboard(proposal_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton("Ок, сделать PNG", callback_data=f"ok:{proposal_id}"),
                InlineKeyboardButton("Внести правки", callback_data=f"edit:{proposal_id}"),
            ],
            [InlineKeyboardButton("Отмена", callback_data=f"cancel:{proposal_id}")],
        ]
    )


def looks_like_correction(text: str) -> bool:
    normalized = text.strip().lower()
    correction_words = (
        "добав",
        "добавь",
        "замени",
        "заменить",
        "убери",
        "убрать",
        "исправ",
        "поменяй",
        "измени",
        "цена",
        "сумма",
        "сделай",
        "поставь",
    )
    return any(normalized.startswith(word) for word in correction_words)


async def deny(update: Update) -> None:
    if update.effective_message:
        await update.effective_message.reply_text("Нет доступа к этому боту.")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_allowed(update.effective_user.id if update.effective_user else None):
        await deny(update)
        return
    text = (
        "Готов делать КП.\n\n"
        "Отправь текст или голос по замеру: клиент, телефон, адрес, модель станции, материалы, работы и цены, если они ручные.\n\n"
        "Я верну черновик. После проверки нажми Ок, и я сделаю PNG."
    )
    await update.message.reply_text(text)


async def new(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data.pop("awaiting_correction_for", None)
    context.user_data.pop("last_proposal_id", None)
    await start(update, context)


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    context.user_data.pop("awaiting_correction_for", None)
    if update.message:
        await update.message.reply_text("Ок, текущий ввод правок отменен.")


async def sync_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_allowed(update.effective_user.id if update.effective_user else None):
        await deny(update)
        return
    google = GoogleSync(SETTINGS)
    reason = google.disabled_reason()
    lines = [
        "Статус синхронизации:",
        f"Google Drive/Sheets: {'включен' if google.enabled else 'не включен'}",
        f"Google clients folder: {'задан' if SETTINGS.google_clients_folder_id else 'не задан'}",
        f"Google registry sheet: {'задан' if SETTINGS.google_registry_sheet_id else 'не задан'}",
        f"Control panel API: {'задан' if SETTINGS.control_panel_api_url else 'не задан'}",
        f"amoCRM API: {'задан' if SETTINGS.amocrm_base_url and SETTINGS.amocrm_access_token else 'не задан'}",
    ]
    if reason:
        lines.append(f"Причина: {reason}")
    await update.effective_message.reply_text("\n".join(lines))


async def send_draft(update: Update, result_record: dict) -> None:
    text = result_record["calculation_text"]
    if len(text) > 3900:
        text = text[:3800] + "\n\n...текст длинный, полная версия сохранена в JSON."
    await update.effective_message.reply_text(text, reply_markup=keyboard(result_record["proposal_id"]))


async def build_from_text(update: Update, context: ContextTypes.DEFAULT_TYPE, text: str) -> None:
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    await update.effective_chat.send_action(ChatAction.TYPING)
    correction_for = context.user_data.pop("awaiting_correction_for", None)
    if not correction_for and looks_like_correction(text):
        correction_for = context.user_data.get("last_proposal_id")

    if correction_for:
        previous = STORE.load(correction_for)
        result = await make_proposal(
            SETTINGS.openai_api_key,
            SETTINGS.openai_proposal_model,
            CATALOG,
            previous["source_text"],
            previous=previous,
            correction=text,
        )
        previous["status"] = "draft_text"
        previous["corrections"].append({"text": text, "created_at": now_iso()})
        previous["payload"] = result["payload"]
        previous["calculation_text"] = result["calculation_text"]
        previous["missing_data"] = result["missing_data"]
        previous["warnings"] = result["warnings"]
        previous["ai_payload"] = result["ai_payload"]
        STORE.save(previous)
        context.user_data["last_proposal_id"] = previous["proposal_id"]
        await send_draft(update, previous)
        return

    result = await make_proposal(SETTINGS.openai_api_key, SETTINGS.openai_proposal_model, CATALOG, text)
    record = STORE.create(user_id, chat_id, text, result)
    context.user_data["last_proposal_id"] = record["proposal_id"]
    await send_draft(update, record)


async def text_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_allowed(update.effective_user.id if update.effective_user else None):
        await deny(update)
        return
    await build_from_text(update, context, update.message.text or "")


async def voice_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not is_allowed(update.effective_user.id if update.effective_user else None):
        await deny(update)
        return
    proposal_id = STORE.new_id()
    target = STORE.upload_path(proposal_id, ".ogg")
    await update.effective_chat.send_action(ChatAction.UPLOAD_VOICE)
    voice = update.message.voice or update.message.audio
    telegram_file = await context.bot.get_file(voice.file_id)
    await telegram_file.download_to_drive(custom_path=target)
    await update.effective_chat.send_action(ChatAction.TYPING)
    transcript = await transcribe_audio(SETTINGS.openai_api_key, SETTINGS.openai_transcription_model, target)
    if not transcript:
        await update.message.reply_text("Не получилось расшифровать голос. Пришли, пожалуйста, текстом.")
        return
    await update.message.reply_text("Расшифровал голос, собираю черновик КП.")
    await build_from_text(update, context, transcript)


async def callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if not query:
        return
    await query.answer()
    if not is_allowed(query.from_user.id if query.from_user else None):
        await query.edit_message_text("Нет доступа к этому боту.")
        return

    action, proposal_id = (query.data or "").split(":", 1)
    record = STORE.load(proposal_id)
    if record["telegram_user_id"] != query.from_user.id and query.from_user.id not in SETTINGS.owner_telegram_user_ids:
        await query.edit_message_text("Это КП создал другой пользователь.")
        return

    if action == "cancel":
        record["status"] = "cancelled"
        STORE.save(record)
        await query.edit_message_text("КП отменено.")
        return

    if action == "edit":
        context.user_data["awaiting_correction_for"] = proposal_id
        await query.message.reply_text("Напиши правку одним сообщением. Например: «замени Био 4 на Про 4, добавь греющий кабель 10 м».")
        return

    if action == "ok":
        record["status"] = "rendering"
        STORE.save(record)
        await query.message.reply_text("Принял. Генерирую PNG.")
        output = STORE.rendered_path(proposal_id)
        result = await asyncio.to_thread(
            render_proposal_png,
            record["payload"],
            SETTINGS.proposal_template_path,
            output,
            SETTINGS.font_regular_path,
            SETTINGS.font_bold_path,
        )
        record["status"] = "rendered"
        record["render_result"] = result
        upload = await sync_rendered_proposal(SETTINGS, record, Path(result["local_path"]))
        if upload:
            record["drive_upload"] = upload
        STORE.save(record)
        with Path(result["local_path"]).open("rb") as fh:
            caption = "КП готово."
            if upload.get("file_url"):
                caption += f"\nGoogle Drive: {upload['file_url']}"
            elif upload.get("sync_skipped"):
                caption += f"\nGoogle sync не выполнен: {upload['sync_skipped']}"
            elif upload.get("sync_error"):
                caption += "\nGoogle sync не выполнен: ошибка, смотри лог сервера."
            await query.message.reply_photo(photo=fh, caption=caption)
        return


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    logger.exception("Telegram update failed", exc_info=context.error)
    if isinstance(update, Update) and update.effective_message:
        await update.effective_message.reply_text(f"Ошибка: {context.error}")


def main() -> None:
    SETTINGS.data_dir.mkdir(parents=True, exist_ok=True)
    app = Application.builder().token(SETTINGS.telegram_bot_token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("new", new))
    app.add_handler(CommandHandler("cancel", cancel))
    app.add_handler(CommandHandler("sync_status", sync_status))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_message))
    app.add_handler(MessageHandler(filters.VOICE | filters.AUDIO, voice_message))
    app.add_handler(CallbackQueryHandler(callback))
    app.add_error_handler(error_handler)
    logger.info("Starting Septik Expert КП bot")
    try:
        asyncio.get_event_loop()
    except RuntimeError:
        asyncio.set_event_loop(asyncio.new_event_loop())
    app.run_polling(allowed_updates=Update.ALL_TYPES)
