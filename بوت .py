#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import re
import logging
import subprocess
import importlib
import psutil
import time
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, Bot, InputFile
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackContext,
    CallbackQueryHandler,
    filters
)

# إعدادات البوت
CHANNEL_USERNAME = "Z3XHACK"  # معرف القناة بدون @
DEVELOPER_USERNAME = "Z_3_3_3_X"  # حساب المطور بدون @
TOKEN = "7634970889:AAHgmxcnIopSePZDcOB4dB_PVKYqLgmnxzQ"  # توكن البوت الأساسي
ADMIN_ID = 7756011232  # معرف الأدمن
BOTS_DIR = "bots"  # مجلد تخزين البوتات
LOG_FILE = "bot_hosting.log"  # ملف السجلات
REQUIREMENTS = ["python-telegram-bot", "psutil"]  # المتطلبات الأساسية

# إعداد نظام التسجيل (Logging)
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    filename=LOG_FILE
)
logger = logging.getLogger(__name__)

# متغيرات الحالة
upload_mode = False
running_bots = {}
bot_users = {}  # لتخزين معلومات مستخدمي البوتات
rejected_bots = {}  # لتخزين البوتات المرفوضة

async def is_user_subscribed(bot: Bot, user_id: int) -> bool:
    """التحقق من اشتراك المستخدم في القناة"""
    try:
        member = await bot.get_chat_member(chat_id=f"@{CHANNEL_USERNAME}", user_id=user_id)
        return member.status in ["member", "creator", "administrator"]
    except Exception as e:
        logger.error(f"خطأ في التحقق من الاشتراك: {str(e)}")
        return False

async def install_requirements():
    """تثبيت المتطلبات الأساسية تلقائياً"""
    for requirement in REQUIREMENTS:
        try:
            importlib.import_module(requirement.replace('-', '_'))
        except ImportError:
            logger.info(f"جاري تثبيت {requirement}...")
            subprocess.run([sys.executable, "-m", "pip", "install", requirement], check=True)

async def show_main_menu(update: Update, text: str = None):
    """عرض القائمة الرئيسية مع رسالة مخصصة"""
    global upload_mode
    upload_mode = False

    user = update.effective_user
    if user.id == ADMIN_ID:
        keyboard = [
            [InlineKeyboardButton("📤 رفع بوت جديد", callback_data='upload_bot')],
            [InlineKeyboardButton("📋 قائمة البوتات النشطة", callback_data='list_bots')],
            [InlineKeyboardButton("👑 لوحة التحكم الإداري", callback_data='admin_panel')],
            [InlineKeyboardButton("🛑 إيقاف جميع البوتات", callback_data='stop_all')],
            [InlineKeyboardButton("ℹ️ المساعدة", callback_data='help')],
            # السطر الجديد - الزرين في نفس الصف
            [
                InlineKeyboardButton("👨‍💻 المطور", url="https://t.me/Z_3_3_3_X"),
                InlineKeyboardButton("📢 قناة المطور", url="https://t.me/Z3XHACK")
            ]
        ]
    else:
        keyboard = [
            [InlineKeyboardButton("📤 رفع بوت جديد", callback_data='upload_bot')],
            [InlineKeyboardButton("📋 قائمة بوتاتي النشطة", callback_data='list_my_bots')],
            [InlineKeyboardButton("ℹ️ المساعدة", callback_data='help')],
            # السطر الجديد - الزرين في نفس الصف
            [
                InlineKeyboardButton("👨‍💻 المطور", url="https://t.me/Z_3_3_3_X"),
                InlineKeyboardButton("📢 قناة المطور", url="https://t.me/Z3XHACK")
            ]
        ]

    reply_markup = InlineKeyboardMarkup(keyboard)

    if hasattr(update, 'callback_query') and update.callback_query:
        await update.callback_query.edit_message_text(
            text or "اختر أحد الخيارات من القائمة:",
            reply_markup=reply_markup
        )
    elif hasattr(update, 'message'):
        await update.message.reply_text(
            text or "اختر أحد الخيارات من القائمة:",
            reply_markup=reply_markup
        )
    else:
        await update.edit_message_text(
            text or "اختر أحد الخيارات من القائمة:",
            reply_markup=reply_markup
        )
        
async def start(update: Update, context: CallbackContext):
    """يعرض رسالة الترحيب مع التحقق من الاشتراك الإجباري"""
    user = update.effective_user
    bot = context.bot

    # التحقق من الاشتراك في القناة
    if not await is_user_subscribed(bot, user.id):
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("📢 قناة المطور", url=f"https://t.me/{CHANNEL_USERNAME}")],
            [InlineKeyboardButton("🔄 تحقق من الاشتراك", callback_data="check_subscription")],
            [InlineKeyboardButton("👨‍💻 المطور", url=f"https://t.me/{DEVELOPER_USERNAME}")]
        ])
        await update.message.reply_text(
            "🚫 يجب عليك الاشتراك في قناة المطور لاستخدام البوت.\n"
            "📌 اضغط على الزر أدناه ثم تحقق من الاشتراك.",
            reply_markup=keyboard
        )
        return

    # إذا كان مشتركاً، عرض القائمة الرئيسية
    if user.id == ADMIN_ID:
        welcome_text = (
            f"مرحباً {user.first_name}!\n"
            "👑 أنت في وضع الأدمن - لديك جميع الصلاحيات\n"
            "✅ يمكنك استضافة البوتات والتحكم الكامل"
        )
    else:
        welcome_text = (
            f"""مرحباً  🫡{user.first_name}!\n 
 "✅أهلاً بك في بوت رفع واستضافة بوتات بايثون!
🎯 مهمة البوت:
- رفع وتشغيل بوتاتك البرمجية.

🚀 كيفية الاستخدام:
1. استخدم الأزرار للتنقل.
2. ارفع ملفك مع الالتزام بالشروط.
      
            " 🔏 نظام آمن لاستضافة بوتات التلجرام" """
        )

    await show_main_menu(update, welcome_text)

async def show_admin_panel(update: Update, context: CallbackContext):
    """عرض لوحة التحكم الإداري"""
    query = update.callback_query
    await query.answer()

    if query.from_user.id != ADMIN_ID:
        await query.edit_message_text("⛔ ليس لديك صلاحية الوصول لهذه اللوحة!")
        return

    admin_text = (
        "👑 لوحة التحكم الإداري\n\n"
        "✅ يمكنك من هنا:\n"
        "- مراقبة جميع البوتات النشطة\n"
        "- إرسال رسائل جماعية للمستخدمين\n"
        "- إدارة البوتات المرفوضة\n"
        "- تحميل ملفات البوتات الأصلية\n"
        "- التحكم الكامل في النظام"
    )

    keyboard = [
        [InlineKeyboardButton("📋 قائمة البوتات النشطة", callback_data='list_bots')],
        [InlineKeyboardButton("👥 إرسال رسالة جماعية", callback_data='broadcast')],
        [InlineKeyboardButton("⚠️ البوتات المرفوضة", callback_data='rejected_list')],
        [InlineKeyboardButton("🛑 إيقاف جميع البوتات", callback_data='stop_all')],
        [InlineKeyboardButton("🔙 القائمة الرئيسية", callback_data='back_to_main')]
    ]

    await query.edit_message_text(
        admin_text,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def notify_admin_new_bot(bot_file: str, user_id: int, username: str, file_id: str, file_path: str, context: CallbackContext):
    """إرسال إشعار للأدمن عن بوت جديد مع إمكانية تحميل الملف"""
    try:
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        message = (
            f"🆕 بوت جديد تم رفعه:\n"
            f"📝 اسم الملف: {bot_file}\n"
            f"👤 المستخدم: {username} (ID: {user_id})\n"
            f"🆔 ملف البوت: {file_id}\n"
            f"⏰ الوقت: {current_time}"
        )

        # تخزين معلومات المستخدم
        bot_users[bot_file] = {
            'user_id': user_id,
            'username': username,
            'file_id': file_id,
            'upload_time': current_time,
            'file_path': file_path
        }

        keyboard = [
            [
                InlineKeyboardButton("🛑 إيقاف هذا البوت", callback_data=f'stop_{bot_file}'),
                InlineKeyboardButton("📥 تحميل الملف الأصلي", callback_data=f'download_{bot_file}')
            ],
            [
                InlineKeyboardButton("⚠️ رفض البوت وإرسال تحذير", callback_data=f'reject_{bot_file}')
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        # إرسال الإشعار للأدمن
        await context.bot.send_message(
            chat_id=ADMIN_ID,
            text=message,
            reply_markup=reply_markup
        )

    except Exception as e:
        logger.error(f"فشل في إرسال إشعار البوت الجديد: {str(e)}")

async def handle_document(update: Update, context: CallbackContext):
    """يتعامل مع رفع ملفات البوتات"""
    global upload_mode

    if not upload_mode:
        await update.message.reply_text(
            "⏳ يرجى الضغط على زر '📤 رفع بوت جديد' أولاً",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("العودة للقائمة", callback_data='back_to_main')]])
        )
        return

    user = update.effective_user
    file = await update.message.document.get_file()
    file_name = update.message.document.file_name

    if not file_name.lower().endswith('.py'):
        await update.message.reply_text(
            "❌ يرجى إرسال ملف بوت بصيغة .py فقط",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("المحاولة مرة أخرى", callback_data='upload_bot')]])
        )
        upload_mode = False
        return

    # إنشاء مجلد البوتات إذا لم يكن موجوداً
    if not os.path.exists(BOTS_DIR):
        os.makedirs(BOTS_DIR)

    download_path = os.path.join(BOTS_DIR, file_name)

    try:
        # تحميل الملف
        await file.download_to_drive(download_path)

        # فحص وجود توكن في الملف
        found_token = await check_for_token(download_path)
        if not found_token:
            os.remove(download_path)
            await update.message.reply_text(
                "⚠️ لم يتم العثور على توكن بوت في الملف\n"
                "❌ يرجى إرسال ملف يحتوي على توكن بوت صحيح\n"
                "📌 مثال: TOKEN = '123456789:ABCdefGHIJKlmNoPQRsTUVwxyZ'\n\n"
                "يرجى المحاولة مرة أخرى:",
                reply_markup=InlineKeyboardMarkup([
                    [InlineKeyboardButton("إعادة المحاولة", callback_data='upload_bot')],
                    [InlineKeyboardButton("العودة للقائمة", callback_data='back_to_main')]
                ])
            )
            upload_mode = False
            return

        # منح صلاحيات التنفيذ
        os.chmod(download_path, 0o755)

        # تثبيت متطلبات البوت الجديد
        await install_bot_requirements(download_path)

        # تشغيل البوت في الخلفية مع إعادة المحاولة عند الفشل
        process = await run_bot_with_retry(download_path)

        # تسجيل البوت في القاموس
        running_bots[file_name] = {
            'process': process,
            'pid': process.pid,
            'user': user.id,
            'username': user.username or user.first_name,
            'path': download_path,
            'token': found_token,
            'file_id': update.message.document.file_id
        }

        # إرسال إشعار للأدمن إذا كان المستخدم ليس أدمن
        if user.id != ADMIN_ID:
            await notify_admin_new_bot(
                file_name,
                user.id,
                user.username or user.first_name,
                update.message.document.file_id,
                download_path,
                context
            )

        # إرسال رسالة النجاح
        success_text = (
            f"✅ تم رفع وتشغيل البوت بنجاح!\n"
            f"📝 اسم الملف: {file_name}\n"
        )

        await update.message.reply_text(
            success_text,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("العودة للقائمة", callback_data='back_to_main')]])
        )

        logger.info(f"تم رفع وتشغيل بوت جديد: {file_name} بواسطة {user.id}")

    except Exception as e:
        error_msg = f"❌ حدث خطأ أثناء رفع البوت: {str(e)}"
        await update.message.reply_text(
            error_msg,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("المحاولة مرة أخرى", callback_data='upload_bot')]])
        )
        logger.error(error_msg)
    finally:
        upload_mode = False

async def check_for_token(file_path):
    """فحص الملف لوجود توكن بوت تلجرام"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

            # البحث عن توكن بوت تلجرام
            token_pattern = r'[0-9]{9,11}:[a-zA-Z0-9_-]{35}'
            matches = re.findall(token_pattern, content)

            if matches:
                return matches[0]  # إرجاع أول توكن موجود
            return None

    except Exception as e:
        logger.error(f"خطأ في فحص التوكن: {str(e)}")
        return None

async def install_bot_requirements(bot_path):
    """اكتشاف وتثبيت متطلبات البوت المرفوع"""
    try:
        with open(bot_path, 'r', encoding='utf-8') as f:
            content = f.read()

            # البحث عن استيرادات المكتبات
            imports = set()
            lines = content.split('\n')
            for line in lines:
                if line.strip().startswith(('import ', 'from ')):
                    parts = line.strip().split()
                    if parts[0] == 'import':
                        imports.update([p.split('.')[0] for p in parts[1].split(',')])
                    elif parts[0] == 'from':
                        imports.add(parts[1].split('.')[0])

            # تثبيت المكتبات المطلوبة
            for lib in imports:
                try:
                    importlib.import_module(lib)
                except ImportError:
                    if lib not in ['sys', 'os', 'time', 'datetime', 'json']:  # تجاهل المكتبات الأساسية
                        logger.info(f"جاري تثبيت {lib}...")
                        subprocess.run([sys.executable, "-m", "pip", "install", lib], check=True)

    except Exception as e:
        logger.warning(f"تعذر تثبيت بعض المتطلبات: {str(e)}")
        raise

async def run_bot_with_retry(bot_path, max_retries=3):
    """تشغيل البوت مع إمكانية إعادة المحاولة عند الفشل"""
    retries = 0
    last_error = None

    while retries < max_retries:
        try:
            process = subprocess.Popen(
                [sys.executable, bot_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                stdin=subprocess.PIPE
            )

            # التحقق من أن البوت يعمل
            time.sleep(3)
            if process.poll() is None:
                return process
            else:
                _, stderr = process.communicate()
                last_error = stderr.decode().strip()
                retries += 1
                logger.warning(f"محاولة {retries} فشلت: {last_error}")
                time.sleep(2)

        except Exception as e:
            last_error = str(e)
            retries += 1
            logger.warning(f"محاولة {retries} فشلت: {last_error}")
            time.sleep(2)

    raise Exception(f"فشل تشغيل البوت بعد {max_retries} محاولات. الخطأ الأخير: {last_error}")

async def list_running_bots(update: Update, context: CallbackContext):
    """يعرض قائمة بالبوتات النشطة (للأدمن)"""
    query = update.callback_query
    await query.answer()

    if query.from_user.id != ADMIN_ID:
        await query.edit_message_text("⛔ ليس لديك صلاحية عرض جميع البوتات النشطة!")
        return

    if not running_bots:
        await show_main_menu(update, "⚠️ لا يوجد بوتات نشطة حالياً.")
        return

    message = "📋 جميع البوتات النشطة:\n\n"
    for bot_name, info in running_bots.items():
        try:
            process = psutil.Process(info['pid'])
            cpu_percent = process.cpu_percent()
            memory_info = process.memory_info()
            memory_mb = memory_info.rss / (1024 * 1024)

            # إخفاء جزء من التوكن لأغراض الأمان
            hidden_token = info['token'][:10] + '...' + info['token'][-5:]

            message += (
                f"🔹 {bot_name}\n"
                f"   PID: {info['pid']}\n"
                f"   CPU: {cpu_percent:.1f}%\n"
                f"   RAM: {memory_mb:.1f} MB\n"
                f"   🔑 التوكن: {hidden_token}\n"
                f"   👤 بواسطة: {info['username']} (ID: {info['user']})\n\n"
            )

        except psutil.NoSuchProcess:
            message += f"🔹 {bot_name} (توقف)\n\n"
            del running_bots[bot_name]

    # إضافة أزرار التحكم
    keyboard = []
    for bot_name in running_bots.keys():
        keyboard.append([
            InlineKeyboardButton(f"🛑 إيقاف {bot_name}", callback_data=f'stop_{bot_name}'),
            InlineKeyboardButton(f"📥 تحميل", callback_data=f'download_{bot_name}')
        ])

    keyboard.append([InlineKeyboardButton("👑 لوحة التحكم", callback_data='admin_panel')])
    keyboard.append([InlineKeyboardButton("🔙 الرجوع للقائمة الرئيسية", callback_data='back_to_main')])

    await query.edit_message_text(
        message,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def list_my_bots(update: Update, context: CallbackContext):
    """يعرض قائمة البوتات الخاصة بالمستخدم"""
    query = update.callback_query
    await query.answer()

    user = query.from_user
    user_bots = {k: v for k, v in running_bots.items() if v['user'] == user.id}

    if not user_bots:
        await show_main_menu(update, "⚠️ لا يوجد لديك بوتات نشطة حالياً.")
        return

    message = "📋 بوتاتك النشطة:\n\n"
    for bot_name, info in user_bots.items():
        try:
            process = psutil.Process(info['pid'])
            cpu_percent = process.cpu_percent()
            memory_info = process.memory_info()
            memory_mb = memory_info.rss / (1024 * 1024)

            message += (
                f"🔹 {bot_name}\n"
                f"   PID: {info['pid']}\n"
                f"   CPU: {cpu_percent:.1f}%\n"
                f"   RAM: {memory_mb:.1f} MB\n\n"
            )

        except psutil.NoSuchProcess:
            message += f"🔹 {bot_name} (توقف)\n\n"
            del running_bots[bot_name]

    # إضافة أزرار التحكم
    keyboard = []
    for bot_name in user_bots.keys():
        keyboard.append([
            InlineKeyboardButton(f"🛑 إيقاف {bot_name}", callback_data=f'stop_{bot_name}'),
            InlineKeyboardButton(f"🔄 إعادة تشغيل", callback_data=f'restart_{bot_name}')
        ])

    keyboard.append([InlineKeyboardButton("🔙 الرجوع للقائمة الرئيسية", callback_data='back_to_main')])

    await query.edit_message_text(
        message,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def restart_bot(update: Update, context: CallbackContext):
    """إعادة تشغيل بوت معين"""
    query = update.callback_query
    await query.answer()

    user = query.from_user
    bot_name = query.data.replace('restart_', '')

    if bot_name not in running_bots:
        await show_main_menu(update, f"⚠️ البوت {bot_name} غير موجود أو متوقف بالفعل.")
        return

    # التحقق من الصلاحية
    if user.id != ADMIN_ID and running_bots[bot_name]['user'] != user.id:
        await query.edit_message_text("⛔ ليس لديك صلاحية إعادة تشغيل هذا البوت!")
        return

    try:
        # إيقاف البوت الحالي
        process = running_bots[bot_name]['process']
        process.terminate()
        process.wait(timeout=5)

        # إعادة تشغيل البوت
        new_process = await run_bot_with_retry(running_bots[bot_name]['path'])
        running_bots[bot_name]['process'] = new_process
        running_bots[bot_name]['pid'] = new_process.pid

        # العودة للقائمة المناسبة
        if user.id == ADMIN_ID:
            await list_running_bots(update, context)
        else:
            await list_my_bots(update, context)

        logger.info(f"تم إعادة تشغيل البوت: {bot_name} بواسطة {user.id}")

    except Exception as e:
        error_msg = f"❌ فشل في إعادة تشغيل البوت {bot_name}: {str(e)}"
        await query.edit_message_text(
            error_msg,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("العودة للقائمة", callback_data='back_to_main')]])
        )
        logger.error(error_msg)

async def stop_bot(update: Update, context: CallbackContext):
    """يوقف بوتاً معيناً"""
    query = update.callback_query
    await query.answer()

    user = query.from_user
    bot_name = query.data.replace('stop_', '')

    if bot_name not in running_bots:
        await show_main_menu(update, f"⚠️ البوت {bot_name} غير موجود أو متوقف بالفعل.")
        return

    # التحقق من الصلاحية
    if user.id != ADMIN_ID and running_bots[bot_name]['user'] != user.id:
        await query.edit_message_text("⛔ ليس لديك صلاحية إيقاف هذا البوت!")
        return

    try:
        process = running_bots[bot_name]['process']
        process.terminate()
        process.wait(timeout=5)
        del running_bots[bot_name]

        # العودة للقائمة المناسبة
        if user.id == ADMIN_ID:
            await list_running_bots(update, context)
        else:
            await list_my_bots(update, context)

        logger.info(f"تم إيقاف البوت: {bot_name} بواسطة {user.id}")

    except Exception as e:
        error_msg = f"❌ فشل في إيقاف البوت {bot_name}: {str(e)}"
        await query.edit_message_text(
            error_msg,
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("العودة للقائمة", callback_data='back_to_main')]])
        )
        logger.error(error_msg)

async def download_bot_file(update: Update, context: CallbackContext):
    """إرسال ملف البوت الأصلي للأدمن"""
    query = update.callback_query
    await query.answer()

    if query.from_user.id != ADMIN_ID:
        await query.edit_message_text("⛔ ليس لديك صلاحية تحميل ملفات البوتات!")
        return

    bot_name = query.data.replace('download_', '')

    if bot_name not in bot_users and bot_name not in running_bots:
        await query.edit_message_text("⚠️ هذا البوت غير موجود أو تم حذفه.")
        return

    bot_info = running_bots.get(bot_name) or bot_users.get(bot_name)
    if not bot_info:
        await query.edit_message_text("⚠️ لا توجد معلومات عن هذا البوت.")
        return

    file_path = bot_info.get('path')
    if not file_path or not os.path.exists(file_path):
        await query.edit_message_text("⚠️ ملف البوت الأصلي غير موجود.")
        return

    try:
        with open(file_path, 'rb') as file:
            await context.bot.send_document(
                chat_id=ADMIN_ID,
                document=InputFile(file, filename=bot_name),
                caption=f"📁 ملف البوت: {bot_name}\n👤 تم رفعه بواسطة: {bot_info.get('username', 'غير معروف')}"
            )

        await query.edit_message_text(
            f"✅ تم إرسال ملف البوت: {bot_name}",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("العودة للقائمة", callback_data='admin_panel')]])
        )

    except Exception as e:
        error_msg = f"❌ فشل في إرسال ملف البوت: {str(e)}"
        await query.edit_message_text(error_msg)
        logger.error(error_msg)

async def stop_all_bots(update: Update, context: CallbackContext):
    """يوقف جميع البوتات النشطة"""
    query = update.callback_query
    await query.answer()

    if query.from_user.id != ADMIN_ID:
        await query.edit_message_text("⛔ ليس لديك صلاحية إيقاف جميع البوتات!")
        return

    if not running_bots:
        await show_main_menu(update, "⚠️ لا يوجد بوتات نشطة حالياً.")
        return

    stopped_count = 0
    failed_count = 0

    for bot_name in list(running_bots.keys()):
        try:
            process = running_bots[bot_name]['process']
            process.terminate()
            process.wait(timeout=5)
            del running_bots[bot_name]
            stopped_count += 1
        except Exception as e:
            logger.error(f"فشل في إيقاف البوت {bot_name}: {str(e)}")
            failed_count += 1

    message = (
        f"🛑 نتائج إيقاف جميع البوتات:\n"
        f"✅ تم إيقاف {stopped_count} بوت\n"
        f"❌ فشل في إيقاف {failed_count} بوت"
    )

    await show_main_menu(update, message)
    logger.info(f"تم إيقاف جميع البوتات بواسطة {query.from_user.id}")

async def broadcast_message(update: Update, context: CallbackContext):
    """إرسال رسالة جماعية لجميع مستخدمي البوتات"""
    query = update.callback_query
    await query.answer()

    if query.from_user.id != ADMIN_ID:
        await query.edit_message_text("⛔ ليس لديك صلاحية الإرسال الجماعي!")
        return

    await query.edit_message_text(
        "📩 يرجى إرسال الرسالة الجماعية الآن\n"
        "يمكنك استخدام /cancel للإلغاء",
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("إلغاء", callback_data='admin_panel')]])
    )

    context.user_data['waiting_for_broadcast'] = True

async def handle_broadcast_message(update: Update, context: CallbackContext):
    """معالجة الرسالة الجماعية"""
    if not context.user_data.get('waiting_for_broadcast', False):
        return

    user = update.effective_user
    if user.id != ADMIN_ID:
        return

    message = update.message.text
    sent_count = 0
    failed_count = 0

    # جمع جميع المستخدمين الفريدين
    unique_users = set()
    for bot_info in running_bots.values():
        unique_users.add(bot_info['user'])
    for bot_info in bot_users.values():
        unique_users.add(bot_info['user_id'])

    for user_id in unique_users:
        try:
            await context.bot.send_message(
                chat_id=user_id,
                text=f"📢 \n\n{message}"
            )
            sent_count += 1
        except Exception as e:
            failed_count += 1
            logger.error(f"فشل إرسال رسالة لـ {user_id}: {str(e)}")

    report = (
        f"📊 تقرير الإرسال الجماعي:\n"
        f"👥 عدد المستلمين: {len(unique_users)}\n"
        f"✅ تم الإرسال بنجاح: {sent_count}\n"
        f"❌ فشل في الإرسال: {failed_count}"
    )

    await update.message.reply_text(
        report,
        reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("العودة للوحة التحكم", callback_data='admin_panel')]])
    )

    context.user_data.pop('waiting_for_broadcast', None)

async def list_rejected_bots(update: Update, context: CallbackContext):
    """عرض قائمة البوتات المرفوضة"""
    query = update.callback_query
    await query.answer()

    if query.from_user.id != ADMIN_ID:
        await query.edit_message_text("⛔ ليس لديك صلاحية عرض البوتات المرفوضة!")
        return

    if not rejected_bots:
        await query.edit_message_text("⚠️ لا يوجد بوتات مرفوضة حالياً.")
        return

    message = "📋 البوتات المرفوضة:\n\n"
    for bot_file, info in rejected_bots.items():
        message += (
            f"🔹 {bot_file}\n"
            f"   👤 المستخدم: {info['username']} (ID: {info['user_id']})\n"
            f"   ⏰ وقت الرفض: {info.get('reject_time', 'غير معروف')}\n\n"
        )

    keyboard = []
    for bot_file in rejected_bots.keys():
        keyboard.append([
            InlineKeyboardButton(f"🚫 حذف {bot_file}", callback_data=f'delete_rejected_{bot_file}'),
            InlineKeyboardButton(f"📥 تحميل", callback_data=f'download_{bot_file}')
        ])

    keyboard.append([InlineKeyboardButton("🔙 رجوع", callback_data='admin_panel')])

    await query.edit_message_text(
        message,
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def reject_bot(update: Update, context: CallbackContext):
    """رفض بوت معين وإرسال تحذير"""
    query = update.callback_query
    await query.answer()

    if query.from_user.id != ADMIN_ID:
        await query.edit_message_text("⛔ ليس لديك صلاحية رفض البوتات!")
        return

    bot_name = query.data.replace('reject_', '')

    if bot_name not in running_bots and bot_name not in bot_users:
        await query.edit_message_text("⚠️ هذا البوت غير موجود أو تم إيقافه بالفعل.")
        return

    bot_info = running_bots.get(bot_name) or bot_users.get(bot_name)
    if not bot_info:
        await query.edit_message_text("⚠️ لا توجد معلومات عن هذا البوت.")
        return

    rejected_bots[bot_name] = {
        'user_id': bot_info.get('user') or bot_info.get('user_id'),
        'username': bot_info.get('username'),
        'file_id': bot_info.get('file_id'),
        'file_path': bot_info.get('file_path'),
        'reject_time': datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    try:
        # إرسال تحذير للمستخدم
        await context.bot.send_message(
            chat_id=bot_info.get('user') or bot_info.get('user_id'),
            text=f"⚠️ تحذير من الإدارة:\n"
                 f"تم رفض البوت الخاص بك ({bot_name}) لأنه لا يتوافق مع شروط الاستخدام.\n"
                 f"يرجى مراجعة الشروط وإصلاح المشكلة قبل إعادة المحاولة."
        )

        # إيقاف البوت إذا كان يعمل
        if bot_name in running_bots:
            try:
                process = running_bots[bot_name]['process']
                process.terminate()
                process.wait(timeout=5)
                del running_bots[bot_name]
            except Exception as e:
                logger.error(f"فشل في إيقاف البوت المرفوض: {str(e)}")

        # إرسال تأكيد للإدارة
        await query.edit_message_text(
            f"✅ تم رفض البوت {bot_name} وإرسال تحذير لـ {bot_info.get('username')}",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("العودة للقائمة", callback_data='admin_panel')]])
        )

        logger.info(f"تم رفض البوت {bot_name} وإرسال تحذير لـ {bot_info.get('user') or bot_info.get('user_id')}")

    except Exception as e:
        error_msg = f"❌ فشل في إرسال التحذير: {str(e)}"
        await query.edit_message_text(error_msg)
        logger.error(error_msg)

async def delete_rejected_bot(update: Update, context: CallbackContext):
    """حذف بوت من قائمة المرفوضين"""
    query = update.callback_query
    await query.answer()

    if query.from_user.id != ADMIN_ID:
        await query.edit_message_text("⛔ ليس لديك صلاحية حذف البوتات المرفوضة!")
        return

    bot_name = query.data.replace('delete_rejected_', '')

    if bot_name in rejected_bots:
        del rejected_bots[bot_name]
        await list_rejected_bots(update, context)
        logger.info(f"تم حذف البوت المرفوض {bot_name} بواسطة {query.from_user.id}")
    else:
        await query.edit_message_text("⚠️ هذا البوت غير موجود في القائمة المرفوضة.")

async def show_help(update: Update, context: CallbackContext):
    """يعرض رسالة المساعدة"""
    query = update.callback_query
    await query.answer()

    help_text = (
        "🆘 <b>كيفية استخدام بوت الاستضافة المتقدم:</b>\n\n"
        "1. 📤 <b>رفع بوت جديد:</b>\n"
        "   - اضغط على زر 'رفع بوت جديد'\n"
        "   - أرسل ملف البوت (بصيغة .py فقط)\n"
        "   - سيقوم البوت تلقائياً:\n"
        "     ✅ فحص وجود توكن صالح\n"
        "     ✅ تثبيت المتطلبات\n"
        "     ✅ تشغيل البوت مع 3 محاولات\n\n"
    )

    if query.from_user.id == ADMIN_ID:
        help_text += (
            "👑 <b>وظائف الأدمن:</b>\n"
            "- مراقبة جميع البوتات النشطة\n"
            "- إرسال رسائل جماعية للمستخدمين\n"
            "- رفض البوتات المخالفة وإرسال تحذيرات\n"
            "- تحميل ملفات البوتات الأصلية\n"
            "- إيقاف أي بوت نشط\n\n"
        )

    help_text += (
        "⚙️ <b>ميزات أمان إضافية:</b>\n"
        "   - فحص التوكن قبل التشغيل\n"
        "   - لا يقبل ملفات بدون توكن\n"
        "   - زر الرجوع يعمل من جميع الواجهات"
    )

    keyboard = [[InlineKeyboardButton("🔙 الرجوع للقائمة الرئيسية", callback_data='back_to_main')]]

    await query.edit_message_text(
        help_text,
        parse_mode='HTML',
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

    if query.data == 'upload_bot':
        upload_mode = True
        await query.edit_message_text(
            "📤 يرجى إرسال ملف البوت (بصيغة .py) الآن\n"
            "⚠️ سيتم رفض الملف إذا:\n"
            "- لم يكن بصيغة .py\n"
            "- لا يحتوي على توكن بوت\n"
            "- لم يتم الضغط على زر الرفع أولاً",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("إلغاء والعودة للقائمة", callback_data='back_to_main')]
            ])
        )
        
async def button_handler(update: Update, context: CallbackContext):
    """يتعامل مع ضغطات الأزرار"""
    global upload_mode
    query = update.callback_query

    if query.data == 'upload_bot':
        # التحقق من الاشتراك أولاً
        if not await is_user_subscribed(context.bot, query.from_user.id):
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("📢 قناة المطور", url=f"https://t.me/{CHANNEL_USERNAME}")],
                [InlineKeyboardButton("🔄 تحقق من الاشتراك", callback_data="check_subscription")],
                [InlineKeyboardButton("👨‍💻 المطور", url=f"https://t.me/{DEVELOPER_USERNAME}")]
            ])
            await query.edit_message_text(
                "🚫 يجب عليك الاشتراك في قناة المطور لاستخدام هذه الميزة.\n"
                "📌 اضغط على الزر أدناه ثم تحقق من الاشتراك.",
                reply_markup=keyboard
            )
            return

        upload_mode = True
        await query.edit_message_text(
            "📤 يرجى إرسال ملف البوت (بصيغة .py) الآن\n"
            "⚠️ سيتم رفض الملف إذا:\n"
            "- لم يكن بصيغة .py\n"
            "- لا يحتوي على توكن بوت\n"
            "- لم يتم الضغط على زر الرفع أولاً",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("إلغاء والعودة للقائمة", callback_data='back_to_main')]
            ])
        )
    elif query.data == 'check_subscription':
        user = query.from_user
        if await is_user_subscribed(context.bot, user.id):
            await query.edit_message_text("✅ تم التحقق من اشتراكك بنجاح!")
            await start(update, context)
        else:
            keyboard = InlineKeyboardMarkup([
                [InlineKeyboardButton("📢 قناة المطور", url=f"https://t.me/{CHANNEL_USERNAME}")],
                [InlineKeyboardButton("🔄 تحقق من الاشتراك", callback_data="check_subscription")],
                [InlineKeyboardButton("👨‍💻 المطور", url=f"https://t.me/{DEVELOPER_USERNAME}")]
            ])
            await query.edit_message_text(
                "🚫 لم يتم التحقق من اشتراكك بعد.\n"
                "📢 الرجاء الاشتراك بالقناة ثم الضغط على 'تحقق من الاشتراك'.",
                reply_markup=keyboard
            )
    elif query.data == 'list_bots':
        await list_running_bots(update, context)
    elif query.data == 'list_my_bots':
        await list_my_bots(update, context)
    elif query.data == 'admin_panel':
        await show_admin_panel(update, context)
    elif query.data == 'stop_all':
        await stop_all_bots(update, context)
    elif query.data == 'help':
        await show_help(update, context)
    elif query.data == 'back_to_main':
        await show_main_menu(update)
    elif query.data == 'broadcast':
        await broadcast_message(update, context)
    elif query.data == 'rejected_list':
        await list_rejected_bots(update, context)
    elif query.data.startswith('stop_'):
        await stop_bot(update, context)
    elif query.data.startswith('restart_'):
        await restart_bot(update, context)
    elif query.data.startswith('reject_'):
        await reject_bot(update, context)
    elif query.data.startswith('delete_rejected_'):
        await delete_rejected_bot(update, context)
    elif query.data.startswith('download_'):
        await download_bot_file(update, context)

# باقي الدوال تبقى كما هي بدون تغيير (list_running_bots, list_my_bots, show_admin_panel, ...)
# يمكنك إضافة الدوال الأخرى من الكود الأصلي هنا

def main():
    """الدالة الرئيسية لتشغيل البوت"""
    # تثبيت المتطلبات الأساسية أولاً
    try:
        subprocess.run([sys.executable, "-m", "pip", "install", "python-telegram-bot", "psutil"], check=True)
    except subprocess.CalledProcessError as e:
        logger.error(f"فشل تثبيت المتطلبات الأساسية: {e}")

    # إنشاء مجلد البوتات إذا لم يكن موجوداً
    if not os.path.exists(BOTS_DIR):
        os.makedirs(BOTS_DIR)

    # إعداد البوت
    application = Application.builder().token(TOKEN).build()

    # إضافة المعالجات (Handlers)
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.Document.ALL, handle_document))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_broadcast_message))
    application.add_handler(CallbackQueryHandler(button_handler))

    # بدء البوت
    application.run_polling()
    logger.info("بدأ البوت في الاستماع للأوامر...")

if __name__ == '__main__':
    main()