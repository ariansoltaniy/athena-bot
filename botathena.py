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
WATCHER_ID = 104164928   # 👀 آریان (ناظر)
TARGET_ID = 141472605    # 🎯 آتنا (هدف)
DB_PATH = 'athena_data.db'
TZ_IR = timezone('Asia/Tehran')  # ⏰ تایم‌زون تهران

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

# ====== 🗄️ مدیریت دیتابیس با Context Manager ======
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
    """ساخت جداول اولیه دیتابیس"""
    with get_db() as conn:
        cursor = conn.cursor()

        # جدول استریک
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS streak (
                id INTEGER PRIMARY KEY,
                streak INTEGER DEFAULT 0,
                last_answer TEXT DEFAULT NULL,
                best_streak INTEGER DEFAULT 0
            )
        """)

        # جدول تاریخچه
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


# ====== 📊 توابع دیتابیس ======
def get_streak_data():
    """دریافت اطلاعات استریک"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT streak, last_answer, best_streak FROM streak WHERE id=?",
            (TARGET_ID,)
        )
        return cursor.fetchone()


def update_streak(new_streak: int, answer_date: str):
    """به‌روزرسانی استریک"""
    with get_db() as conn:
        cursor = conn.cursor()
        cursor.execute(
            "SELECT best_streak FROM streak WHERE id=?",
            (TARGET_ID,)
        )
        best = cursor.fetchone()[0]

        # آپدیت بهترین استریک
        if new_streak > best:
            best = new_streak
            logger.info(f"🎉 New record! Best streak: {best}")

        cursor.execute(
            "UPDATE streak SET streak=?, last_answer=?, best_streak=? WHERE id=?",
            (new_streak, answer_date, best, TARGET_ID)
        )


def add_history(went: bool):
    """ذخیره در تاریخچه"""
    with get_db() as conn:
        cursor = conn.cursor()
        now = datetime.now(TZ_IR)
        cursor.execute(
            "INSERT INTO history (user_id, date, went_to_shop, timestamp) VALUES (?, ?, ?, ?)",
            (TARGET_ID, now.date().isoformat(), went, now.isoformat())
        )


# ====== 🚀 دستورات بات ======
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """دستور /start"""
    user_id = update.message.chat_id

    if user_id == TARGET_ID:
        data = get_streak_data()
        streak = data[0] if data else 0

        await update.message.reply_text(
            f"سلام آتنا جون! 💎\n\n"
            f"🔥 استریک فعلی: {streak} روز\n"
            f"⏰ هر روز ساعت ۹ شب ازت می‌پرسم مغازه رفتی یا نه\n\n"
            f"برای دیدن استریکت می‌تونی /mystats بزنی 📊"
        )
    elif user_id == WATCHER_ID:
        await update.message.reply_text(
            "سلام آریان! 👀\n\n"
            "دستورات ناظر:\n"
            "📊 /status - وضعیت کامل\n"
            "📜 /history - تاریخچه ۷ روز گذشته\n"
            "🔔 /test_question - تست ارسال سؤال (فقط برای تست)"
        )
    else:
        await update.message.reply_text(
            "سلام! این بات مخصوص آتنا و آریانه 😊"
        )


async def my_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش آمار شخصی آتنا"""
    if update.message.chat_id != TARGET_ID:
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

        stats_text = (
            f"📊 **آمار تو آتنا:**\n\n"
            f"🔥 استریک فعلی: **{streak}** روز\n"
            f"🏆 بهترین رکوردت: **{best}** روز\n"
            f"✅ مجموع روزهای موفق: **{total_success}** روز\n"
            f"📅 آخرین پاسخ: {last_answer if last_answer else 'هنوز پاسخی نداده‌ای'}\n\n"
            f"💪 بزن بریم قهرمان!"
        )

        await update.message.reply_text(stats_text, parse_mode='Markdown')

    except Exception as e:
        logger.error(f"Error in my_stats: {e}")
        await update.message.reply_text("⚠️ خطا در دریافت اطلاعات")


# ====== 📨 ارسال پیام روزانه (۲۱:۰۰ تهران) ======
async def daily_question(context: ContextTypes.DEFAULT_TYPE):
    """ارسال سؤال شبانه - ساعت 21:00 به وقت تهران"""
    try:
        current_time = datetime.now(TZ_IR)
        logger.info(f"⏰ Sending daily question at {current_time.strftime('%Y-%m-%d %H:%M:%S')} Tehran time")

        with get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("UPDATE streak SET last_answer=NULL WHERE id=?", (TARGET_ID,))

        keyboard = [
            [InlineKeyboardButton("✅ بله، رفتم", callback_data="yes")],
            [InlineKeyboardButton("❌ نه، نرفتم", callback_data="no")],
            [InlineKeyboardButton("📊 استریک من", callback_data="show_streak")]
        ]

        message = random.choice(QUESTION_MESSAGES)

        await context.bot.send_message(
            chat_id=TARGET_ID,
            text=message,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

        logger.info("✉️ Daily question sent to آتنا")

    except TelegramError as e:
        logger.error(f"Failed to send daily question: {e}")


# ====== ⏰ بررسی عدم پاسخ (۲۳:۰۰ تهران) ======
async def check_no_response(context: ContextTypes.DEFAULT_TYPE):
    """بررسی اگر پاسخ نداده باشد - ساعت 23:00 به وقت تهران"""
    try:
        current_time = datetime.now(TZ_IR)
        logger.info(f"⏰ Checking for no response at {current_time.strftime('%Y-%m-%d %H:%M:%S')} Tehran time")

        data = get_streak_data()

        if data and data[1] is None:  # اگر پاسخ نداده
            old_streak = data[0]
            update_streak(0, None)
            add_history(False)

            await context.bot.send_message(
                chat_id=TARGET_ID,
                text=f"😢 پاسخ ندادی... استریک از {old_streak} روز به صفر رسید.\nفردا جبران می‌کنیم! 💪"
            )

            await context.bot.send_message(
                chat_id=WATCHER_ID,
                text=f"⚠️ آتنا امروز پاسخ نداد.\n📉 استریک: {old_streak} → 0"
            )

            logger.warning(f"🔄 Streak reset due to no response (was {old_streak})")
        else:
            logger.info("✅ آتنا has already responded today")

    except Exception as e:
        logger.error(f"Error in check_no_response: {e}")


# ====== 🧪 تست دستی (فقط برای ناظر) ======
async def test_question(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """ارسال سؤال تستی (فقط برای ناظر)"""
    if update.message.chat_id != WATCHER_ID:
        await update.message.reply_text("این دستور فقط برای ناظره 👀")
        return

    await daily_question(context)
    await update.message.reply_text("✅ سؤال تستی ارسال شد")


# ====== 🎯 مدیریت دکمه‌ها ======
async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """مدیریت کلیک روی دکمه‌ها"""
    query = update.callback_query
    uid = query.from_user.id

    if uid != TARGET_ID:
        await query.answer("این دکمه برای آتناست 😉", show_alert=True)
        return

    await query.answer()

    try:
        action = query.data

        # نمایش استریک
        if action == "show_streak":
            data = get_streak_data()
            streak, _, best = data[0], data[1], data[2]

            status_text = (
                f"📊 وضعیت استریک آتنا:\n\n"
                f"🔥 استریک فعلی: {streak} روز\n"
                f"🏆 بهترین رکورد: {best} روز\n"
                f"💪 به همین روال ادامه بده!"
            )

            await query.edit_message_text(status_text)
            return

        # پاسخ بله یا نه
        now = datetime.now(TZ_IR).date()
        data = get_streak_data()
        streak = data[0]

        if action == "yes":
            streak += 1
            update_streak(streak, now.isoformat())
            add_history(True)

            success_msg = random.choice(SUCCESS_MESSAGES).format(streak)
            await query.edit_message_text(success_msg)

            # پیام به ناظر
            await context.bot.send_message(
                chat_id=WATCHER_ID,
                text=f"✅ آتنا امروز رفت مغازه\n🔥 استریک: {streak} روز"
            )

            # بررسی سنگ‌های میانی (Milestones)
            if streak in MILESTONE_MESSAGES:
                milestone_msg = MILESTONE_MESSAGES[streak]
                await context.bot.send_message(chat_id=TARGET_ID, text=milestone_msg)
                await context.bot.send_message(
                    chat_id=WATCHER_ID,
                    text=f"🎊 آتنا به {streak} روز رسید! {milestone_msg}"
                )

            logger.info(f"✅ آتنا پاسخ مثبت داد — Streak: {streak}")

        else:  # no
            old_streak = streak
            update_streak(0, now.isoformat())
            add_history(False)

            await query.edit_message_text(
                f"😔 استریک از {old_streak} روز به صفر رسید.\n"
                f"اشکال نداره آتنا! فردا دوباره شروع می‌کنیم 💪"
            )

            await context.bot.send_message(
                chat_id=WATCHER_ID,
                text=f"❌ آتنا امروز نرفت مغازه\n📉 استریک: {old_streak} → 0"
            )

            logger.info(f"❌ آتنا پاسخ منفی داد — Streak reset (was {old_streak})")

    except Exception as e:
        logger.error(f"Error in button_callback: {e}")
        await query.edit_message_text("⚠️ خطایی رخ داد. دوباره تلاش کن.")


# ====== 📊 دستور /status (برای ناظر) ======
async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش وضعیت کامل (فقط برای ناظر)"""
    if update.message.chat_id != WATCHER_ID:
        await update.message.reply_text("این دستور مخصوص ناظره 👀")
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

        current_time = datetime.now(TZ_IR).strftime('%Y-%m-%d %H:%M:%S')

        status_text = (
            f"📊 **گزارش وضعیت آتنا**\n\n"
            f"🔥 استریک فعلی: **{streak}** روز\n"
            f"🏆 بهترین رکورد: **{best}** روز\n"
            f"✅ مجموع روزهای موفق: **{total_success}** روز\n"
            f"📅 آخرین پاسخ: {last_answer if last_answer else 'هنوز پاسخی نداده'}\n"
            f"⏰ زمان فعلی تهران: {current_time}\n"
        )

        await update.message.reply_text(status_text, parse_mode='Markdown')

    except Exception as e:
        logger.error(f"Error in status command: {e}")
        await update.message.reply_text("⚠️ خطا در دریافت اطلاعات")


# ====== 📜 دستور /history (برای ناظر) ======
async def history_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """نمایش ۷ روز گذشته"""
    if update.message.chat_id != WATCHER_ID:
        await update.message.reply_text("این دستور مخصوص ناظره 👀")
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
            await update.message.reply_text("هنوز تاریخچه‌ای ثبت نشده")
            return

        history_text = "📜 **تاریخچه ۷ روز گذشته:**\n\n"
        for rec_date, went in records:
            emoji = "✅" if went else "❌"
            history_text += f"{emoji} {rec_date}\n"

        await update.message.reply_text(history_text, parse_mode='Markdown')

    except Exception as e:
        logger.error(f"Error in history command: {e}")
        await update.message.reply_text("⚠️ خطا در دریافت تاریخچه")


# ====== 💬 پاسخ به پیام‌های عادی ======
async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """پاسخ به متن‌های عادی"""
    user_id = update.message.chat_id
    text = update.message.text.lower()

    if user_id == TARGET_ID:
        if any(word in text for word in ['سلام', 'هلو', 'هی', 'hi', 'hello']):
            await update.message.reply_text(
                "سلام آتنا جون! 💎\n"
                "برای دیدن آمارت /mystats بزن 📊"
            )
        elif 'استریک' in text or 'streak' in text:
            data = get_streak_data()
            streak = data[0] if data else 0
            await update.message.reply_text(f"🔥 استریک فعلیت: {streak} روز")
        else:
            await update.message.reply_text(
                "برای دیدن دستورات /start بزن 😊"
            )
    elif user_id == WATCHER_ID:
        await update.message.reply_text(
            "برای دیدن دستورات /start بزن 👀"
        )


# ====== 🚀 تابع اصلی ======
def main():
    """راه‌اندازی بات"""
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

    # دسترسی به job_queue برای زمان‌بندی
    job_queue = app.job_queue

    # ارسال سؤال روزانه - ساعت 21:00 تهران
    job_queue.run_daily(
        daily_question,
        time=time(21, 0),  # 21:00
        days=(0, 1, 2, 3, 4, 5, 6),
        name="daily_question"
    )

    # بررسی عدم پاسخ - ساعت 23:00 تهران
    job_queue.run_daily(
        check_no_response,
        time=time(23, 0),  # 23:00
        days=(0, 1, 2, 3, 4, 5, 6),
        name="check_no_response"
    )

    current_time = datetime.now(TZ_IR).strftime('%Y-%m-%d %H:%M:%S')

    logger.info("=" * 50)
    logger.info("🤖 AthenaBot started successfully!")
    logger.info(f"⏰ Current Tehran time: {current_time}")
    logger.info("📅 Schedule:")
    logger.info("   - Daily question: 21:00 Tehran time")
    logger.info("   - Check response: 23:00 Tehran time")
    logger.info("=" * 50)

    # اجرای بات
    app.run_polling(allowed_updates=Update.ALL_TYPES)


# ====== ▶️ اجرا ======
if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        logger.info("👋 Bot stopped by user")
    except Exception as e:
        logger.critical(f"💥 Fatal error: {e}")
