from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from classified_item import Classified_item
import slack_chatbot as robot
from telegram_chatbot import TelegramChatBot
from DB_elements import Keyword, CarousellListingDB, Chat

Base = declarative_base()

class Processing_items():
    engine = create_engine('sqlite:///Database/marabou_alert.db')
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    session = Session()

    # def telegram_bot_sendtext(bot_message):
    # # print(bot_message)
    # send_text = 'https://api.telegram.org/bot' + bot_token + '/sendMessage?chat_id=' + bot_chatID + '&parse_mode=Markdown&text=' + bot_message.to_string()

    # response = requests.get(send_text)

    # return response.json()

    def start_process_items(self, item: Classified_item, search_keyword):
        if item:            
            # Check if listing is in DB already
            listing_DB_obj = (self.session.query(CarousellListingDB).filter_by(listing_id=item.listing_id).first())
            
            # If listing is not in DB, we add it
            if listing_DB_obj is None:
            # if True:
                # print ("-------------------------------- Send notification")
                # print (item.toJSON())
                # print ("--------------------------------------------------")

                # keyword_id = self.session.query(Keyword).filter_by(keyword_str=).first()

                # Create DB object
                listing_DB_obj = CarousellListingDB(
                    platform = item.platform,
                    listing_id = item.listing_id,
                    title = item.title,
                    price = item.price,
                    image = item.image,
                    seller = item.seller,
                    url = item.url
                )

                # Insert the object in DB
                self.session.add(listing_DB_obj)

            #
            # Find the group chats to send the notifications to
            #
            # print ('+++++++++++++++++++++++++++++++' + search_keyword + "   " + item.listing_id)
            
            # Find the chat groups that subscribed to a keyword
            chats_associated_with_keyword = []
            for chat_DB_obj in self.session.query(Chat).filter(Chat.keywords.any(Keyword.keyword_str == search_keyword)).all():
                chats_associated_with_keyword.append(chat_DB_obj.chat_id)

            # print ("chats_associated_with_keyword: ")
            # print (chats_associated_with_keyword)

            
            # Find the chats that have already been notified for the listing
            chats_already_processed = []
            for chat_DB_obj in self.session.query(Chat).filter(Chat.listings.any(CarousellListingDB.listing_id == item.listing_id)).all():
                chats_already_processed.append(chat_DB_obj.chat_id)
            
            # print ("chats_already_processed: ")
            # print (chats_already_processed)

            chats_to_notify = [string for string in chats_associated_with_keyword if string not in chats_already_processed]
            # print ("Chats to notify: ")
            # print (chats_to_notify)
            
            # Mark the listing as sent to users group chat (notification sent) in DB
            chat_DB_obj = self.session.query(Chat).filter(Chat.chat_id.in_(chats_to_notify)).all()
            if chat_DB_obj:
                listing_DB_obj.chats.extend(chat_DB_obj)
            
            # Commit all changes in DB from above
            self.session.commit()
                
            # # Send notifications to Slack
            # robot.slack_post_message(item)

            # Send notifications to Telegram
            TelegramChatBot.prepare_alert(item, chats_to_notify)

            return