from pycarousell import CarousellSearch
from configuration import RESULTS_COUNT
from telegram_chatbot import TelegramChatBot

if __name__ == "__main__":
    TelegramChatBot()
    CarousellSearch(results=RESULTS_COUNT)
