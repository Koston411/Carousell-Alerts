from sqlalchemy import Column, Integer, String, Table, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()

listing_chat_table = Table(
    'listing_chat',
    Base.metadata,
    Column('chat_id', ForeignKey('chats.id')),
    Column('listing_id', ForeignKey('listings.id'))
)

keyword_chat_table = Table(
    'keyword_chat',
    Base.metadata,
    Column('keyword_id', ForeignKey('keywords.id')),
    Column('chat_id', ForeignKey('chats.id'))
)

class Chat(Base):
    __tablename__ = 'chats'

    id = Column(Integer, primary_key=True)
    chat_id = Column(String)
    keywords = relationship(
        'Keyword',
        secondary = keyword_chat_table,
        back_populates = 'chats'
    )
    listings = relationship(
        'CarousellListingDB',
        secondary = listing_chat_table,
        back_populates = 'chats'
    )

class Keyword(Base):
    __tablename__ = 'keywords'

    id = Column(Integer, primary_key=True)
    keyword_str = Column(String)
    chats = relationship(
        'Chat',
        secondary = keyword_chat_table,
        back_populates = 'keywords'
    )

class CarousellListingDB(Base):
    __tablename__ = 'listings'
    id = Column(Integer, primary_key=True)
    platform = Column(String)
    listing_id = Column(String)
    title = Column(String)
    price = Column(String)
    image = Column(String)
    seller = Column(String)
    url = Column(String)
    chats = relationship(
        'Chat',
        secondary = listing_chat_table,
        back_populates = 'listings'
    )