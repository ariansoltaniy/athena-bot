import sqlite3
import logging
import random
from datetime import datetime, time
from contextlib import contextmanager
from pytz import timezone
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
from telegram.error import TelegramError

# ====== 🎨 تنظیمات و لاگینگ ======
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

TOKEN = '8243652882:AAHRqQAvGczyooTy8WB6U6YLmk9CXgfTpJE'
WATCHER_ID = 141472605   # 👀 آریان (ناظر)
TARGET_ID = 104164928    # 🎯 آتنا (هدف)
DB_PATH = 'athena_data.db'  # 🗄️ نام دیتابیس
TZ_IR = timezone('Asia/Tehran')

# ====== 💬 پیام‌های متنوع ======
QUESTION_MESSAGES = [
    "سلام آتنا جون ✨ امروز مغازه رفتی؟",
    "هی آتنا 💫 امروز چطور بود؟ مغازه رفتی؟",
    "سلام قهرمان 🌟 امروز به مغازه سر زدی؟",
    "آتنای عزیز 💎 امروز هم رفتی مغازه؟",
]

SUCCESS_MESSAGES = [
    "آفرین آتنا! 🎉 استریکت شد {} روزه 💪",
    "عالیییی! 🌟 {} روز پشت سر هم 🔥",
    "دمت گرم آتنا! 💫 {} روزه که داری ادامه میدی 🚀",
    "یالااا! 🎊 {} روز تمام 💎",
]

MILESTONE_MESSAGES = {
    5: "🎯 ۵ روز تموم! داری خفن میشی 💪",
    10: "🔥 ۱۰ روز! نیمه راه برای هدف بزرگتر 🚀",
    15: "⭐ ۱۵ روز! حرف نداری آتنا 💎",
    20: "🏆 ۲۰ روز! افسانه‌ای شدی 👑",
    30: "👑 یک ماه کامل! قهرمان واقعی 🌟",
}

# ====== 🗄️ مدیریت دیتابیس ======
@contextmanager
def get_db():
    conn = sqlite3.connect(DB_PATH)
    try:
        yield conn
        conn.commit()
    except Exception as e:
        conn.rollback()
        logger.error(f"Database error: {e}")
        raise
    finally:
        conn.close()


def init_db():
    """ساخت جداول اولیه"""
    with get_db() as conn:
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS streak (
                id INTEGER PRIMARY KEY,
                streak INTEGER DEFAULT 0,
                last_answer TEXT DEFAULT NULL,
                best_streak INTEGER DEFAULT 0
            )
        """)
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                date TEXT,
                went_to_shop BOOLEAN,
                timestamp TEXT
            )
        """)
        
        cursor.execute(
            "INSERT OR IGNORE INTO streak (id, streak, best_streak) VALUES (?, ?, ?)", 
            (TARGET_ID, 0, 0)
        )
        
        logger.info("✅ Database initialized successfully")


def get_streak_data():
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT streak, last_answer, best_streak FROM streak WHERE id=?", 
            (TARGET_ID,)
        )
        return cursor.fetchone()


def update_streak(new_streak: int, answer_date: str):
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT best_streak FROM streak WHERE id=?", (TARGET_ID,))
        best = cursor.fetchone()[0]
        
        if new_streak > best:
            best = new_streak
            logger.info(f"🎉 New record! Best streak: {best}")
        
        cursor.execute(
            "UPDATE streak SET streak=?, last_answer=?, best_streak=? WHERE id=?",
            (new_streak, answer_date, best, TARGET_ID)
        )


def add_history(went: bool):
    with get_db() as conn:
        cursor = conn.cursor()
        now = datetime.now(TZ_IR)
        cursor.execute(
            "INSERT INTO history (user_id, date, went_to_shop, timestamp) VALUES (?, ?, ?, ?)",
            (TARGET_ID, now.date().isoformat(), went, now.isoformat())
        )


# ====== 🚀 دستورات ======
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    
    if user_id == TARGET_ID:
        data = get_streak_data()
        streak = data[0] if data else 0
        await update.message.reply_text(
            f"سلام آتنا جون! 💎\n\n"
            f"🔥 استریک فعلی: {streak} روز\n"
            f"⏰ هر روز ساعت ۹ شب ازت می‌پرسم\n\n"
            f"📊 /mystats - برای دیدن آمار"
        )
    elif user_id == WATCHER_ID:
        await update.message.reply_text(
            "سلام آریان! 👀\n\n"
            "📊 /status - وضعیت کامل\n"
            "📜 /history - تاریخچه\n"
            "🔔 /test_question - تست"
        )
    else:
        await update.message.reply_text("این بات مخصوص آتنا و آریانه 😊")


async def my_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    
    if user_id != TARGET_ID:
        await update.message.reply_text("این دستور فقط برای آتناست 💎")
        return
    
    try:
        data = get_streak_data()
        streak, last_answer, best = data
        
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT COUNT(*) FROM history WHERE user_id=? AND went_to_shop=1",
                (TARGET_ID,)
            )
            total_success = cursor.fetchone()[0]
        
        await update.message.reply_text(
            f"📊 **آمار تو:**\n\n"
            f"🔥 استریک: **{streak}** روز\n"
            f"🏆 رکورد: **{best}** روز\n"
            f"✅ مجموع: **{total_success}** روز\n"
            f"📅 آخرین: {last_answer or 'هنوز پاسخی ندادی'}",
            parse_mode='Markdown'
        )
    except Exception as e:
        logger.error(f"Error in my_stats: {e}")
        await update.message.reply_text("⚠️ خطا در دریافت اطلاعات")


async def daily_question(context: ContextTypes.DEFAULT_TYPE):
    try:
        current_time = datetime.now(TZ_IR)
        logger.info(f"⏰ Sending daily question at {current_time}")
        
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE streak SET last_answer=NULL WHERE id=?", (TARGET_ID,))
        
        keyboard = [
            [InlineKeyboardButton("✅ بله، رفتم", callback_data="yes")],
            [InlineKeyboardButton("❌ نه، نرفتم", callback_data="no")],
            [InlineKeyboardButton("📊 استریک من", callback_data="show_streak")]
        ]
        
        await context.bot.send_message(
            chat_id=TARGET_ID,
            text=random.choice(QUESTION_MESSAGES),
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        logger.info("✉️ Daily question sent")
    except TelegramError as e:
        logger.error(f"Failed to send: {e}")


async def check_no_response(context: ContextTypes.DEFAULT_TYPE):
    try:
        current_time = datetime.now(TZ_IR)
        logger.info(f"⏰ Checking response at {current_time}")
        
        data = get_streak_data()
        
        if data and data[1] is None:
            old_streak = data[0]
            update_streak(0, None)
            add_history(False)
            
            await context.bot.send_message(
                chat_id=TARGET_ID,
                text=f"😢 پاسخ ندادی... استریک از {old_streak} به صفر رسید"
            )
            await context.bot.send_message(
                chat_id=WATCHER_ID,
                text=f"⚠️ آتنا پاسخ نداد\n📉 {old_streak} → 0"
            )
            logger.warning(f"🔄 Streak reset (was {old_streak})")
        else:
            logger.info("✅ آتنا has responded")
    except Exception as e:
        logger.error(f"Error checking: {e}")


async def test_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    
    if user_id != WATCHER_ID:
        await update.message.reply_text("فقط برای ناظر 👀")
        return
    
    await daily_question(context)
    await update.message.reply_text("✅ سؤال تستی ارسال شد")


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    uid = query.from_user.id
    
    if uid != TARGET_ID:
        await query.answer("این دکمه برای آتناست 😉", show_alert=True)
        return
    
    await query.answer()
    
    try:
        action = query.data
        
        if action == "show_streak":
            data = get_streak_data()
            streak, _, best = data
            await query.edit_message_text(
                f"📊 وضعیت:\n\n🔥 استریک: {streak}\n🏆 رکورد: {best}"
            )
            return
        
        now = datetime.now(TZ_IR).date()
        data = get_streak_data()
        streak = data[0]
        
        if action == "yes":
            streak += 1
            update_streak(streak, now.isoformat())
            add_history(True)
            
            await query.edit_message_text(
                random.choice(SUCCESS_MESSAGES).format(streak)
            )
            
            await context.bot.send_message(
                chat_id=WATCHER_ID,
                text=f"✅ آتنا رفت مغازه\n🔥 استریک: {streak}"
            )
            
            if streak in MILESTONE_MESSAGES:
                milestone = MILESTONE_MESSAGES[streak]
                await context.bot.send_message(chat_id=TARGET_ID, text=milestone)
                await context.bot.send_message(
                    chat_id=WATCHER_ID, 
                    text=f"🎊 {streak} روز! {milestone}"
                )
            
            logger.info(f"✅ Positive answer — Streak: {streak}")
            
        else:
            old_streak = streak
            update_streak(0, now.isoformat())
            add_history(False)
            
            await query.edit_message_text(
                f"😔 استریک از {old_streak} به صفر رسید\n"
                f"فردا دوباره شروع! 💪"
            )
            
            await context.bot.send_message(
                chat_id=WATCHER_ID,
                text=f"❌ آتنا نرفت\n📉 {old_streak} → 0"
            )
            
            logger.info(f"❌ Negative answer — Reset (was {old_streak})")
            
    except Exception as e:
        logger.error(f"Button error: {e}")
        await query.edit_message_text("⚠️ خطا رخ داد")


async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    
    if user_id != WATCHER_ID:
        await update.message.reply_text("فقط برای ناظر 👀")
        return
    
    try:
        data = get_streak_data()
        streak, last_answer, best = data
        
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT COUNT(*) FROM history WHERE user_id=? AND went_to_shop=1",
                (TARGET_ID,)
            )
            total = cursor.fetchone()[0]
        
        current = datetime.now(TZ_IR).strftime('%Y-%m-%d %H:%M:%S')
        
        await update.message.reply_text(
            f"📊 **گزارش آتنا**\n\n"
            f"🔥 استریک: **{streak}**\n"
            f"🏆 رکورد: **{best}**\n"
            f"✅ مجموع: **{total}**\n"
            f"📅 آخرین: {last_answer or 'ندارد'}\n"
            f"⏰ تهران: {current}",
            parse_mode='Markdown'
        )
    except Exception as e:
        logger.error(f"Status error: {e}")
        await update.message.reply_text("⚠️ خطا")


async def history_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    
    if user_id != WATCHER_ID:
        await update.message.reply_text("فقط برای ناظر 👀")
        return
    
    try:
        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT date, went_to_shop FROM history WHERE user_id=? ORDER BY date DESC LIMIT 7",
                (TARGET_ID,)
            )
            records = cursor.fetchall()
        
        if not records:
            await update.message.reply_text("هنوز تاریخچه ندارد")
            return
        
        history_text = "📜 **تاریخچه ۷ روز:**\n\n"
        for rec_date, went in records:
            emoji = "✅" if went else "❌"
            history_text += f"{emoji} {rec_date}\n"
        
        await update.message.reply_text(history_text, parse_mode='Markdown')
    except Exception as e:
        logger.error(f"History error: {e}")
        await update.message.reply_text("⚠️ خطا")


async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    text = update.message.text.lower()
    
    if user_id == TARGET_ID:
        if any(w in text for w in ['سلام', 'هی', 'hi', 'hello']):
            await update.message.reply_text("سلام آتنا! 💎\n📊 /mystats")
        elif 'استریک' in text or 'streak' in text:
            data = get_streak_data()
            streak = data[0] if data else 0
            await update.message.reply_text(f"🔥 استریک: {streak} روز")
        else:
            await update.message.reply_text("برای راهنما /start بزن 😊")
    elif user_id == WATCHER_ID:
        await update.message.reply_text("سلام آریان! 👀\n/start")
    else:
        await update.message.reply_text("مخصوص آتنا و آریان 😊")


# ====== 🚀 اصلی ======
def main():
    init_db()
    
    app = ApplicationBuilder().token(TOKEN).build()
    
    # هندلرها
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("mystats", my_stats))
    app.add_handler(CommandHandler("status", status))
    app.add_handler(CommandHandler("history", history_command))
    app.add_handler(CommandHandler("test_question", test_question))
    app.add_handler(CallbackQueryHandler(button_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    
    # زمان‌بندی
    job_queue = app.job_queue
    
    job_queue.run_daily(
        daily_question,
        time=time(21, 0),
        days=(0, 1, 2, 3, 4, 5, 6),
        name="daily_question"
    )
    
    job_queue.run_daily(
        check_no_response,
        time=time(23, 0),
        days=(0, 1, 2, 3, 4, 5, 6),
        name="check_no_response"
    )
    
    current = datetime.now(TZ_IR).strftime('%Y-%m-%d %H:%M:%S')
    
    logger.info("=" * 50)
    logger.info("🤖 AthenaBot started!")
    logger.info(f"⏰ Tehran time: {current}")
    logger.info("📅 Schedule: 21:00 & 23:00")
    logger.info("=" * 50)
    
    # ✅ اصلاح شده
    app.run_polling(drop_pending_updates=True)


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        logger.info("👋 Stopped by user")
    except Exception as e:
        logger.critical(f"💥 Fatal: {e}")
        raise
