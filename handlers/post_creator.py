import json
import datetime
from telebot import types
from config import ADMIN_ID
from database import add_post
from keyboards import days_selection_keyboard, main_menu_keyboard, cancel_keyboard

sessions = {}

def is_admin(user_id: int) -> bool:
    return user_id == ADMIN_ID

def serialize_entities(entities):
    """Telegram formatting entities (bold, italic, quote, spoilers etc.) ko JSON me convert karta hai."""
    if not entities:
        return "[]"
    return json.dumps([e.to_dict() for e in entities])

def register_post_creator_handlers(bot):

    @bot.callback_query_handler(func=lambda call: call.data == "btn_create_post")
    def start_create_post(call):
        if not is_admin(call.from_user.id):
            return

        chat_id = call.message.chat.id
        sessions[chat_id] = {"selected_days": []}

        text = (
            "📝 **Step 1: Content Bhejo**\n\n"
            "Aap inme se kuch bhi send kar sakte ho:\n"
            "• 💬 Text (Bold, Italic, Quotes, Spoilers, Links sab support hai)\n"
            "• 📸 Photo (with/without Caption)\n"
            "• 🎥 Video (with/without Caption)\n"
            "• 📁 Document / File (PDF, APK, ZIP etc.)\n"
            "• 🎵 Audio / MP3\n"
            "• 🎞 GIF / Animation\n"
            "• 🏷 Sticker\n\n"
            "👉 Abhi apni post bot ko send karein ya cancel karein:"
        )
        msg = bot.send_message(chat_id, text, parse_mode="Markdown", reply_markup=cancel_keyboard())
        bot.register_next_step_handler(msg, lambda m: process_media_content(bot, m))

    @bot.callback_query_handler(func=lambda call: call.data.startswith("toggle_day_") or call.data == "toggle_all_days")
    def handle_day_toggles(call):
        if not is_admin(call.from_user.id):
            return

        chat_id = call.message.chat.id
        session = sessions.get(chat_id, {"selected_days": []})

        if call.data == "toggle_all_days":
            all_days = ["mon", "tue", "wed", "thu", "fri", "sat", "sun"]
            if len(session["selected_days"]) == 7:
                session["selected_days"] = []
            else:
                session["selected_days"] = all_days.copy()
        else:
            day = call.data.replace("toggle_day_", "")
            if day in session["selected_days"]:
                session["selected_days"].remove(day)
            else:
                session["selected_days"].append(day)

        sessions[chat_id] = session
        bot.edit_message_reply_markup(
            chat_id, 
            call.message.message_id, 
            reply_markup=days_selection_keyboard(session["selected_days"])
        )

    @bot.callback_query_handler(func=lambda call: call.data == "confirm_days")
    def handle_confirm_days(call):
        if not is_admin(call.from_user.id):
            return

        chat_id = call.message.chat.id
        session = sessions.get(chat_id)

        if not session or not session.get("selected_days"):
            bot.answer_callback_query(call.id, "⚠️ Kam se kam ek din select karein!", show_alert=True)
            return

        text = (
            "⏰ **Step 3: Posting Times Set Karo**\n\n"
            "Din me kis-kis time post bhejna hai? (24-Hour format me likho).\n\n"
            "💡 *Multiple times ke liye comma (,) use karein:*\n"
            "Example: `09:30, 14:00, 21:15`\n\n"
            "👉 Apna Time bhejiye:"
        )
        msg = bot.send_message(chat_id, text, parse_mode="Markdown", reply_markup=cancel_keyboard())
        bot.register_next_step_handler(msg, lambda m: process_posting_times(bot, m))

def process_media_content(bot, message):
    chat_id = message.chat.id
    session = sessions.get(chat_id, {})

    # 1. Text Message
    if message.text:
        session["post_type"] = "text"
        session["content"] = message.text
        session["caption"] = ""
        session["entities"] = serialize_entities(message.entities)

    # 2. Photo Message
    elif message.photo:
        session["post_type"] = "photo"
        session["content"] = message.photo[-1].file_id
        session["caption"] = message.caption or ""
        session["entities"] = serialize_entities(message.caption_entities)

    # 3. Video Message
    elif message.video:
        session["post_type"] = "video"
        session["content"] = message.video.file_id
        session["caption"] = message.caption or ""
        session["entities"] = serialize_entities(message.caption_entities)

    # 4. Document / File
    elif message.document:
        session["post_type"] = "document"
        session["content"] = message.document.file_id
        session["caption"] = message.caption or ""
        session["entities"] = serialize_entities(message.caption_entities)

    # 5. Audio Message
    elif message.audio:
        session["post_type"] = "audio"
        session["content"] = message.audio.file_id
        session["caption"] = message.caption or ""
        session["entities"] = serialize_entities(message.caption_entities)

    # 6. GIF / Animation
    elif message.animation:
        session["post_type"] = "animation"
        session["content"] = message.animation.file_id
        session["caption"] = message.caption or ""
        session["entities"] = serialize_entities(message.caption_entities)

    # 7. Sticker
    elif message.sticker:
        session["post_type"] = "sticker"
        session["content"] = message.sticker.file_id
        session["caption"] = ""
        session["entities"] = "[]"

    else:
        bot.send_message(chat_id, "⚠️ Invalid format! Kripya valid content bhejiye.", reply_markup=cancel_keyboard())
        return

    sessions[chat_id] = session

    text = (
        "📅 **Step 2: Posting Days Select Karo**\n\n"
        "Jin dino post channel me jana chahiye unhe toggle karke 'Confirm Days' dabayein:"
    )
    bot.send_message(chat_id, text, parse_mode="Markdown", reply_markup=days_selection_keyboard([]))

def process_posting_times(bot, message):
    chat_id = message.chat.id
    raw_times = message.text.strip().split(",")
    valid_times = []

    for t in raw_times:
        t = t.strip()
        try:
            datetime.datetime.strptime(t, "%H:%M")
            valid_times.append(t)
        except ValueError:
            bot.send_message(
                chat_id,
                f"⚠️ Galat Time format: `{t}`\nFormat hamesha 24-hour `HH:MM` (e.g. 14:30) hona chahiye. Dobara bhejo:",
                parse_mode="Markdown",
                reply_markup=cancel_keyboard()
            )
            bot.register_next_step_handler(message, lambda m: process_posting_times(bot, m))
            return

    session = sessions.get(chat_id)
    days_str = ",".join(session["selected_days"])
    times_str = ", ".join(valid_times)

    # Database me save karein (source='manual')
    post_id = add_post(
        post_type=session["post_type"],
        content=session["content"],
        caption=session["caption"],
        entities=session.get("entities", "[]"),
        days=days_str,
        times=times_str,
        source="manual"
    )

    text = (
        "🎉 **Post Successfully Scheduled!**\n"
        "───────────────────────────\n"
        f"🆔 **Post ID:** `#{post_id}`\n"
        f"📦 **Type:** `{session['post_type'].upper()}`\n"
        f"📅 **Days:** `{days_str.upper()}`\n"
        f"⏰ **Times:** `{times_str} IST`\n"
        "───────────────────────────\n"
        "Ye post aapke sabhi registered channels me auto-broadcast ho jayegi!"
    )
    bot.send_message(chat_id, text, parse_mode="Markdown", reply_markup=main_menu_keyboard())
    sessions.pop(chat_id, None)
