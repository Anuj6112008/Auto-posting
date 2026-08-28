import sqlite3
from config import DB_PATH

def get_connection():
    """SQLite Database connection return karta hai."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Saare tables create karta hai aur columns migrate karta hai."""
    conn = get_connection()
    c = conn.cursor()
    
    # 1. Settings Table (One-time Sheet Link, Admin configs etc.)
    c.execute('''CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )''')
    
    # 2. Multi-Channels Table (Public & Private Channels)
    c.execute('''CREATE TABLE IF NOT EXISTS channels (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    chat_id TEXT UNIQUE NOT NULL,
                    channel_name TEXT DEFAULT '',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )''')
    
    # 3. Scheduled Posts Table
    c.execute('''CREATE TABLE IF NOT EXISTS posts (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    post_type TEXT NOT NULL,
                    content TEXT NOT NULL,
                    caption TEXT DEFAULT '',
                    entities TEXT DEFAULT '[]',
                    days TEXT NOT NULL,
                    times TEXT NOT NULL,
                    source TEXT DEFAULT 'manual',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    status TEXT DEFAULT 'active'
                )''')
    
    # Auto-Migration for existing databases
    try:
        c.execute("ALTER TABLE posts ADD COLUMN source TEXT DEFAULT 'manual'")
    except sqlite3.OperationalError:
        pass
    try:
        c.execute("ALTER TABLE posts ADD COLUMN entities TEXT DEFAULT '[]'")
    except sqlite3.OperationalError:
        pass
    
    # 4. Post Execution & Stats Logs Table
    c.execute('''CREATE TABLE IF NOT EXISTS post_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    post_id INTEGER,
                    posted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    status TEXT NOT NULL,
                    error_message TEXT DEFAULT ''
                )''')
    
    conn.commit()
    conn.close()

# ==================== SETTINGS CRUD ====================

def get_setting(key: str, default: str = None) -> str:
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT value FROM settings WHERE key=?", (key,))
    row = c.fetchone()
    conn.close()
    return row["value"] if row else default

def set_setting(key: str, value: str):
    conn = get_connection()
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, str(value)))
    conn.commit()
    conn.close()

# ==================== MULTI-CHANNELS CRUD ====================

def add_channel(chat_id: str, channel_name: str = "") -> bool:
    """Naya channel (Public @username ya Private ID) add karta hai."""
    conn = get_connection()
    c = conn.cursor()
    try:
        c.execute("INSERT INTO channels (chat_id, channel_name) VALUES (?, ?)", (chat_id, channel_name))
        conn.commit()
        success = True
    except sqlite3.IntegrityError:
        success = False  # Already exists
    conn.close()
    return success

def remove_channel(channel_id: int) -> bool:
    """Channel ID ke hisaab se channel remove karta hai."""
    conn = get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM channels WHERE id=?", (channel_id,))
    deleted = c.rowcount > 0
    conn.commit()
    conn.close()
    return deleted

def get_all_channels():
    """Saare registered channels ki list return karta hai."""
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM channels ORDER BY id ASC")
    rows = c.fetchall()
    conn.close()
    return rows

def count_channels() -> int:
    """Total active channels count karta hai."""
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) AS total FROM channels")
    count = c.fetchone()["total"]
    conn.close()
    return count

# ==================== POSTS CRUD ====================

def add_post(post_type: str, content: str, caption: str, entities: str, days: str, times: str, source: str = "manual") -> int:
    conn = get_connection()
    c = conn.cursor()
    c.execute('''INSERT INTO posts (post_type, content, caption, entities, days, times, source)
                 VALUES (?, ?, ?, ?, ?, ?, ?)''',
              (post_type, content, caption, entities, days, times, source))
    conn.commit()
    post_id = c.lastrowid
    conn.close()
    return post_id

def clear_sheet_posts():
    """Purani Google Sheet posts ko delete karta hai taaki auto-sync pe fresh data aaye bina duplicates ke."""
    conn = get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM posts WHERE source='sheet'")
    conn.commit()
    conn.close()

def get_active_posts():
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM posts WHERE status='active' ORDER BY id DESC")
    rows = c.fetchall()
    conn.close()
    return rows

def delete_post(post_id: int) -> bool:
    conn = get_connection()
    c = conn.cursor()
    c.execute("DELETE FROM posts WHERE id=?", (post_id,))
    deleted = c.rowcount > 0
    conn.commit()
    conn.close()
    return deleted

def count_active_posts() -> int:
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) AS total FROM posts WHERE status='active'")
    count = c.fetchone()["total"]
    conn.close()
    return count

def log_post_execution(post_id: int, status: str, error_message: str = ""):
    conn = get_connection()
    c = conn.cursor()
    c.execute('''INSERT INTO post_logs (post_id, status, error_message)
                 VALUES (?, ?, ?)''', (post_id, status, error_message))
    conn.commit()
    conn.close()