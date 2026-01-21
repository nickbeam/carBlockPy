"""
Telegram bot module for CarBlockPy2 application.

This module provides the Telegram bot interface for managing license plates
and sending messages between users.
"""

import logging
from typing import Optional
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.error import BadRequest
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes,
    ConversationHandler,
    CommandHandler as CmdHandler
)

from src.database import (
    UserRepository,
    LicensePlateRepository,
    MessageHistoryRepository,
    User,
    LicensePlate
)
from src.rate_limiter import RateLimiter
from config.config_loader import load_config

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Conversation states
ADD_PLATE, DELETE_PLATE, SEND_MESSAGE, SEND_USERNAME_PLATE, SEND_USERNAME_CONFIRM = range(5)


class CarBlockBot:
    """
    Telegram bot for CarBlockPy2 application.
    
    Handles user registration, license plate management, and messaging.
    """
    
    def __init__(self):
        """Initialize the bot."""
        self.config = load_config()
        self.rate_limiter = RateLimiter()
        self.application = None
    
    def get_main_menu_keyboard(self):
        """
        Create the main menu inline keyboard.
        
        Returns:
            InlineKeyboardMarkup with main menu buttons.
        """
        keyboard = [
            [
                InlineKeyboardButton("📋 My Plates", callback_data="menu_myplates"),
                InlineKeyboardButton("➕ Add Plate", callback_data="menu_addplate"),
            ],
            [
                InlineKeyboardButton("🗑️ Delete Plate", callback_data="menu_deleteplate"),
                InlineKeyboardButton("📨 Send Message", callback_data="menu_sendmsg"),
            ],
            [
                InlineKeyboardButton("👤 Share Contact", callback_data="menu_sharecontact"),
                InlineKeyboardButton("ℹ️ Help", callback_data="menu_help"),
            ],
        ]
        return InlineKeyboardMarkup(keyboard)
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Handle the /start command.
        
        Args:
            update: The Telegram update object.
            context: The callback context.
        """
        user = update.effective_user
        
        # Get or create user in database
        db_user = UserRepository.get_or_create(
            telegram_id=user.id,
            username=user.username or f"user_{user.id}"
        )
        
        welcome_message = (
            f"👋 Welcome to CarBlockPy2, {db_user.username}!\n\n"
            "This bot helps you manage your license plates and "
            "send messages to other vehicle owners.\n\n"
            "Use the buttons below to navigate:"
        )
        
        await update.message.reply_text(
            welcome_message,
            reply_markup=self.get_main_menu_keyboard()
        )
    
    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Handle the /help command.
        
        Args:
            update: The Telegram update object.
            context: The callback context.
        """
        help_message = (
            "📖 *CarBlockPy2 Help*\n\n"
            "*How to send a message:*\n"
            "1. Click \"Send Message\" button\n"
            "2. Enter the license plate number\n"
            "3. The bot will send a message to the owner\n\n"
            "*Rate Limiting:*\n"
            f"You can send up to {self.config.rate_limiting.max_messages_per_hour} "
            "messages per hour."
        )
        
        await update.message.reply_text(
            help_message,
            parse_mode="Markdown",
            reply_markup=self.get_main_menu_keyboard()
        )
    
    async def my_plates(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Handle the /myplates command - list user's license plates.
        
        Args:
            update: The Telegram update object.
            context: The callback context.
        """
        user = update.effective_user
        db_user = UserRepository.get_by_telegram_id(user.id)
        
        if not db_user:
            await update.message.reply_text(
                "Please use /start to register first.",
                reply_markup=self.get_main_menu_keyboard()
            )
            return
        
        plates = LicensePlateRepository.get_by_user(db_user.id)
        
        if not plates:
            await update.message.reply_text(
                "You don't have any license plates registered.\n"
                "Use /addplate to add one.",
                reply_markup=self.get_main_menu_keyboard()
            )
            return
        
        plates_list = "🚗 *Your License Plates:*\n\n"
        for i, plate in enumerate(plates, 1):
            plates_list += f"{i}. `{plate.plate_number}`\n"
        
        plates_list += f"\n*Total: {len(plates)} plate(s)*"
        
        await update.message.reply_text(
            plates_list,
            parse_mode="Markdown",
            reply_markup=self.get_main_menu_keyboard()
        )
    
    async def add_plate_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Start the add license plate conversation.
        
        Args:
            update: The Telegram update object.
            context: The callback context.
        """
        user = update.effective_user
        db_user = UserRepository.get_by_telegram_id(user.id)
        
        if not db_user:
            if update.message:
                await update.message.reply_text(
                    "Please use /start to register first.",
                    reply_markup=self.get_main_menu_keyboard()
                )
            elif update.callback_query:
                await update.callback_query.answer()
                try:
                    await update.callback_query.edit_message_text(
                        "Please use /start to register first.",
                        reply_markup=self.get_main_menu_keyboard()
                    )
                except BadRequest:
                    pass  # Message content is identical
            return ConversationHandler.END
        
        # Debug logging
        logger.info(f"add_plate_start called. context.args: {context.args}")
        
        # Check if plate number is provided as argument
        if context.args and len(context.args) > 0:
            plate_number = " ".join(context.args).strip().upper()
            logger.info(f"Processing plate from argument: {plate_number}")
            # Process the plate directly
            return await self._process_add_plate(update, db_user, plate_number)
        
        # For callback query, edit the message to prompt for plate number
        if update.callback_query:
            await update.callback_query.answer()
            try:
                await update.callback_query.edit_message_text(
                    "Please enter the license plate number you want to add:\n"
                    "(e.g., ABC123, X777XX77)"
                )
            except BadRequest:
                pass  # Message content is identical
            return ADD_PLATE
        
        await update.message.reply_text(
            "Please enter the license plate number you want to add:\n"
            "(e.g., ABC123, X777XX77)"
        )
        
        return ADD_PLATE
    
    async def _process_add_plate(self, update: Update, db_user: User, plate_number: str):
        """
        Process adding a license plate to the database.
        
        Args:
            update: The Telegram update object.
            db_user: The database user object.
            plate_number: The license plate number to add.
        """
        # Check if plate already exists
        existing_plate = LicensePlateRepository.get_by_plate_number(plate_number)
        
        if existing_plate:
            if existing_plate.user_id == db_user.id:
                await update.message.reply_text(
                    f"❌ You already have this license plate: `{plate_number}`",
                    parse_mode="Markdown",
                    reply_markup=self.get_main_menu_keyboard()
                )
            else:
                await update.message.reply_text(
                    f"❌ This license plate is already registered by another user.",
                    reply_markup=self.get_main_menu_keyboard()
                )
            return ConversationHandler.END
        
        # Add the plate
        try:
            LicensePlateRepository.create(db_user.id, plate_number)
            await update.message.reply_text(
                f"✅ License plate `{plate_number}` has been added successfully!",
                parse_mode="Markdown",
                reply_markup=self.get_main_menu_keyboard()
            )
        except Exception as e:
            logger.error(f"Error adding license plate: {e}")
            await update.message.reply_text(
                "❌ An error occurred while adding the license plate. Please try again.",
                reply_markup=self.get_main_menu_keyboard()
            )
        
        return ConversationHandler.END
    
    async def add_plate(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Process the license plate number and add it to the database.
        
        Args:
            update: The Telegram update object.
            context: The callback context.
        """
        user = update.effective_user
        db_user = UserRepository.get_by_telegram_id(user.id)
        plate_number = update.message.text.strip().upper()
        
        return await self._process_add_plate(update, db_user, plate_number)
    
    async def cancel_conversation(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Cancel the current conversation.
        
        Args:
            update: The Telegram update object.
            context: The callback context.
        """
        if update.message:
            await update.message.reply_text(
                "Operation cancelled.",
                reply_markup=self.get_main_menu_keyboard()
            )
        elif update.callback_query:
            await update.callback_query.answer()
            await update.callback_query.edit_message_text(
                "Operation cancelled.",
                reply_markup=self.get_main_menu_keyboard()
            )
        return ConversationHandler.END
    
    async def delete_plate_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Start the delete license plate conversation.
        
        Args:
            update: The Telegram update object.
            context: The callback context.
        """
        user = update.effective_user
        db_user = UserRepository.get_by_telegram_id(user.id)
        
        if not db_user:
            if update.message:
                await update.message.reply_text(
                    "Please use /start to register first.",
                    reply_markup=self.get_main_menu_keyboard()
                )
            elif update.callback_query:
                await update.callback_query.answer()
                try:
                    await update.callback_query.edit_message_text(
                        "Please use /start to register first.",
                        reply_markup=self.get_main_menu_keyboard()
                    )
                except BadRequest:
                    pass  # Message content is identical
            return ConversationHandler.END
        
        plates = LicensePlateRepository.get_by_user(db_user.id)
        
        if not plates:
            if update.message:
                await update.message.reply_text(
                    "You don't have any license plates to delete.\n"
                    "Use /addplate to add one first.",
                    reply_markup=self.get_main_menu_keyboard()
                )
            elif update.callback_query:
                await update.callback_query.answer()
                try:
                    await update.callback_query.edit_message_text(
                        "You don't have any license plates to delete.\n"
                        "Use /addplate to add one first.",
                        reply_markup=self.get_main_menu_keyboard()
                    )
                except BadRequest:
                    pass  # Message content is identical
            return ConversationHandler.END
        
        # Create inline keyboard with plates
        keyboard = []
        for plate in plates:
            keyboard.append([
                    InlineKeyboardButton(
                        plate.plate_number,
                        callback_data=f"delete_{plate.id}"
                    )
                ])
        
        # Add Cancel button at the end
        keyboard.append([
            InlineKeyboardButton("❌ Cancel", callback_data="cancel_delete")
        ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if update.callback_query:
            await update.callback_query.answer()
            try:
                await update.callback_query.edit_message_text(
                    "Select a license plate to delete:",
                    reply_markup=reply_markup
                )
            except BadRequest:
                pass  # Message content is identical
        else:
            await update.message.reply_text(
                "Select a license plate to delete:",
                reply_markup=reply_markup
            )
        
        return DELETE_PLATE
    
    async def delete_plate_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Handle the delete plate callback.
        
        Args:
            update: The Telegram update object.
            context: The callback context.
        """
        query = update.callback_query
        await query.answer()
        
        # Check if this is a cancel request - show help menu
        if query.data == "cancel_delete":
            help_message = (
                "📖 *CarBlockPy2 Help*\n\n"
                "*How to send a message:*\n"
                "1. Click \"Send Message\" button\n"
                "2. Enter the license plate number\n"
                "3. The bot will send a message to the owner\n\n"
                "*Rate Limiting:*\n"
                f"You can send up to {self.config.rate_limiting.max_messages_per_hour} "
                "messages per hour."
            )
            await query.edit_message_text(
                help_message,
                parse_mode="Markdown",
                reply_markup=self.get_main_menu_keyboard()
            )
            return ConversationHandler.END
        
        plate_id = int(query.data.split("_")[1])
        plate = LicensePlateRepository.get_by_id(plate_id)
        
        if not plate:
            await query.edit_message_text(
                "❌ License plate not found.",
                reply_markup=self.get_main_menu_keyboard()
            )
            return ConversationHandler.END
        
        LicensePlateRepository.delete(plate_id)
        
        await query.edit_message_text(
            f"✅ License plate `{plate.plate_number}` has been deleted.",
            parse_mode="Markdown",
            reply_markup=self.get_main_menu_keyboard()
        )
        
        return ConversationHandler.END
    
    async def send_message_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Start the send message conversation.
        
        Args:
            update: The Telegram update object.
            context: The callback context.
        """
        user = update.effective_user
        db_user = UserRepository.get_by_telegram_id(user.id)
        
        if not db_user:
            if update.message:
                await update.message.reply_text(
                    "Please use /start to register first.",
                    reply_markup=self.get_main_menu_keyboard()
                )
            elif update.callback_query:
                await update.callback_query.answer()
                try:
                    await update.callback_query.edit_message_text(
                        "Please use /start to register first.",
                        reply_markup=self.get_main_menu_keyboard()
                    )
                except BadRequest:
                    pass  # Message content is identical
            return ConversationHandler.END
        
        # Check rate limit
        can_send, message = self.rate_limiter.can_send_message(db_user.id)
        if not can_send:
            if update.message:
                await update.message.reply_text(
                    message,
                    reply_markup=self.get_main_menu_keyboard()
                )
            elif update.callback_query:
                await update.callback_query.answer()
                try:
                    await update.callback_query.edit_message_text(
                        message,
                        reply_markup=self.get_main_menu_keyboard()
                    )
                except BadRequest:
                    pass  # Message content is identical
            return ConversationHandler.END
        
        remaining = self.rate_limiter.get_remaining_messages(db_user.id)
        if update.callback_query:
            await update.callback_query.answer()
            try:
                await update.callback_query.edit_message_text(
                    f"Please enter the license plate number of the recipient:\n"
                    f"(You have {remaining} message(s) remaining this hour)"
                )
            except BadRequest:
                pass  # Message content is identical
        else:
            await update.message.reply_text(
                f"Please enter the license plate number of the recipient:\n"
                f"(You have {remaining} message(s) remaining this hour)"
            )
        
        return SEND_MESSAGE
    
    async def send_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Send a message to the owner of the specified license plate.
        
        Args:
            update: The Telegram update object.
            context: The callback context.
        """
        sender = update.effective_user
        db_sender = UserRepository.get_by_telegram_id(sender.id)
        plate_number = update.message.text.strip().upper()
        
        # Find the license plate
        plate = LicensePlateRepository.get_by_plate_number(plate_number)
        
        if not plate:
            await update.message.reply_text(
                f"❌ License plate `{plate_number}` not found.\n"
                "Please check the number and try again.",
                parse_mode="Markdown",
                reply_markup=self.get_main_menu_keyboard()
            )
            return ConversationHandler.END
        
        # Check if sending to self
        if plate.user_id == db_sender.id:
            await update.message.reply_text(
                "❌ You cannot send a message to yourself.",
                reply_markup=self.get_main_menu_keyboard()
            )
            return ConversationHandler.END
        
        # Get recipient
        recipient = UserRepository.get_by_id(plate.user_id)
        
        if not recipient:
            await update.message.reply_text(
                "❌ Could not find the license plate owner.",
                reply_markup=self.get_main_menu_keyboard()
            )
            return ConversationHandler.END
        
        # Check rate limit again
        can_send, message = self.rate_limiter.can_send_message(db_sender.id)
        if not can_send:
            await update.message.reply_text(
                message,
                reply_markup=self.get_main_menu_keyboard()
            )
            return ConversationHandler.END
        
        # Prepare message
        message_text = self.config.message_template.replace(
            "{licence_plate}",
            plate_number
        )
        
        # Record message in history
        MessageHistoryRepository.create(
            sender_id=db_sender.id,
            recipient_id=recipient.id,
            license_plate_id=plate.id,
            message_text=message_text
        )
        
        # Send message to recipient
        try:
            await context.bot.send_message(
                chat_id=recipient.telegram_id,
                text=f"📨 *New Message*\n\n{message_text}",
                parse_mode="Markdown"
            )
            
            await update.message.reply_text(
                f"✅ Message sent to the owner of `{plate_number}`!",
                parse_mode="Markdown",
                reply_markup=self.get_main_menu_keyboard()
            )
        except Exception as e:
            logger.error(f"Error sending message: {e}")
            await update.message.reply_text(
                "❌ Could not send the message. "
                "The recipient may have blocked the bot.",
                reply_markup=self.get_main_menu_keyboard()
            )
        
        return ConversationHandler.END
    
    async def send_username_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Start the Share Contact conversation.
        
        Args:
            update: The Telegram update object.
            context: The callback context.
        """
        user = update.effective_user
        db_user = UserRepository.get_by_telegram_id(user.id)
        
        if not db_user:
            if update.message:
                await update.message.reply_text(
                    "Please use /start to register first.",
                    reply_markup=self.get_main_menu_keyboard()
                )
            elif update.callback_query:
                await update.callback_query.answer()
                try:
                    await update.callback_query.edit_message_text(
                        "Please use /start to register first.",
                        reply_markup=self.get_main_menu_keyboard()
                    )
                except BadRequest:
                    pass  # Message content is identical
            return ConversationHandler.END
        
        # Check rate limit
        can_send, message = self.rate_limiter.can_send_message(db_user.id)
        if not can_send:
            if update.message:
                await update.message.reply_text(
                    message,
                    reply_markup=self.get_main_menu_keyboard()
                )
            elif update.callback_query:
                await update.callback_query.answer()
                try:
                    await update.callback_query.edit_message_text(
                        message,
                        reply_markup=self.get_main_menu_keyboard()
                    )
                except BadRequest:
                    pass  # Message content is identical
            return ConversationHandler.END
        
        remaining = self.rate_limiter.get_remaining_messages(db_user.id)
        if update.callback_query:
            await update.callback_query.answer()
            try:
                await update.callback_query.edit_message_text(
                    f"Please enter the license plate number of the recipient:\n"
                    f"(You have {remaining} message(s) remaining this hour)"
                )
            except BadRequest:
                pass  # Message content is identical
        else:
            await update.message.reply_text(
                f"Please enter the license plate number of the recipient:\n"
                f"(You have {remaining} message(s) remaining this hour)"
            )
        
        return SEND_USERNAME_PLATE
    
    async def send_username_plate_entry(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Process the license plate number and show privacy warning with confirmation.
        
        Args:
            update: The Telegram update object.
            context: The callback context.
        """
        sender = update.effective_user
        db_sender = UserRepository.get_by_telegram_id(sender.id)
        plate_number = update.message.text.strip().upper()
        
        # Find the license plate
        plate = LicensePlateRepository.get_by_plate_number(plate_number)
        
        if not plate:
            await update.message.reply_text(
                f"❌ License plate `{plate_number}` not found.\n"
                "Please check the number and try again.",
                parse_mode="Markdown",
                reply_markup=self.get_main_menu_keyboard()
            )
            return ConversationHandler.END
        
        # Check if sending to self
        if plate.user_id == db_sender.id:
            await update.message.reply_text(
                "❌ You cannot send your username to yourself.",
                reply_markup=self.get_main_menu_keyboard()
            )
            return ConversationHandler.END
        
        # Get recipient
        recipient = UserRepository.get_by_id(plate.user_id)
        
        if not recipient:
            await update.message.reply_text(
                "❌ Could not find the license plate owner.",
                reply_markup=self.get_main_menu_keyboard()
            )
            return ConversationHandler.END
        
        # Store plate number and recipient in context for confirmation
        context.user_data['send_username_plate'] = plate_number
        context.user_data['send_username_recipient'] = recipient
        
        # Create confirmation keyboard
        keyboard = [
            [
                InlineKeyboardButton("✅ Send", callback_data="confirm_send_username"),
                InlineKeyboardButton("❌ Cancel", callback_data="cancel_send_username")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Show privacy warning
        sender_username = db_sender.username
        privacy_warning = (
            f"⚠️ *Privacy Warning*\n\n"
            f"You are about to send your Telegram username (@{sender_username}) "
            f"to the owner of license plate `{plate_number}`.\n\n"
            f"This will make your username visible to the recipient. "
            f"Your message will no longer be private.\n\n"
            f"Do you want to proceed?"
        )
        
        await update.message.reply_text(
            privacy_warning,
            parse_mode="Markdown",
            reply_markup=reply_markup
        )
        
        return SEND_USERNAME_CONFIRM
    
    async def send_username_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Handle the Share Contact confirmation callback.
        
        Args:
            update: The Telegram update object.
            context: The callback context.
        """
        query = update.callback_query
        await query.answer()
        
        if query.data == "cancel_send_username":
            # Clear user data
            context.user_data.pop('send_username_plate', None)
            context.user_data.pop('send_username_recipient', None)
            
            await query.edit_message_text(
                "Operation cancelled.",
                reply_markup=self.get_main_menu_keyboard()
            )
            return ConversationHandler.END
        
        if query.data == "confirm_send_username":
            # Get stored data
            plate_number = context.user_data.get('send_username_plate')
            recipient = context.user_data.get('send_username_recipient')
            
            if not plate_number or not recipient:
                await query.edit_message_text(
                    "❌ An error occurred. Please try again.",
                    reply_markup=self.get_main_menu_keyboard()
                )
                return ConversationHandler.END
            
            # Get sender
            sender = update.effective_user
            db_sender = UserRepository.get_by_telegram_id(sender.id)
            
            # Find the license plate again to get the plate ID
            plate = LicensePlateRepository.get_by_plate_number(plate_number)
            
            if not plate:
                await query.edit_message_text(
                    f"❌ License plate `{plate_number}` not found.",
                    parse_mode="Markdown",
                    reply_markup=self.get_main_menu_keyboard()
                )
                return ConversationHandler.END
            
            # Check rate limit again
            can_send, message = self.rate_limiter.can_send_message(db_sender.id)
            if not can_send:
                await query.edit_message_text(
                    message,
                    reply_markup=self.get_main_menu_keyboard()
                )
                return ConversationHandler.END
            
            # Prepare message
            sender_username = db_sender.username
            message_text = f"User @{sender_username} wants to contact you regarding your vehicle with license plate {plate_number}"
            
            # Record message in history
            MessageHistoryRepository.create(
                sender_id=db_sender.id,
                recipient_id=recipient.id,
                license_plate_id=plate.id,
                message_text=message_text
            )
            
            # Send message to recipient
            try:
                await context.bot.send_message(
                    chat_id=recipient.telegram_id,
                    text=f"📨 *New Contact Request*\n\n{message_text}",
                    parse_mode="Markdown"
                )
                
                await query.edit_message_text(
                    f"✅ Your username has been sent to the owner of `{plate_number}`!",
                    parse_mode="Markdown",
                    reply_markup=self.get_main_menu_keyboard()
                )
            except Exception as e:
                logger.error(f"Error sending username: {e}")
                await query.edit_message_text(
                    "❌ Could not send the message. "
                    "The recipient may have blocked the bot.",
                    reply_markup=self.get_main_menu_keyboard()
                )
            
            # Clear user data
            context.user_data.pop('send_username_plate', None)
            context.user_data.pop('send_username_recipient', None)
            
            return ConversationHandler.END
        
        return ConversationHandler.END
    
    async def menu_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """
        Handle main menu button callbacks.
        
        Args:
            update: The Telegram update object.
            context: The callback context.
        """
        query = update.callback_query
        await query.answer()
        
        callback_data = query.data
        
        if callback_data == "menu_myplates":
            # Trigger my_plates command
            user = update.effective_user
            db_user = UserRepository.get_by_telegram_id(user.id)
            
            if not db_user:
                try:
                    await query.edit_message_text(
                        "Please use /start to register first.",
                        reply_markup=self.get_main_menu_keyboard()
                    )
                except BadRequest:
                    pass  # Message content is identical
                return
            
            plates = LicensePlateRepository.get_by_user(db_user.id)
            
            if not plates:
                try:
                    await query.edit_message_text(
                        "You don't have any license plates registered.\n"
                        "Use /addplate to add one.",
                        reply_markup=self.get_main_menu_keyboard()
                    )
                except BadRequest:
                    pass  # Message content is identical
                return
            
            plates_list = "🚗 *Your License Plates:*\n\n"
            for i, plate in enumerate(plates, 1):
                plates_list += f"{i}. `{plate.plate_number}`\n"
            
            plates_list += f"\n*Total: {len(plates)} plate(s)*"
            
            try:
                await query.edit_message_text(
                    plates_list,
                    parse_mode="Markdown",
                    reply_markup=self.get_main_menu_keyboard()
                )
            except BadRequest:
                    pass  # Message content is identical
            
        elif callback_data == "menu_addplate":
            # This is handled by the conversation handler entry point
            # Just answer the callback and let the conversation handler take over
            return
        elif callback_data == "menu_deleteplate":
            # This is handled by the conversation handler entry point
            return
        elif callback_data == "menu_sendmsg":
            # This is handled by the conversation handler entry point
            return
        elif callback_data == "menu_sharecontact":
            # This is handled by the conversation handler entry point
            return
        elif callback_data == "menu_help":
            # Trigger help_command
            help_message = (
                "📖 *CarBlockPy2 Help*\n\n"
                "*How to send a message:*\n"
                "1. Click \"Send Message\" button\n"
                "2. Enter the license plate number\n"
                "3. The bot will send a message to the owner\n\n"
                "*Rate Limiting:*\n"
                f"You can send up to {self.config.rate_limiting.max_messages_per_hour} "
                "messages per hour."
            )
            
            try:
                await query.edit_message_text(
                    help_message,
                    parse_mode="Markdown",
                    reply_markup=self.get_main_menu_keyboard()
                )
            except BadRequest:
                    pass  # Message content is identical
    
    def setup_handlers(self):
        """Set up all bot handlers."""
        # Add plate conversation handler
        add_plate_handler = ConversationHandler(
            entry_points=[
                CmdHandler("addplate", self.add_plate_start),
                CallbackQueryHandler(
                    self.add_plate_start,
                    pattern=r"^menu_addplate$"
                ),
            ],
            states={
                ADD_PLATE: [
                    MessageHandler(
                        filters.TEXT & ~filters.COMMAND,
                        self.add_plate
                    )
                ],
            },
            fallbacks=[
                CmdHandler("cancel", self.cancel_conversation),
                MessageHandler(filters.COMMAND, self.cancel_conversation)
            ],
        )
        
        # Delete plate conversation handler
        delete_plate_handler = ConversationHandler(
            entry_points=[
                CmdHandler("deleteplate", self.delete_plate_start),
                CallbackQueryHandler(
                    self.delete_plate_start,
                    pattern=r"^menu_deleteplate$"
                ),
            ],
            states={
                DELETE_PLATE: [
                    CallbackQueryHandler(
                        self.delete_plate_callback,
                        pattern=r"^(delete_|cancel_delete)"
                    )
                ],
            },
            fallbacks=[
                CmdHandler("cancel", self.cancel_conversation),
                MessageHandler(filters.TEXT, self.cancel_conversation)
            ],
        )
        
        # Send message conversation handler
        send_message_handler = ConversationHandler(
            entry_points=[
                CmdHandler("sendmsg", self.send_message_start),
                CallbackQueryHandler(
                    self.send_message_start,
                    pattern=r"^menu_sendmsg$"
                ),
            ],
            states={
                SEND_MESSAGE: [
                    MessageHandler(
                        filters.TEXT & ~filters.COMMAND,
                        self.send_message
                    )
                ],
            },
            fallbacks=[
                CmdHandler("cancel", self.cancel_conversation),
                MessageHandler(filters.COMMAND, self.cancel_conversation)
            ],
        )
        
        # Share Contact conversation handler
        send_username_handler = ConversationHandler(
            entry_points=[
                CmdHandler("sendusername", self.send_username_start),
                CallbackQueryHandler(
                    self.send_username_start,
                    pattern=r"^menu_sharecontact$"
                ),
            ],
            states={
                SEND_USERNAME_PLATE: [
                    MessageHandler(
                        filters.TEXT & ~filters.COMMAND,
                        self.send_username_plate_entry
                    )
                ],
                SEND_USERNAME_CONFIRM: [
                    CallbackQueryHandler(
                        self.send_username_callback,
                        pattern=r"^(confirm_send_username|cancel_send_username)"
                    )
                ],
            },
            fallbacks=[
                CmdHandler("cancel", self.cancel_conversation),
                MessageHandler(filters.TEXT, self.cancel_conversation),
                MessageHandler(filters.COMMAND, self.cancel_conversation)
            ],
        )
        
        # Menu button callback handler for non-conversation buttons
        # Note: menu_addplate, menu_deleteplate, menu_sendmsg, menu_sharecontact are handled by conversation handlers
        menu_handler = CallbackQueryHandler(
            self.menu_callback,
            pattern=r"^(menu_myplates|menu_help)$"
        )
        
        return [
            menu_handler,
            CmdHandler("start", self.start),
            CmdHandler("help", self.help_command),
            CmdHandler("myplates", self.my_plates),
            add_plate_handler,
            delete_plate_handler,
            send_message_handler,
            send_username_handler,
        ]
    
    def run(self):
        """Start the bot."""
        # Initialize database connection pool
        from src.database import init_connection_pool
        init_connection_pool()
        
        # Create application
        self.application = Application.builder().token(
            self.config.telegram.bot_token
        ).build()
        
        # Add handlers
        for handler in self.setup_handlers():
            self.application.add_handler(handler)
        
        # Start bot
        logger.info("Starting CarBlockPy2 bot...")
        self.application.run_polling(allowed_updates=Update.ALL_TYPES)
    
    def stop(self):
        """Stop the bot and cleanup resources."""
        if self.application:
            self.application.stop()
        
        from src.database import close_connection_pool
        close_connection_pool()


def main():
    """Main entry point for the bot."""
    bot = CarBlockBot()
    
    try:
        bot.run()
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
        bot.stop()
    except Exception as e:
        logger.error(f"Bot error: {e}")
        bot.stop()


if __name__ == "__main__":
    main()
