import os
import logging
from flask import Flask, request
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import openai
from openai import OpenAI
import asyncio
import json

# Cấu hình logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Flask app
app = Flask(__name__)

# Cấu hình API keys từ environment variables
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
WEBHOOK_URL = os.getenv("WEBHOOK_URL", "https://your-app.onrender.com")

# Kiểm tra API keys
if not TELEGRAM_TOKEN or not OPENAI_API_KEY:
    raise ValueError("API keys not configured")

# Khởi tạo OpenAI client
client = OpenAI(api_key=OPENAI_API_KEY)

# Dictionary để lưu lịch sử chat
user_conversations = {}

# Tạo application
application = Application.builder().token(TELEGRAM_TOKEN).build()

# Handlers (giống như code cũ)
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_conversations[user_id] = []
    
    welcome_message = """
🤖 Xin chào! Tôi là ChatGPT Bot.

Các lệnh có sẵn:
/start - Bắt đầu cuộc trò chuyện
/clear - Xóa lịch sử chat
/help - Hiển thị trợ giúp

Chỉ cần gửi tin nhắn và tôi sẽ trả lời bạn!
    """
    await update.message.reply_text(welcome_message)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user_message = update.message.text
    
    if user_id not in user_conversations:
        user_conversations[user_id] = []
    
    user_conversations[user_id].append({
        "role": "user", 
        "content": user_message
    })
    
    if len(user_conversations[user_id]) > 20:
        user_conversations[user_id] = user_conversations[user_id][-20:]
    
    try:
        await context.bot.send_chat_action(
            chat_id=update.effective_chat.id, 
            action="typing"
        )
        
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "Bạn là một trợ lý AI hữu ích, trả lời bằng tiếng Việt."}
            ] + user_conversations[user_id],
            max_tokens=1000,
            temperature=0.7
        )
        
        bot_reply = response.choices[0].message.content
        
        user_conversations[user_id].append({
            "role": "assistant",
            "content": bot_reply
        })
        
        await update.message.reply_text(bot_reply)
        
    except Exception as e:
        logger.error(f"Error: {e}")
        await update.message.reply_text("❌ Có lỗi xảy ra. Vui lòng thử lại.")

# Đăng ký handlers
application.add_handler(CommandHandler("start", start))
application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

@app.route(f'/{TELEGRAM_TOKEN}', methods=['POST'])
def webhook():
    """Xử lý webhook từ Telegram"""
    try:
        json_data = request.get_json()
        update = Update.de_json(json_data, application.bot)
        
        # Chạy handler trong event loop mới
        asyncio.run(application.process_update(update))
        
        return 'OK'
    except Exception as e:
        logger.error(f"Webhook error: {e}")
        return 'Error', 500

@app.route('/')
def index():
    return 'Telegram ChatGPT Bot is running!'

if __name__ == '__main__':
    # Thiết lập webhook
    asyncio.run(application.bot.set_webhook(f"{WEBHOOK_URL}/{TELEGRAM_TOKEN}"))
    
    # Chạy Flask app
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
