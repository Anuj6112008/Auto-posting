import datetime
from database import get_connection
from config import TIMEZONE

def get_performance_stats() -> dict:
    """Database se Weekly, Monthly, Yearly aur Total stats calculate karta hai."""
    conn = get_connection()
    c = conn.cursor()
    
    # Current Time with Timezone
    now = datetime.datetime.now(TIMEZONE)
    
    # 1. Weekly Start Date (Current Week ka Monday)
    week_start = (now - datetime.timedelta(days=now.weekday())).strftime('%Y-%m-%d 00:00:00')
    
    # 2. Monthly Start Date (Current Month ki 1st date)
    month_start = now.strftime('%Y-%m-01 00:00:00')
    
    # 3. Yearly Start Date (Current Year ka Jan 1st)
    year_start = now.strftime('%Y-01-01 00:00:00')
    
    # Query Weekly Posts
    c.execute("SELECT COUNT(*) AS total FROM post_logs WHERE posted_at >= ? AND status='success'", (week_start,))
    week_success = c.fetchone()["total"]
    
    # Query Monthly Posts
    c.execute("SELECT COUNT(*) AS total FROM post_logs WHERE posted_at >= ? AND status='success'", (month_start,))
    month_success = c.fetchone()["total"]
    
    # Query Yearly Posts
    c.execute("SELECT COUNT(*) AS total FROM post_logs WHERE posted_at >= ? AND status='success'", (year_start,))
    year_success = c.fetchone()["total"]
    
    # Lifetime Success & Failures
    c.execute("SELECT COUNT(*) AS total FROM post_logs WHERE status='success'")
    total_success = c.fetchone()["total"]
    
    c.execute("SELECT COUNT(*) AS total FROM post_logs WHERE status='failed'")
    total_failed = c.fetchone()["total"]
    
    conn.close()
    
    # Success Rate Percentage Calculation
    total_attempts = total_success + total_failed
    success_rate = (total_success / total_attempts * 100) if total_attempts > 0 else 100.0

    return {
        "week": week_success,
        "month": month_success,
        "year": year_success,
        "total": total_success,
        "failed": total_failed,
        "success_rate": round(success_rate, 2)
    }

def format_stats_message() -> str:
    """Admin ke padhne ke liye clean formatted message banata hai."""
    stats = get_performance_stats()
    
    text = (
        "📊 **AUTO-POSTING PERFORMANCE & STATS**\n"
        "───────────────────────────\n"
        f"📅 **This Week Sent:** `{stats['week']}` posts\n"
        f"🗓️ **This Month Sent:** `{stats['month']}` posts\n"
        f"📈 **This Year Sent:** `{stats['year']}` posts\n"
        "───────────────────────────\n"
        f"🚀 **Lifetime Success:** `{stats['total']}` posts\n"
        f"⚠️ **Total Failures/Errors:** `{stats['failed']}`\n"
        f"🎯 **Overall Success Rate:** `{stats['success_rate']}%`\n"
        "───────────────────────────"
    )
    return text