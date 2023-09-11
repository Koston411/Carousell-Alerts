from ast import keyword
import logging
import json
import html
from configuration import DEBUG
import telegram
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackQueryHandler
from sqlalchemy import insert, update, text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from DB_elements import CarousellListingDB, Keyword, Chat

# Initialise logs
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.WARNING)
logger = logging.getLogger(__name__)

# Initialise BD
Base = declarative_base()


class TelegramChatBot():
    updater = Updater(
        "5158328999:AAH8ceaw8w5VfYhtwaCEe8E7ijvmTgfsMk0", use_context=True)
    dispatcher = updater.dispatcher

    engine = create_engine('sqlite:///Database/marabou_alert.db', future=True)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    setup_keyword_status = {}

    def error(self, upd, context):
        logger.warning('Update "%s" caused error "%s"', upd, context.error)

    def help(self, upd, context):
        context.bot.send_message(chat_id=upd.effective_chat.id, text='Here are the commands you can use for me to help you:\n/help: get the list of commands\n/list: get you the list of keywords that Marabou Bot will look for you\n/add KEYWORD: adds a new keyword to look for\n/remove: removes an existing keyword')

    def start(self, upd, context):
        chat_id = self.register_chat_id(upd, context)

        if (upd.effective_chat.first_name):
            message = "Bienvenido " + upd.effective_chat.first_name + \
                " !!! I'm Marabou Bot to help you be alerted if I find new listings on Carousell. Type /help if you want to know how to work with me"
        else:
            message = "Bienvenido !!! I'm Marabou Bot to help you be alerted if I find new listings on Carousell. Type /help if you want to know how to work with me"

        context.bot.send_message(chat_id=chat_id, text=message)

    def chat_created(self, upd, context):
        chat_id = self.register_chat_id(upd, context)
        message = "Bienvenido " + upd.effective_chat.first_name + \
            " !!! I'm Marabou Bot to help you be alerted if I find new listings on Carousell. Type /help if you want to know how to work with me"
        context.bot.send_message(chat_id=chat_id, text=message)

    def new_member(self, upd, context):
        for member in upd.message.new_chat_members:
            chat_id = self.register_chat_id(upd, context)
            message = "Bienvenido " + member.first_name + \
                " !!! I'm Marabou Bot to help you be alerted if I find new listings on Carousell. Type /help if you want to know how to work with me"
            context.bot.send_message(chat_id=chat_id, text=message)

    def unknown(self, upd, context):
        if (not self.setup_keyword_status):
            context.bot.send_message(chat_id=upd.effective_chat.id,text="Sorry, I don't speak your language. You can type /help to learn about the commands I know")
        elif (self.setup_keyword_status['action'] == 'addKeyword'):
            chatID = upd.effective_chat.id

            # Check if the messsage sent by the user is a number
            if (upd['message']['text'].isnumeric()):
                self.setup_keyword_status['filter'] = upd['message']['text']
                self.add_keyword_in_DB(chatID, context)
            else:
                message = 'Come on bro, just enter digits\! You think I deal with that currency\!\!'
                context.bot.send_message(
                    chat_id=chatID, text=message, parse_mode=telegram.constants.PARSEMODE_MARKDOWN_V2)
            
    def register_chat_id(self, upd, context):
        id = str(upd.effective_chat.id)

        # Insert chat_id to DB
        instance = self.session.query(Chat).filter_by(chat_id=id).first()
        statement = None
        if instance:
            statement = (
                update(Chat).
                where(Chat.chat_id == id).
                values(
                    chat_id=id
                )
            )
        else:
            statement = (
                insert(Chat).values(
                    chat_id=id
                )
            )
        self.session.execute(statement)
        self.session.commit()

        return id
    
    def add_keyword_in_DB(self, chatID, context):
        # Create chat DB object to associate it to the keyword
        chat = self.session.query(Chat).filter(Chat.chat_id == chatID).first()
        
        # Set the keyword string to be inserted in DB
        keyword_str = self.setup_keyword_status['keyword']

        # Set the filter string to be inserted in DB if it is given by user
        filter_str = ''
        if ('filter' in self.setup_keyword_status):
            filter_str = self.setup_keyword_status['filter']
        
        # Add keyword in DB if it doesn't exist
        keyword_obj = self.session.query(Keyword).filter_by(
                keyword_str=keyword_str).first()
        
        if not keyword_obj:
            keyword_obj = Keyword(keyword_str=keyword_str, filter_str=filter_str)
            self.session.add(keyword_obj)

        chat.keywords.append(keyword_obj)
        self.session.commit()

        message = '*_' + self.clean_message_for_telegram(keyword_str) + '_* is added to your list of keywords'
        context.bot.send_message(chat_id=chatID, text=message, parse_mode=telegram.constants.PARSEMODE_MARKDOWN_V2)

        self.setup_keyword_status = {}

    def add_keyword_command(self, upd, context):
        try:
            # Set the keyword status worklow to None
            self.setup_keyword_status['action'] = 'addKeyword'

            id = str(upd.effective_chat.id)

            # Extract the keyword from the received bot command
            keyword_string = ' '.join(context.args).lower()

            message = 'Do you want to add "' + keyword_string + '" without filter?'

            data = 'add1' + "|" + keyword_string
            buttons = [[InlineKeyboardButton("OK", callback_data=data + "|ok")],
                       [InlineKeyboardButton("Add filters", callback_data=data + "|filtr")]]

            reply_markup = InlineKeyboardMarkup(buttons)
            context.bot.send_message(
                chat_id=id, text=message, reply_markup=reply_markup)

        except (IndexError, ValueError):
            upd.message.reply_text('Error, the search query is not added')

    def list_keywords(self, upd, context):
        # Set the keyword status worklow to None
        self.setup_keyword_status = {}

        id = str(upd.effective_chat.id)
        chat = self.session.query(
            Chat).filter(Chat.chat_id == id).first()

        keyword_str = 'Your search keywords:\n'
        if (len(chat.keywords) > 0):
            for keyword in chat.keywords:
                keyword_str += '\- _*' + keyword.keyword_str + '*_\n'
        else:
            keyword_str = self.clean_message_for_telegram(
                "No keyword yet, to add a keyword use the command: /add + keyword")

        context.bot.send_message(
            chat_id=id, text=keyword_str, parse_mode=telegram.constants.PARSEMODE_MARKDOWN_V2)

    def remove_keyword(self, upd, context):
        # Set the keyword status worklow to None
        self.setup_keyword_status = {}

        id = str(upd.effective_chat.id)
        chat = self.session.query(
            Chat).filter(Chat.chat_id == id).first()

        message = 'Select the keyword you want to remove:'
        buttons = []
        if (len(chat.keywords) == 0):
            message = 'No keyword to delete'
        else:
            for keyword in chat.keywords:
                data = 'rmKey' + "|" + str(keyword.id)
                buttons.append([InlineKeyboardButton(
                    keyword.keyword_str, callback_data=data)])

        reply_markup = InlineKeyboardMarkup(buttons)
        context.bot.send_message(
            chat_id=id, text=message, reply_markup=reply_markup)

    def callback(self, upd, context):

        args = upd.callback_query.data.split('|')
        chatID = upd.effective_chat.id

        # Get the type of the action requested
        if (args[0] == 'add1' and args[2] == 'ok'):
            self.setup_keyword_status['keyword'] = args[1]
            self.add_keyword_in_DB(chatID, context)

        elif (args[0] == 'add1' and args[2] == 'filtr'):
            self.setup_keyword_status['keyword'] = args[1]

            message = 'What is the maximum price you want to pay for your ' + self.clean_message_for_telegram(
                args[1]) + '?'
            context.bot.send_message(
                chat_id=chatID, text=message, parse_mode=telegram.constants.PARSEMODE_MARKDOWN_V2)

        elif (args[0] == 'rmKey'):
            if upd.callback_query.message is None:
                upd.answer_callback_query(
                    callback_query_id=upd.callback_query.id
                )
                return

            keyword_id = args[1]
            keyword = self.session.query(
                Keyword).filter(Keyword.id == keyword_id).first()
            chat = self.session.query(
                Chat).filter(Chat.chat_id == chatID).first()

            message = "%s has been removed" % keyword.keyword_str
            context.bot.send_message(chat_id=chatID, text=message)

            keyword.chats.remove(chat)
            self.session.commit()

    @classmethod
    def clean_message_for_telegram(self, str, type=''):
        return telegram.utils.helpers.escape_markdown(str, version=2, entity_type=type)

    @classmethod
    def prepare_alert(self, item, chat_IDs, search_keyword):

        # Clean the different elements of the message before sending to Telegram
        title = self.clean_message_for_telegram(item.title)
        price = self.clean_message_for_telegram(item.price)
        seller = self.clean_message_for_telegram(item.seller)
        image = self.clean_message_for_telegram(item.image, type="TEXT_LINKS")
        url = self.clean_message_for_telegram(item.url, type="TEXT_LINKS")

        message = "*" + title + "*\n[​​​​​​​​​​​](" + image + ")_Price:_ " + price + \
            "\n_Seller:_ " + seller + \
            "\n[Open listing in Carousell](" + url + ")"
        for chat_ID in chat_IDs:
            try:
                self.updater.dispatcher.bot.sendMessage(
                    chat_id=chat_ID, text=message, parse_mode=telegram.constants.PARSEMODE_MARKDOWN_V2)
            except Exception as e:
                if (str(e) == 'Forbidden: bot was kicked from the group chat'):
                    # Remove chat ID as it's not valid anymore
                    chat = self.session.query(
                        Chat).filter(Chat.chat_id == chat_ID).first()
                    self.session.delete(chat)
                    self.session.commit()
                else:
                    print('ERROR: ' + str(e))

    def log_update(self, u, c):
        id = str(u.effective_chat.id)
        message = (
            'Received a new update event from telegram\n'
            f'update = {json.dumps(u.to_dict(), indent = 2, ensure_ascii = False)}\n'
            f'user_data = {json.dumps(c.user_data, indent = 2, ensure_ascii = False)}\n'
            f'chat_data = {json.dumps(c.chat_data, indent = 2, ensure_ascii = False)}'
        )
        logging.info(message)
        if DEBUG:
            try:
                c.bot.send_message(id, html.escape(
                    message), parse_mode=telegram.constants.PARSEMODE_HTML)
            except Exception as e:
                print(e)

    def __init__(self):

        # Help handler
        help_handler = CommandHandler("help", self.help)
        self.dispatcher.add_handler(help_handler)

        # Start handler
        start_handler = CommandHandler("start", self.start)
        self.dispatcher.add_handler(start_handler)

        # Add keyword handler
        add_handler = CommandHandler("add", self.add_keyword_command)
        self.dispatcher.add_handler(add_handler)

        # Remove keyword handler
        remove_handler = CommandHandler("remove", self.remove_keyword)
        self.dispatcher.add_handler(remove_handler)

        # List keywords handler
        list_handler = CommandHandler("list", self.list_keywords)
        self.dispatcher.add_handler(list_handler)

        # Handler new user in the group chat
        new_member_handler = MessageHandler(
            Filters.status_update.new_chat_members, self.new_member)
        self.dispatcher.add_handler(new_member_handler)

        chat_created_handler = MessageHandler(
            Filters.status_update.chat_created, self.chat_created)
        self.dispatcher.add_handler(chat_created_handler)

        # Callback query handler
        self.dispatcher.add_handler(CallbackQueryHandler(self.callback))

        # log all errors
        self.dispatcher.add_error_handler(self.error)

        # unknown_handler = MessageHandler(Filters.all, unknown)
        unknown_handler = MessageHandler(Filters.all, self.unknown)
        self.dispatcher.add_handler(unknown_handler)

        # Start the Bot
        self.updater.start_polling()

        # Run the bot until you press Ctrl-C or the process receives SIGINT,
        # SIGTERM or SIGABRT. This should be used most of the time, since
        # start_polling() is non-blocking and will stop the bot gracefully.
        # self.updater.idle()
