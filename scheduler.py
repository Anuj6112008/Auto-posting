import json
import datetime
from telebot import types
from apscheduler.schedulers.background import BackgroundScheduler
from config import TIMEZONE
from database import get_setting, get_all_channels, get_active_posts, log_post_execution
from sheets_reader import sync_sheet_to_db

def deserialize_entities(entities_json: str):
    """JSON string ko Telegram MessageEntity objects me convert karta hai."""
    if not entities_json:
        return None
    try:
        raw_list = json.loads(entities_json)
        return [types.MessageEntity.de_json(item) for item in raw_list] if raw_list else None
    except Exception:
        return None

def check_and_execute_posts(bot):
    """Real-Time Live Sheet Sync + Active schedules broadcasting."""
    # 1. REAL-TIME LIVE SYNC (Har minute post check hone se pehle live sheet data fetch hoga)
    sheet_url = get_setting("sheet_url")
    if sheet_url:
        try:
            sync_sheet_to_db(sheet_url)
        except Exception as e:
            print(f"⚠️ [Real-Time Sync] Sheet sync notice: {e}")

    channels = get_all_channels()
    if not channels:
        return  # Koi channel registered nahi hai
        
    now = datetime.datetime.now(TIMEZONE)
    current_day = now.strftime('%a').lower()       # e.g. 'thu'
    current_day_full = now.strftime('%A').lower()  # e.g. 'thursday'
    current_time = now.strftime('%H:%M')           # e.g. '23:45'
    
    active_posts = get_active_posts()
    
    for post in active_posts:
        p_id = post["id"]
        p_type = post["post_type"]
        content = post["content"]
        caption = post["caption"]
        source = post["source"] if "source" in post.keys() else "manual"
        entities = deserialize_entities(post["entities"] if "entities" in post.keys() else "[]")
        
        days_list = [d.strip().lower() for d in post["days"].split(",")]
        times_list = [t.strip().zfill(5) if len(t.strip()) == 4 else t.strip() for t in post["times"].split(",")]
        
        day_match = (
            current_day in days_list or 
            current_day_full in days_list or 
            "everyday" in days_list or 
            "all" in days_list
        )
        time_match = current_time in times_list
        
        if day_match and time_match:
            print(f"[{current_time}] 🎯 MATCH FOUND! Broadcasting Post #{p_id} ({p_type.upper()}) to {len(channels)} channels...")
            
            for ch in channels:
                ch_id = ch["chat_id"]
                try:
                    # 1. Multi-Media Group / Album (Multiple Photos/Videos)
                    if p_type == "album":
                        items = json.loads(content)
                        media_group = []
                        for idx, it in enumerate(items):
                            cap = caption if idx == 0 else None
                            p_mode = "HTML" if idx == 0 else None
                            if it["type"] == "photo":
                                media_group.append(types.InputMediaPhoto(media=it["url"], caption=cap, parse_mode=p_mode))
                            elif it["type"] == "video":
                                media_group.append(types.InputMediaVideo(media=it["url"], caption=cap, parse_mode=p_mode))
                        bot.send_media_group(chat_id=ch_id, media=media_group)

                    # 2. Plain Text Message
                    elif p_type == "text":
                        if source == "sheet":
                            bot.send_message(chat_id=ch_id, text=content, parse_mode="HTML")
                        else:
                            bot.send_message(chat_id=ch_id, text=content, entities=entities)

                    # 3. Photo Post
                    elif p_type == "photo":
                        if source == "sheet":
                            bot.send_photo(chat_id=ch_id, photo=content, caption=caption, parse_mode="HTML")
                        else:
                            bot.send_photo(chat_id=ch_id, photo=content, caption=caption, caption_entities=entities)

                    # 4. Video Post
                    elif p_type == "video":
                        if source == "sheet":
                            bot.send_video(chat_id=ch_id, video=content, caption=caption, parse_mode="HTML")
                        else:
                            bot.send_video(chat_id=ch_id, video=content, caption=caption, caption_entities=entities)

                    # 5. Document / File
                    elif p_type == "document":
                        bot.send_document(chat_id=ch_id, document=content, caption=caption, caption_entities=entities)

                    # 6. Audio / MP3
                    elif p_type == "audio":
                        bot.send_audio(chat_id=ch_id, audio=content, caption=caption, caption_entities=entities)

                    # 7. GIF / Animation
                    elif p_type == "animation":
                        bot.send_animation(chat_id=ch_id, animation=content, caption=caption, caption_entities=entities)

                    # 8. Sticker
                    elif p_type == "sticker":
                        bot.send_sticker(chat_id=ch_id, sticker=content)
                    
                    log_post_execution(post_id=p_id, status="success")
                    print(f"[{current_time}] 🚀 Sent Post #{p_id} to Channel: {ch_id}!")
                    
                except Exception as e:
                    error_msg = str(e)
                    log_post_execution(post_id=p_id, status="failed", error_message=error_msg)
                    print(f"[{current_time}] ❌ Error sending to {ch_id}: {error_msg}")

def start_scheduler(bot) -> BackgroundScheduler:
    scheduler = BackgroundScheduler(timezone=TIMEZONE)
    # Check & Real-time Sync Every 1 Minute
    scheduler.add_job(check_and_execute_posts, 'interval', minutes=1, args=[bot])
    scheduler.start()
    return scheduler