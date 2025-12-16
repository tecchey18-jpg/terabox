"""
Main Telegram Bot
"""

import asyncio
import logging
import html
import re
from typing import Optional
from datetime import datetime

from telegram import (
    Update, 
    InlineKeyboardButton, 
    InlineKeyboardMarkup,
    BotCommand
)
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters,
)
from telegram.constants import ParseMode, ChatAction

from config import config, logger
from mirrors import TeraboxMirrors
from terabox_extractor import TeraboxExtractor, VideoInfo
from database import db
from utils import format_file_size

# Rate limiting
user_last_request = {}
RATE_LIMIT_SECONDS = 3


class TeraboxBot:
    def __init__(self):
        self.extractor = TeraboxExtractor()
        self.app: Optional[Application] = None
        self._semaphore = asyncio.Semaphore(config.MAX_CONCURRENT_EXTRACTIONS)
    
    async def start(self):
        """Start the bot"""
        # Initialize database
        await db.init()
        
        # Initialize extractor session
        await self.extractor.init_session()
        
        # Build application
        self.app = (
            Application.builder()
            .token(config.BOT_TOKEN)
            .concurrent_updates(True)
            .build()
        )
        
        # Add handlers
        self._add_handlers()
        
        # Set commands
        await self._set_commands()
        
        # Start polling
        logger.info("Starting bot...")
        await self.app.initialize()
        await self.app.start()
        await self.app.updater.start_polling(
            drop_pending_updates=True,
            allowed_updates=["message", "callback_query"]
        )
        
        logger.info("Bot is running!")
        
        # Keep running
        while True:
            await asyncio.sleep(1)
    
    async def stop(self):
        """Stop the bot"""
        if self.app:
            await self.app.updater.stop()
            await self.app.stop()
            await self.app.shutdown()
        await self.extractor.close()
    
    def _add_handlers(self):
        """Add all handlers"""
        self.app.add_handler(CommandHandler("start", self.cmd_start))
        self.app.add_handler(CommandHandler("help", self.cmd_help))
        self.app.add_handler(CommandHandler("stats", self.cmd_stats))
        self.app.add_handler(CommandHandler("admin", self.cmd_admin))
        self.app.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message)
        )
        self.app.add_handler(CallbackQueryHandler(self.handle_callback))
        self.app.add_error_handler(self.error_handler)
    
    async def _set_commands(self):
        """Set bot commands"""
        commands = [
            BotCommand("start", "Start the bot"),
            BotCommand("help", "Show help message"),
            BotCommand("stats", "Show your statistics"),
        ]
        await self.app.bot.set_my_commands(commands)
    
    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command"""
        user = update.effective_user
        
        # Save user to database
        await db.add_user(
            user_id=user.id,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name
        )
        
        welcome_text = f"""
🎬 <b>Welcome to Terabox Video Extractor Bot!</b>

Hello {html.escape(user.first_name)}! 👋

I can extract direct playable video links from:
• Terabox.com
• TeraboxApp.com  
• 1024tera.com
• And 15+ mirror sites!

<b>How to use:</b>
Just send me any Terabox share link and I'll extract the direct video URL for you.

<b>Supported URL formats:</b>
• https://terabox.com/s/xxxxx
• https://1024tera.com/s/xxxxx
• https://teraboxapp.com/s/xxxxx
• And many more...

Send a link to get started! 🚀
"""
        
        keyboard = [
            [
                InlineKeyboardButton("📖 Help", callback_data="help"),
                InlineKeyboardButton("📊 Stats", callback_data="stats"),
            ],
            [
                InlineKeyboardButton("🔗 Supported Sites", callback_data="sites"),
            ]
        ]
        
        await update.message.reply_text(
            welcome_text,
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    
    async def cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command"""
        help_text = """
📖 <b>How to Use This Bot</b>

<b>Step 1:</b> Get a Terabox share link
<b>Step 2:</b> Send the link to this bot
<b>Step 3:</b> Wait for extraction (usually 5-15 seconds)
<b>Step 4:</b> Get your direct playable video link!

<b>Supported Link Formats:</b>
• <code>https://terabox.com/s/1ABCdef123</code>
• <code>https://www.teraboxapp.com/s/1XYZ789</code>
• <code>https://1024tera.com/s/1abc123</code>
• <code>https://terabox.com/wap/share/link?surl=xxx</code>

<b>Tips:</b>
• Make sure the link is publicly accessible
• Some files may be password protected
• Large files might take longer to process
• If extraction fails, try again after a few seconds

<b>Commands:</b>
/start - Start the bot
/help - Show this help message
/stats - View your usage statistics
"""
        await update.message.reply_text(help_text, parse_mode=ParseMode.HTML)
    
    async def cmd_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /stats command"""
        user = update.effective_user
        stats = await db.get_user_stats(user.id)
        
        if not stats:
            await update.message.reply_text("No statistics available yet. Start using the bot!")
            return
        
        stats_text = f"""
📊 <b>Your Statistics</b>

👤 User: {html.escape(user.first_name)}
📨 Total Requests: {stats['total_requests']}
✅ Successful: {stats['successful']}
❌ Failed: {stats['failed']}
📈 Success Rate: {(stats['successful'] / stats['total_requests'] * 100) if stats['total_requests'] > 0 else 0:.1f}%
"""
        await update.message.reply_text(stats_text, parse_mode=ParseMode.HTML)
    
    async def cmd_admin(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /admin command (admin only)"""
        user = update.effective_user
        
        if user.id not in config.ADMIN_IDS:
            await update.message.reply_text("⛔ Access denied!")
            return
        
        stats = await db.get_global_stats()
        
        admin_text = f"""
🔐 <b>Admin Dashboard</b>

<b>Global Statistics:</b>
👥 Total Users: {stats['total_users']}
📨 Total Requests: {stats['total_requests']}
✅ Successful: {stats['successful_requests']}
📈 Success Rate: {stats['success_rate']:.1f}%
🕐 Requests (24h): {stats['requests_24h']}

<b>System Status:</b>
🟢 Bot: Online
🟢 Extractor: Ready
🟢 Database: Connected
"""
        await update.message.reply_text(admin_text, parse_mode=ParseMode.HTML)
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle incoming messages with Terabox links"""
        user = update.effective_user
        message = update.message
        text = message.text.strip()
        
        # Check rate limiting
        if not self._check_rate_limit(user.id):
            await message.reply_text(
                "⏳ Please wait a few seconds before sending another request."
            )
            return
        
        # Check if it's a Terabox URL
        if not TeraboxMirrors.is_terabox_url(text):
            # Try to find URL in the text
            url_match = re.search(r'https?://[^\s]+', text)
            if url_match:
                text = url_match.group(0)
                if not TeraboxMirrors.is_terabox_url(text):
                    await message.reply_text(
                        "❌ That doesn't look like a Terabox link.\n\n"
                        "Please send a valid Terabox share URL."
                    )
                    return
            else:
                await message.reply_text(
                    "❌ No valid URL found.\n\n"
                    "Please send a Terabox share link like:\n"
                    "<code>https://terabox.com/s/1ABCdef123</code>",
                    parse_mode=ParseMode.HTML
                )
                return
        
        # Send processing message
        processing_msg = await message.reply_text(
            "⏳ <b>Processing your request...</b>\n\n"
            "🔍 Analyzing link...",
            parse_mode=ParseMode.HTML
        )
        
        # Show typing action
        await context.bot.send_chat_action(
            chat_id=message.chat_id,
            action=ChatAction.TYPING
        )
        
        # Extract video
        try:
            async with self._semaphore:
                # Update status
                await processing_msg.edit_text(
                    "⏳ <b>Processing your request...</b>\n\n"
                    "🔄 Extracting video information...",
                    parse_mode=ParseMode.HTML
                )
                
                video_info = await asyncio.wait_for(
                    self.extractor.extract(text),
                    timeout=config.EXTRACTION_TIMEOUT
                )
                
                if video_info.is_valid():
                    # Log success
                    await db.log_request(
                        user_id=user.id,
                        url=text,
                        success=True,
                        video_title=video_info.title,
                        video_size=video_info.size
                    )
                    
                    # Send result
                    await self._send_result(processing_msg, video_info)
                else:
                    raise Exception("Could not extract a valid video link")
                    
        except asyncio.TimeoutError:
            await db.log_request(
                user_id=user.id,
                url=text,
                success=False,
                error_message="Timeout"
            )
            await processing_msg.edit_text(
                "⏰ <b>Request Timeout</b>\n\n"
                "The extraction took too long. Please try again.",
                parse_mode=ParseMode.HTML
            )
        except Exception as e:
            logger.error(f"Extraction failed: {e}")
            await db.log_request(
                user_id=user.id,
                url=text,
                success=False,
                error_message=str(e)
            )
            await processing_msg.edit_text(
                f"❌ <b>Extraction Failed</b>\n\n"
                f"Error: {html.escape(str(e)[:200])}\n\n"
                "Please try again or check if the link is valid and publicly accessible.",
                parse_mode=ParseMode.HTML
            )
    
    async def _send_result(self, message, video_info: VideoInfo):
        """Send the extraction result"""
        
        # Get the best available link
        direct_link = video_info.get_best_link()
        
        # Build response text
        result_text = f"""
✅ <b>Video Extracted Successfully!</b>

📁 <b>Title:</b> {html.escape(video_info.title[:100])}
💾 <b>Size:</b> {video_info.size_formatted}
"""
        
        if video_info.resolution:
            result_text += f"📐 <b>Resolution:</b> {video_info.resolution}\n"
        
        result_text += f"""
🔗 <b>Direct Link:</b>
<code>{direct_link}</code>

<i>Click the link above to copy, or use the buttons below.</i>
"""
        
        # Build keyboard
        keyboard = [
            [InlineKeyboardButton("▶️ Play Video", url=direct_link)],
            [InlineKeyboardButton("📥 Download", url=direct_link)],
        ]
        
        # Add quality options if available
        if video_info.quality_options:
            quality_buttons = []
            for quality, link in video_info.quality_options.items():
                quality_buttons.append(
                    InlineKeyboardButton(f"📺 {quality}", url=link)
                )
            if quality_buttons:
                keyboard.append(quality_buttons[:2])  # Max 2 per row
        
        # Add thumbnail if available
        if video_info.thumbnail:
            try:
                await message.reply_photo(
                    photo=video_info.thumbnail,
                    caption=result_text,
                    parse_mode=ParseMode.HTML,
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
                await message.delete()
                return
            except Exception as e:
                logger.warning(f"Failed to send thumbnail: {e}")
        
        # Send text result
        await message.edit_text(
            result_text,
            parse_mode=ParseMode.HTML,
            reply_markup=InlineKeyboardMarkup(keyboard),
            disable_web_page_preview=False
        )
    
    async def handle_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle callback queries"""
        query = update.callback_query
        await query.answer()
        
        if query.data == "help":
            help_text = """
📖 <b>How to Use This Bot</b>

1️⃣ Get a Terabox share link
2️⃣ Send the link to this bot
3️⃣ Wait for extraction
4️⃣ Get your direct video link!

<b>Supported sites:</b>
Terabox, TeraboxApp, 1024tera, and 15+ mirrors!
"""
            await query.edit_message_text(help_text, parse_mode=ParseMode.HTML)
        
        elif query.data == "stats":
            stats = await db.get_user_stats(query.from_user.id)
            if stats:
                stats_text = f"""
📊 <b>Your Statistics</b>

📨 Total Requests: {stats['total_requests']}
✅ Successful: {stats['successful']}
❌ Failed: {stats['failed']}
"""
            else:
                stats_text = "No statistics yet. Send a Terabox link to get started!"
            await query.edit_message_text(stats_text, parse_mode=ParseMode.HTML)
        
        elif query.data == "sites":
            sites_text = """
🔗 <b>Supported Websites</b>

<b>Primary:</b>
• terabox.com
• teraboxapp.com
• 1024tera.com

<b>Mirrors:</b>
• mirrobox.com
• nephobox.com
• 4funbox.com
• freeterabox.com
• momerybox.com
• And more...

Just send any link from these sites!
"""
            await query.edit_message_text(sites_text, parse_mode=ParseMode.HTML)
    
    def _check_rate_limit(self, user_id: int) -> bool:
        """Check if user is rate limited"""
        now = datetime.now().timestamp()
        last_request = user_last_request.get(user_id, 0)
        
        if now - last_request < RATE_LIMIT_SECONDS:
            return False
        
        user_last_request[user_id] = now
        return True
    
    async def error_handler(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle errors"""
        logger.error(f"Error: {context.error}", exc_info=context.error)
        
        if update and update.effective_message:
            try:
                await update.effective_message.reply_text(
                    "❌ An unexpected error occurred. Please try again later."
                )
            except:
                pass


async def main():
    """Main entry point"""
    if not config.BOT_TOKEN:
        logger.error("BOT_TOKEN not set!")
        return
    
    bot = TeraboxBot()
    
    try:
        await bot.start()
    except KeyboardInterrupt:
        logger.info("Shutting down...")
    finally:
        await bot.stop()


if __name__ == "__main__":
    asyncio.run(main())
