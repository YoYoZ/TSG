
"""
Telegram Bot for Yasno Outages - WITH PERSISTENT STORAGE
"""

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import logging
from yasno_api import YasnoAPI
from database import UserDatabase
from schedule_analyzer import ScheduleAnalyzer
import os

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

calculating_chats = set()


class YasnoBotV2:
    """Enhanced Telegram bot for Yasno outages"""

    def __init__(self, token: str, db_path: str = "/app/data/users.db"):
        """Initialize bot"""
        self.token = token
        self.db = UserDatabase(db_path)  # Persistent storage!
        self.api = YasnoAPI(city="kyiv")

        self.app = Application.builder().token(token).build()

        self.app.add_handler(CommandHandler("start", self.start_command))
        self.app.add_handler(CommandHandler("help", self.help_command))
        self.app.add_handler(CommandHandler("register", self.register_command))
        self.app.add_handler(CommandHandler("calculate", self.calculate_command))
        self.app.add_handler(CommandHandler("users", self.users_command))
        self.app.add_handler(CommandHandler("unregister", self.unregister_command))
        self.app.add_handler(CommandHandler("debug", self.debug_command))

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        welcome_text = (
            "👋 Привіт! Я бот для аналізу графіків відключень електроенергії Yasno.\n\n"
            "Мої можливості:\n"
            "• 📝 /register <група> <ім'я> - зареєструватися\n"
            "• 🔍 /calculate - знайти час, коли в усіх є світло\n"
            "• 👥 /users - список учасників\n"
            "• ❌ /unregister - видалити себе\n"
            "• ❓ /help - справка\n"
            "• 🔧 /debug - debug інформація\n\n"
            "Приклад: /register 1.1 Іван"
        )
        await update.message.reply_text(welcome_text)

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        help_text = (
            "📚 Довідка команд:\n\n"
            "🔐 Реєстрація:\n"
            "/register <група> <ім'я> - зареєструватися в цій групі\n"
            "Приклади груп: 1.1, 1.2, 2.1, 2.2, 3.1, 3.2, итд\n\n"

            "📊 Аналіз:\n"
            "/calculate - знайти період, коли у всіх світло\n\n"

            "👥 Управління:\n"
            "/users - список зареєстрованих учасників\n"
            "/unregister - видалити себе з чату\n\n"

            "🔧 DEBUG:\n"
            "/debug - виводить debug інформацію\n\n"

            "💾 Дані зберігаються автоматично!"
        )
        await update.message.reply_text(help_text)

    async def register_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /register <group> <name> command"""
        if not context.args or len(context.args) < 2:
            await update.message.reply_text(
                "❌ Неправильний формат команди.\n"
                "Використовуй: /register <група> <ім'я>\n"
                "Приклад: /register 1.1 Іван"
            )
            return

        group = context.args[0]
        name = " ".join(context.args[1:])

        chat_id = update.message.chat_id
        user_id = update.message.from_user.id

        if self.db.register_user(chat_id, user_id, name, group):
            await update.message.reply_text(
                f"✅ Привіт, {name}!\n"
                f"Ти зареєстрований у групі {group}\n"
                f"Дані збережені на сервері! 💾\n"
                f"Тепер використовуй /calculate для аналізу"
            )
        else:
            await update.message.reply_text(
                f"❌ Помилка при реєстрації.\n"
                f"Перевір, чи група {group} у правильному форматі (наприклад, 1.1)"
            )

    async def debug_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Debug command"""
        chat_id = update.message.chat_id
        users = self.db.get_chat_users(chat_id)

        if not users:
            await update.message.reply_text("Нет пользователей в этом чате")
            return

        debug_text = "🔧 DEBUG INFO:\n\n"

        for user in users:
            try:
                schedule = self.api.get_outages_for_group(group=user["group"])
                debug_text += f"Пользователь: {user['username']} (группа {user['group']})\n"

                today_outages = schedule["today"]["outages"]
                debug_text += f"  Сегодня отключения (Definite) ({len(today_outages)}):\n"
                for outage in today_outages:
                    start_h = outage['start_hour']
                    end_h = outage['end_hour']
                    debug_text += f"    {start_h:.2f} - {end_h:.2f}\n"

                electricity_periods = ScheduleAnalyzer.get_electricity_periods(today_outages)
                debug_text += f"  Сегодня свет ({len(electricity_periods)} периодов):\n"
                for start, end in electricity_periods:
                    debug_text += f"    {ScheduleAnalyzer.minutes_to_hhmm(start)} - {ScheduleAnalyzer.minutes_to_hhmm(end)}\n"

                debug_text += "\n"
            except Exception as e:
                debug_text += f"❌ Ошибка для {user['username']}: {e}\n\n"

        if len(debug_text) > 4000:
            for i in range(0, len(debug_text), 4000):
                await update.message.reply_text(debug_text[i:i+4000])
        else:
            await update.message.reply_text(debug_text)

    async def calculate_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /calculate command"""
        chat_id = update.message.chat_id

        if chat_id in calculating_chats:
            logger.debug(f"Пропускаем дублирующийся /calculate для чата {chat_id}")
            return

        calculating_chats.add(chat_id)

        try:
            users = self.db.get_chat_users(chat_id)

            if not users:
                await update.message.reply_text(
                    "❌ У цьому чаті ніхто не зареєстрований!\n"
                    "Використовуй /register <група> <ім'я> для реєстрації"
                )
                return

            if len(users) == 1:
                await update.message.reply_text(
                    "⚠️ Потрібно щонайменше 2 учасники для аналізу"
                )
                return

            loading_msg = await update.message.reply_text("⏳ Аналізую графіки...")

            schedules_today = []
            schedules_tomorrow = []
            errors = []

            logger.info(f"Начинаем получение расписаний для {len(users)} пользователей")

            for user in users:
                try:
                    logger.info(f"Получаем расписание для {user['username']} (группа {user['group']})")
                    schedule = self.api.get_outages_for_group(group=user["group"])

                    logger.debug(f"  Сегодня: {len(schedule['today']['outages'])} отключений (Definite)")
                    logger.debug(f"  Завтра: {len(schedule['tomorrow']['outages'])} отключений (Definite)")

                    schedules_today.append({
                        "user_id": user["user_id"],
                        "username": user["username"],
                        "group": user["group"],
                        "outages": schedule["today"]["outages"]
                    })

                    schedules_tomorrow.append({
                        "user_id": user["user_id"],
                        "username": user["username"],
                        "group": user["group"],
                        "outages": schedule["tomorrow"]["outages"]
                    })

                except Exception as e:
                    error_msg = f"Користувач {user['username']}: {str(e)}"
                    logger.error(error_msg, exc_info=True)
                    errors.append(error_msg)
                    continue

            logger.info(f"Получено расписаний для {len(schedules_today)} пользователей")

            if len(schedules_today) < 2:
                error_text = "❌ Не удалось получить расписание для пользователей:\n"
                for error in errors[:3]:
                    error_text += f"  • {error}\n"
                await loading_msg.edit_text(error_text)
                return

            logger.info("Ищем пересечения сегодня...")
            common_today, _ = ScheduleAnalyzer.find_common_electricity_periods(schedules_today)
            logger.info(f"Найдено пересечений сегодня: {len(common_today)}")

            logger.info("Ищем пересечения завтра...")
            common_tomorrow, _ = ScheduleAnalyzer.find_common_electricity_periods(schedules_tomorrow)
            logger.info(f"Найдено пересечений завтра: {len(common_tomorrow)}")

            response_lines = ["👥 Учасники:"]
            for user in users:
                response_lines.append(f"  • {user['username']} (група {user['group']})")

            response_lines.append("")
            response_lines.append("════════════════════════════════════════")
            response_lines.append(ScheduleAnalyzer.format_report("🌅 СЬОГОДНІ", common_today))
            response_lines.append("")
            response_lines.append(ScheduleAnalyzer.format_report("🌙 ЗАВТРА", common_tomorrow))

            response_text = "\n".join(response_lines)
            logger.info(f"Отправляю результат")
            await loading_msg.edit_text(response_text)

        except Exception as e:
            logger.error(f"Error in calculate command: {e}", exc_info=True)
            try:
                await update.message.reply_text(
                    f"❌ Помилка при аналізі: {str(e)}"
                )
            except:
                pass

        finally:
            calculating_chats.discard(chat_id)

    async def users_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /users command"""
        chat_id = update.message.chat_id
        users = self.db.get_chat_users(chat_id)

        if not users:
            await update.message.reply_text("❌ У цьому чаті ніхто не зареєстрований")
            return

        response = "👥 Зареєстровані учасники:\n\n"
        for i, user in enumerate(users, 1):
            response += f"{i}. {user['username']} (група {user['group']})\n"

        await update.message.reply_text(response)

    async def unregister_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /unregister command"""
        chat_id = update.message.chat_id
        user_id = update.message.from_user.id

        user_data = self.db.get_user(chat_id, user_id)

        if not user_data:
            await update.message.reply_text("❌ Ти не зареєстрований у цьому чаті")
            return

        if self.db.delete_user(chat_id, user_id):
            await update.message.reply_text(
                f"✅ Ти видалений з групи {user_data['group']}"
            )
        else:
            await update.message.reply_text("❌ Помилка при видаленні")

    def run(self):
        """Run the bot"""
        logger.info("🤖 Бот запущено (з persistent storage)...")
        self.app.run_polling(allowed_updates=Update.ALL_TYPES)


def main():
    """Main entry point"""
    token = os.getenv("TELEGRAM_BOT_TOKEN")

    if not token:
        raise ValueError(
            "Помилка: TELEGRAM_BOT_TOKEN не встановлено!"
        )

    bot = YasnoBotV2(token=token)
    bot.run()


if __name__ == "__main__":
    main()
