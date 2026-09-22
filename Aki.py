import os
import logging
from contextlib import asynccontextmanager

import requests
import akinator
from fastapi import FastAPI, Request, Response
from fastapi.concurrency import run_in_threadpool

BOT_TOKEN = os.environ.get("BOT_TOKEN")
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")  # مثل: https://aki-bot.onrender.com

API = f"https://api.telegram.org/bot{BOT_TOKEN}"

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# بازی هر کاربر
games: dict[int, akinator.Akinator] = {}


# ---------- Telegram helpers ----------
def tg(method: str, **payload):
    """صدازدن متد تلگرام"""
    try:
        r = requests.post(f"{API}/{method}", json=payload, timeout=30)
        return r.json()
    except Exception as e:
        logger.error(f"tg {method} error: {e}")
        return {"ok": False}


def send_message(chat_id: int, text: str, keyboard=None):
    payload = {"chat_id": chat_id, "text": text}
    if keyboard:
        payload["reply_markup"] = {"inline_keyboard": keyboard}
    return tg("sendMessage", **payload)


def answer_callback(callback_id: str, text: str = ""):
    return tg("answerCallbackQuery", callback_query_id=callback_id, text=text)


def question_keyboard():
    return [
        [
            {"text": "بله ✅", "callback_data": "y"},
            {"text": "خیر ❌", "callback_data": "n"},
        ],
        [
            {"text": "نمی‌دونم 🤷", "callback_data": "i"},
            {"text": "احتمالاً 👍", "callback_data": "p"},
            {"text": "احتمالاً نه 👎", "callback_data": "pn"},
        ],
        [
            {"text": "برگشت 🔙", "callback_data": "b"},
        ],
    ]


# ---------- Game logic ----------
def start_game(chat_id: int):
    aki = akinator.Akinator()
    aki.start_game()
    games[chat_id] = aki
    send_message(chat_id, f"سوال: {aki.question}", question_keyboard())


def handle_answer(chat_id: int, callback_id: str, ans: str):
    aki = games.get(chat_id)
    if not aki:
        answer_callback(callback_id, "بازی پیدا نشد، /play رو بزن")
        send_message(chat_id, "برای شروع /play رو بزن.")
        return

    if ans == "b":
        try:
            aki.back()
        except akinator.CantGoBackAnyFurther:
            answer_callback(callback_id, "نمی‌شه عقب‌تر رفت")
            return
        answer_callback(callback_id)
    else:
        try:
            aki.answer(ans)
        except Exception as e:
            answer_callback(callback_id, f"خطا: {e}")
            return
        answer_callback(callback_id)

    if aki.progression >= 80 or aki.answer == "win":
        send_message(
            chat_id,
            f"حدس من: {aki.name_proposition}\n"
            f"توضیح: {aki.description_proposition}\n"
            f"عکس: {aki.photo}",
        )
        games.pop(chat_id, None)
    else:
        send_message(chat_id, f"سوال: {aki.question}", question_keyboard())


# ---------- Update dispatcher ----------
def process_update(update: dict):
    if "message" in update:
        msg = update["message"]
        chat_id = msg["chat"]["id"]
        text = (msg.get("text") or "").strip()

        if text.startswith("/start"):
            send_message(
                chat_id,
                "سلام! من اِکیناتور هستم 🧞\n"
                "به یه شخصیت فکر کن، من با سوالات بله/خیر حدس می‌زنم.\n"
                "برای شروع /play رو بزن.",
            )
        elif text.startswith("/play"):
            start_game(chat_id)
        else:
            send_message(chat_id, "برای شروع /play رو بزن.")

    elif "callback_query" in update:
        cq = update["callback_query"]
        chat_id = cq["message"]["chat"]["id"]
        handle_answer(chat_id, cq["id"], cq["data"])


# ---------- FastAPI ----------
@asynccontextmanager
async def lifespan(app: FastAPI):
    webhook = f"{WEBHOOK_URL}/webhook"
    await run_in_threadpool(tg, "setWebhook", url=webhook, drop_pending_updates=True)
    logger.info(f"Webhook set: {webhook}")
    yield
    await run_in_threadpool(tg, "deleteWebhook")


app = FastAPI(lifespan=lifespan)


@app.get("/")
async def health():
    return {"status": "ok"}


@app.post("/webhook")
async def webhook(request: Request):
    update = await request.json()
    # پردازش توی ترد جدا تا event loop بلاک نشه
    await run_in_threadpool(process_update, update)
    return Response(status_code=200)
