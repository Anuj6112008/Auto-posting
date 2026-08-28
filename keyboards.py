from telebot import types

def main_menu_keyboard():
    """Main Admin Dashboard Buttons with Instant Sync."""
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("➕ Create Post", callback_data="btn_create_post"),
        types.InlineKeyboardButton("📋 Manage Posts", callback_data="btn_list_posts"),
        types.InlineKeyboardButton("🔗 Connect Sheet", callback_data="btn_connect_sheet"),
        types.InlineKeyboardButton("🔄 Sync Sheet Now", callback_data="btn_sync_now"),
        types.InlineKeyboardButton("📢 Manage Channels", callback_data="btn_manage_channels"),
        types.InlineKeyboardButton("📊 Analytics & Stats", callback_data="btn_stats")
    )
    return markup

def channels_menu_keyboard(channels: list):
    """Multi-Channels Add & Delete Manager Keypad."""
    markup = types.InlineKeyboardMarkup(row_width=1)
    markup.add(types.InlineKeyboardButton("➕ Add New Channel", callback_data="btn_add_channel"))
    
    for ch in channels:
        ch_id = ch["id"]
        ch_title = ch["channel_name"] or ch["chat_id"]
        markup.add(
            types.InlineKeyboardButton(f"❌ Remove: {ch_title}", callback_data=f"remove_channel_{ch_id}")
        )
        
    markup.add(types.InlineKeyboardButton("🔙 Back to Main Menu", callback_data="btn_main_menu"))
    return markup

def cancel_keyboard():
    """Universal Cancel Button."""
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("❌ Cancel Action", callback_data="btn_cancel_action"))
    return markup

def days_selection_keyboard(selected_days: list):
    """Week Days Toggle Keypad."""
    days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    markup = types.InlineKeyboardMarkup(row_width=3)
    buttons = []
    
    for d in days:
        is_selected = d.lower() in selected_days
        label = f"✅ {d}" if is_selected else f"❌ {d}"
        buttons.append(types.InlineKeyboardButton(label, callback_data=f"toggle_day_{d.lower()}"))
    
    markup.add(*buttons)
    
    all_selected = len(selected_days) == 7
    all_label = "✅ All Days" if all_selected else "Select All"
    
    markup.add(
        types.InlineKeyboardButton(all_label, callback_data="toggle_all_days"),
        types.InlineKeyboardButton("➡️ Confirm Days", callback_data="confirm_days")
    )
    markup.add(types.InlineKeyboardButton("❌ Cancel Action", callback_data="btn_cancel_action"))
    return markup

def posts_list_keyboard(posts: list):
    """Active posts list view."""
    markup = types.InlineKeyboardMarkup(row_width=1)
    
    for p in posts:
        post_id = p["id"]
        post_type = p["post_type"].upper()
        markup.add(
            types.InlineKeyboardButton(f"❌ Delete #{post_id} ({post_type})", callback_data=f"delete_post_{post_id}")
        )
        
    markup.add(types.InlineKeyboardButton("🔙 Back to Main Menu", callback_data="btn_main_menu"))
    return markup

def back_to_menu_keyboard():
    """Simple Back button."""
    markup = types.InlineKeyboardMarkup()
    markup.add(types.InlineKeyboardButton("🔙 Back to Main Menu", callback_data="btn_main_menu"))
    return markup