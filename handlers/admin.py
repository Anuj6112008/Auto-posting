import sqlite3
import datetime
from telebot import types
from config import ADMIN_ID, TIMEZONE, DB_PATH
from database import (
    get_setting, set_setting, get_all_channels, add_channel, 
    remove_channel, count_channels, get_active_posts, 
    delete_post, count_active_posts
)
from keyboards import (
    main_menu_keyboard, back_to_menu_keyboard, 
    channels_menu_keyboard, posts_list_keyboard, cancel_keyboard
)
from stats import format_stats_message
from sheets_reader import sync_sheet_to_db

def is_admin(user_id: int) -> bool:
    return user_id == ADMIN_ID

def get_live_execution_logs() -> str:
    """Database se latest 10 posting logs fetch karke Green/Red format me return karta hai."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    c.execute("SELECT * FROM post_logs ORDER BY id DESC LIMIT 10")
    logs = c.fetchall()
    conn.close()

    if not logs:
        return "📜 **LIVE POSTING STATUS & LOGS**\n───────────────────────────\nFilhaal koi recent posting record nahi hai."

    text = "📜 **LIVE POSTING STATUS & LOGS**\n───────────────────────────\n"
    for log in logs:
        status = log["status"].upper()
        posted_at = log["posted_at"]
        err = log["error_message"]
        
        if status == "SUCCESS":
            text += f"🟢 **POSTED** | `{posted_at}`\n👉 Status: Successfully broadcasted\n───────────────────────────\n"
        else:
            err_preview = (err[:30] + '...') if err else 'Unknown Error'
            text += f"🔴 **FAILED** | `{posted_at}`\n👉 Error: `{err_preview}`\n───────────────────────────\n"

    return text

def register_admin_handlers(bot):

    # 1. /start & /admin Command
    @bot.message_handler(commands=['start', 'admin'])
    def handle_admin_panel(message):
        if not is_admin(message.from_user.id):
            bot.reply_to(message, "⛔ Access Denied! Ye private admin bot hai.")
            return

        total_channels = count_channels()
        sheet_status = "Connected ✅ (Multi-Tab Sync)" if get_setting("sheet_url") else "Not Linked ❌"
        total_posts = count_active_posts()
        server_time = datetime.datetime.now(TIMEZONE).strftime('%H:%M:%S (%A)')

        text = (
            "🤖 **TELEGRAM AUTO-POSTING ADMIN PANEL**\n"
            "───────────────────────────\n"
            f"📢 **Registered Channels:** `{total_channels}` Active\n"
            f"📊 **Google Sheet:** `{sheet_status}`\n"
            f"📌 **Active Scheduled Posts:** `{total_posts}`\n"
            f"⏰ **Server Time:** `{server_time}`\n"
            "───────────────────────────\n"
            "Neeche diye gaye buttons se operate karein 👇"
        )
        bot.send_message(message.chat.id, text, parse_mode="Markdown", reply_markup=main_menu_keyboard())

    # 2. Main Callback Router
    @bot.callback_query_handler(func=lambda call: call.data in [
        "btn_main_menu", "btn_stats", "btn_manage_channels", 
        "btn_add_channel", "btn_connect_sheet", "btn_sync_now", 
        "btn_list_posts", "btn_cancel_action"
    ])
    def handle_menu_callbacks(call):
        if not is_admin(call.from_user.id):
            return

        chat_id = call.message.chat.id
        msg_id = call.message.message_id
        data = call.data

        # --- Universal Cancel Button ---
        if data == "btn_cancel_action":
            bot.clear_step_handler_by_chat_id(chat_id)
            bot.answer_callback_query(call.id, "❌ Action Cancelled!")
            data = "btn_main_menu"

        # --- Instant Sync Sheet Now ---
        if data == "btn_sync_now":
            sheet_url = get_setting("sheet_url")
            if not sheet_url:
                bot.answer_callback_query(call.id, "⚠️ Pehle Google Sheet connect karein!", show_alert=True)
                return
            count, msg = sync_sheet_to_db(sheet_url)
            bot.answer_callback_query(call.id, f"🔄 Synced! {count} posts updated from all tabs.", show_alert=True)
            data = "btn_main_menu"

        # --- Main Menu / Refresh ---
        if data == "btn_main_menu":
            total_channels = count_channels()
            sheet_status = "Connected ✅ (Multi-Tab Sync)" if get_setting("sheet_url") else "Not Linked ❌"
            total_posts = count_active_posts()
            server_time = datetime.datetime.now(TIMEZONE).strftime('%H:%M:%S (%A)')

            text = (
                "🤖 **TELEGRAM AUTO-POSTING ADMIN PANEL**\n"
                "───────────────────────────\n"
                f"📢 **Registered Channels:** `{total_channels}` Active\n"
                f"📊 **Google Sheet:** `{sheet_status}`\n"
                f"📌 **Active Scheduled Posts:** `{total_posts}`\n"
                f"⏰ **Server Time:** `{server_time}`\n"
                "───────────────────────────\n"
                "Neeche diye gaye buttons se operate karein 👇"
            )
            bot.edit_message_text(text, chat_id, msg_id, parse_mode="Markdown", reply_markup=main_menu_keyboard())

        # --- Performance & Live Logs ---
        elif data == "btn_stats":
            stats_text = format_stats_message()
            live_logs = get_live_execution_logs()
            full_text = f"{stats_text}\n\n{live_logs}"
            bot.edit_message_text(full_text, chat_id, msg_id, parse_mode="Markdown", reply_markup=back_to_menu_keyboard())

        # --- Manage Channels Menu ---
        elif data == "btn_manage_channels":
            show_channels_view(bot, chat_id, msg_id)

        # --- Add New Channel ---
        elif data == "btn_add_channel":
            text = (
                "➕ **Add Target Channel**\n\n"
                "👉 Channel ka **Username** (e.g. `@MyChannel`) ya **Numeric ID** (e.g. `-1001234567890`) chat me bhejiye:\n\n"
                "*(Make sure karein ki bot us channel me Admin ho!)*"
            )
            prompt = bot.send_message(chat_id, text, parse_mode="Markdown", reply_markup=cancel_keyboard())
            bot.register_next_step_handler(prompt, lambda m: process_channel_add(bot, m))

        # --- Connect Google Sheet Once ---
        elif data == "btn_connect_sheet":
            current_sheet = get_setting("sheet_url", "None")
            text = (
                "🔗 **Connect Google Sheet (Multi-Tab Auto-Sync)**\n\n"
                f"Current Linked Sheet: `{current_sheet}`\n\n"
                "👉 Apni Google Sheet ka shareable link yahan paste karein:\n"
                "*(Mon, Tue, Wed, Thu, Fri, Sat, Sun, Everyday saare tabs automatically sync honge)*"
            )
            prompt = bot.send_message(chat_id, text, parse_mode="Markdown", reply_markup=cancel_keyboard())
            bot.register_next_step_handler(prompt, lambda m: process_sheet_connect(bot, m))

        # --- List / Manage Posts ---
        elif data == "btn_list_posts":
            show_posts_view(bot, chat_id, msg_id)

    # 3. Channel Delete Callback
    @bot.callback_query_handler(func=lambda call: call.data.startswith("remove_channel_"))
    def handle_remove_channel(call):
        if not is_admin(call.from_user.id):
            return
        ch_id = int(call.data.replace("remove_channel_", ""))
        remove_channel(ch_id)
        bot.answer_callback_query(call.id, "✅ Channel successfully removed!")
        show_channels_view(bot, call.message.chat.id, call.message.message_id)

    # 4. Post Delete Callback
    @bot.callback_query_handler(func=lambda call: call.data.startswith("delete_post_"))
    def handle_delete_post(call):
        if not is_admin(call.from_user.id):
            return
        post_id = int(call.data.replace("delete_post_", ""))
        delete_post(post_id)
        bot.answer_callback_query(call.id, f"✅ Post #{post_id} delete ho gayi!")
        show_posts_view(bot, call.message.chat.id, call.message.message_id)

# ==================== STEP PROCESSORS ====================

def process_channel_add(bot, message):
    if not is_admin(message.from_user.id):
        return
    channel_input = message.text.strip()
    
    success = add_channel(chat_id=channel_input, channel_name=channel_input)
    if success:
        bot.send_message(message.chat.id, f"✅ Channel `{channel_input}` successfully add ho gaya!", parse_mode="Markdown", reply_markup=main_menu_keyboard())
    else:
        bot.send_message(message.chat.id, f"⚠️ Channel `{channel_input}` pehle se added hai.", parse_mode="Markdown", reply_markup=main_menu_keyboard())

def process_sheet_connect(bot, message):
    if not is_admin(message.from_user.id):
        return
    sheet_url = message.text.strip()
    
    status_msg = bot.send_message(message.chat.id, "🔄 Google Sheet ke saare tabs scan aur sync ho rahe hain...")
    count, result_message = sync_sheet_to_db(sheet_url)
    
    if count > 0:
        set_setting("sheet_url", sheet_url)
        bot.delete_message(message.chat.id, status_msg.message_id)
        bot.send_message(
            message.chat.id,
            f"🎉 **Google Sheet Successfully Connected!**\n\n{result_message}\n\n"
            f"⚡ **Permanent Weekly Cycle Active:** Saare tabs (`Mon`, `Tue` etc.) ka schedule continuous har week execute hota rahega!",
            parse_mode="Markdown",
            reply_markup=main_menu_keyboard()
        )
    else:
        bot.delete_message(message.chat.id, status_msg.message_id)
        bot.send_message(message.chat.id, f"{result_message}", parse_mode="Markdown", reply_markup=main_menu_keyboard())

def show_channels_view(bot, chat_id: int, message_id: int = None):
    channels = get_all_channels()
    text = (
        "📢 **REGISTERED BROADCAST CHANNELS**\n"
        "───────────────────────────\n"
        f"Total Active Channels: `{len(channels)}`\n\n"
        "Neeche se naya channel add karein ya kisi channel ko remove karein:\n"
        "───────────────────────────"
    )
    if message_id:
        bot.edit_message_text(text, chat_id, message_id, parse_mode="Markdown", reply_markup=channels_menu_keyboard(channels))
    else:
        bot.send_message(chat_id, text, parse_mode="Markdown", reply_markup=channels_menu_keyboard(channels))

def show_posts_view(bot, chat_id: int, message_id: int = None):
    posts = get_active_posts()
    if not posts:
        text = "📋 Filhaal koi active scheduled post nahi hai."
        if message_id:
            bot.edit_message_text(text, chat_id, message_id, reply_markup=back_to_menu_keyboard())
        else:
            bot.send_message(chat_id, text, reply_markup=back_to_menu_keyboard())
        return

    text = "📋 **ACTIVE SCHEDULED POSTS LIST**\n───────────────────────────\n"
    for p in posts:
        source_val = p["source"] if "source" in p.keys() else "manual"
        src = "📊 SHEET" if source_val == "sheet" else "💬 MANUAL"
        cap_preview = (p["caption"][:20] + '...') if p["caption"] else "Media"
        text += (
            f"🔹 **ID #{p['id']}** | `{p['post_type'].upper()}` | `{src}`\n"
            f"📅 Day/Tab: `{p['days'].upper()}`\n"
            f"⏰ Times: `{p['times']} IST`\n"
            f"📝 Preview: {cap_preview}\n"
            "───────────────────────────\n"
        )

    if message_id:
        bot.edit_message_text(text, chat_id, message_id, parse_mode="Markdown", reply_markup=posts_list_keyboard(posts))
    else:
        bot.send_message(chat_id, text, parse_mode="Markdown", reply_markup=posts_list_keyboard(posts))
