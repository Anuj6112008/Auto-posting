import csv
import re
import io
import json
import requests
from database import add_post, clear_sheet_posts

def extract_sheet_id(url: str) -> str:
    """Google Sheet URL se Sheet ID nikaalta hai."""
    match = re.search(r"/spreadsheets/d/([a-zA-Z0-9-_]+)", url)
    return match.group(1) if match else None

def normalize_times(raw_times: str) -> str:
    """Time format clean aur standardize karta hai (e.g. '9:28' -> '09:28')."""
    parts = str(raw_times).split(",")
    valid_times = []
    
    for t in parts:
        t = t.strip().replace('"', '').replace("'", "")
        if not t:
            continue
        # 1:30 ya 9:28 ko 01:30 ya 09:28 banayein
        if re.match(r"^\d:\d{2}$", t):
            t = "0" + t
        valid_times.append(t)
        
    return ", ".join(valid_times)

def parse_media_urls(url_string: str) -> list:
    """Comma-separated URLs ko list me convert karta hai."""
    if not url_string:
        return []
    urls = [u.strip().replace('"', '') for u in str(url_string).split(",") if u.strip().startswith("http")]
    return urls

def sync_sheet_to_db(sheet_url: str) -> tuple[int, str]:
    """Direct Tab Name API se saare tabs (Everyday, Mon-Sun) fetch karke sync karta hai."""
    sheet_id = extract_sheet_id(sheet_url)
    if not sheet_id:
        return 0, "❌ Invalid Google Sheet URL!"

    # Saare possible day tab names jo client banata hai
    target_tabs = [
        "Everyday", "everyday", 
        "Mon", "mon", "Monday", 
        "Tue", "tue", "Tuesday", 
        "Wed", "wed", "Wednesday", 
        "Thu", "thu", "Thursday", 
        "Fri", "fri", "Friday", 
        "Sat", "sat", "Saturday", 
        "Sun", "sun", "Sunday",
        "Sheet1"
    ]

    all_valid_rows = []
    found_tabs = []
    seen_content = set()

    for tab_name in target_tabs:
        # Google Direct Sheet Name Endpoint
        gviz_url = f"https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?sheet={tab_name}&tqx=out:csv"
        
        try:
            res = requests.get(gviz_url, timeout=8)
            if res.status_code != 200 or "<html" in res.text.lower():
                continue

            csv_text = res.content.decode('utf-8', errors='replace')
            csv_file = io.StringIO(csv_text)
            reader = csv.DictReader(csv_file)

            # Clean header keys
            fieldnames = [f.strip().lower().replace('"', '') for f in (reader.fieldnames or [])]
            if not fieldnames or ("time" not in fieldnames and "text" not in fieldnames):
                continue

            tab_day_default = tab_name.lower().replace("day", "")
            if tab_day_default.startswith("every"):
                tab_day_default = "everyday"

            tab_rows_count = 0

            for row in reader:
                clean_row = {k.strip().lower().replace('"', ''): v.strip().replace('"', '') for k, v in row.items() if k}

                day_val = clean_row.get("day", "").strip().lower() or tab_day_default
                time_val = clean_row.get("time", "").strip()
                text_val = clean_row.get("text", "").strip()
                photo_raw = clean_row.get("photo_url", "").strip()
                video_raw = clean_row.get("video_url", "").strip()
                status = clean_row.get("status", "ACTIVE").strip().upper()

                if (status == "ACTIVE" or not status) and time_val and (text_val or photo_raw or video_raw):
                    photos = parse_media_urls(photo_raw)
                    videos = parse_media_urls(video_raw)
                    formatted_times = normalize_times(time_val)

                    # Deduplication key
                    unique_key = f"{day_val}_{formatted_times}_{text_val[:15]}"
                    if unique_key in seen_content:
                        continue
                    seen_content.add(unique_key)

                    total_media = len(photos) + len(videos)

                    if total_media > 1:
                        p_type = "album"
                        album_items = []
                        for p in photos:
                            album_items.append({"type": "photo", "url": p})
                        for v in videos:
                            album_items.append({"type": "video", "url": v})
                        content = json.dumps(album_items)
                        caption = text_val
                    elif len(photos) == 1 and len(videos) == 0:
                        p_type = "photo"
                        content = photos[0]
                        caption = text_val
                    elif len(videos) == 1 and len(photos) == 0:
                        p_type = "video"
                        content = videos[0]
                        caption = text_val
                    elif text_val:
                        p_type = "text"
                        content = text_val
                        caption = ""
                    else:
                        continue

                    all_valid_rows.append({
                        "post_type": p_type,
                        "content": content,
                        "caption": caption,
                        "days": day_val,
                        "times": formatted_times
                    })
                    tab_rows_count += 1

            if tab_rows_count > 0:
                found_tabs.append(f"{tab_name} ({tab_rows_count})")

        except Exception as e:
            continue

    if not all_valid_rows:
        return 0, "⚠️ Sheet ke tabs me koi valid rows nahi mili."

    # Clear old sheet records and insert fresh data
    clear_sheet_posts()

    for item in all_valid_rows:
        add_post(
            post_type=item["post_type"],
            content=item["content"],
            caption=item["caption"],
            entities="[]",
            days=item["days"],
            times=item["times"],
            source="sheet"
        )

    tabs_summary = ", ".join(found_tabs)
    return len(all_valid_rows), f"✅ Total `{len(all_valid_rows)}` posts synced successfully from: `{tabs_summary}`!"