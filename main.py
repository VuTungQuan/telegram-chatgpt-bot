import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import openai
from openai import OpenAI
import asyncio

# Cấu hình logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Cấu hình API keys từ environment variables
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# Kiểm tra API keys
if not TELEGRAM_TOKEN:
    raise ValueError("TELEGRAM_TOKEN environment variable is not set")
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY environment variable is not set")

# Khởi tạo OpenAI client
client = OpenAI(api_key=OPENAI_API_KEY)

# Dictionary để lưu lịch sử chat của từng user
user_conversations = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Xử lý lệnh /start"""
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

async def clear_conversation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Xóa lịch sử cuộc trò chuyện"""
    user_id = update.effective_user.id
    user_conversations[user_id] = []
    await update.message.reply_text("✅ Đã xóa lịch sử cuộc trò chuyện!")

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Hiển thị trợ giúp"""
    help_text = """
🤖 ChatGPT Telegram Bot

Lệnh:
/start - Khởi động bot
/clear - Xóa lịch sử chat
/help - Hiển thị trợ giúp này

Tính năng:
• Trò chuyện với ChatGPT
• Lưu ngữ cảnh cuộc trò chuyện
• Hỗ trợ tiếng Việt
    """
    await update.message.reply_text(help_text)

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Xử lý tin nhắn từ user và gửi đến ChatGPT"""
    user_id = update.effective_user.id
    user_message = update.message.text
    
    # Khởi tạo conversation nếu chưa có
    if user_id not in user_conversations:
        user_conversations[user_id] = []
    
    # Thêm tin nhắn của user vào lịch sử
    user_conversations[user_id].append({
        "role": "user", 
        "content": user_message
    })
    
    # Giới hạn lịch sử (để tránh vượt quá token limit)
    if len(user_conversations[user_id]) > 20:
        user_conversations[user_id] = user_conversations[user_id][-20:]
    
    try:
        # Gửi "typing..." để user biết bot đang xử lý
        await context.bot.send_chat_action(
            chat_id=update.effective_chat.id, 
            action="typing"
        )
        
        # Gọi OpenAI API
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",  # Hoặc "gpt-4" nếu có quyền truy cập
            messages=[
                {"role": "system", "content": "Bạn là một trợ lý AI hữu ích, trả lời bằng tiếng Việt."}
            ] + user_conversations[user_id],
            max_tokens=1000,
            temperature=0.7
        )
        
        # Lấy phản hồi từ ChatGPT
        bot_reply = response.choices[0].message.content
        
        # Thêm phản hồi của bot vào lịch sử
        user_conversations[user_id].append({
            "role": "assistant",
            "content": bot_reply
        })
        
        # Gửi phản hồi cho user
        await update.message.reply_text(bot_reply)
        
    except openai.RateLimitError:
        await update.message.reply_text("❌ Đã vượt quá giới hạn API. Vui lòng thử lại sau.")
    except openai.APIError as e:
        logger.error(f"OpenAI API error: {e}")
        await update.message.reply_text("❌ Có lỗi xảy ra với API. Vui lòng thử lại.")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        await update.message.reply_text("❌ Có lỗi không mong muốn xảy ra.")

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Xử lý lỗi"""
    logger.warning(f'Update {update} caused error {context.error}')

def main():
    """Khởi chạy bot"""
    # Kiểm tra API keys trước khi khởi tạo
    if not TELEGRAM_TOKEN:
        print("❌ TELEGRAM_TOKEN không được thiết lập!")
        return
    if not OPENAI_API_KEY:
        print("❌ OPENAI_API_KEY không được thiết lập!")
        return
    
    try:
        # Tạo Application
        application = Application.builder().token(TELEGRAM_TOKEN).build()
        
        # Đăng ký handlers
        application.add_handler(CommandHandler("start", start))
        application.add_handler(CommandHandler("clear", clear_conversation))
        application.add_handler(CommandHandler("help", help_command))
        application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
        
        # Đăng ký error handler
        application.add_error_handler(error_handler)
        
        # Chạy bot
        print("🤖 Bot đang chạy...")
        application.run_polling(
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True
        )
    except Exception as e:
        logger.error(f"Lỗi khởi động bot: {e}")
        print(f"❌ Lỗi khởi động: {e}")

if __name__ == '__main__':
    main()
