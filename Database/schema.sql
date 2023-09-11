DROP TABLE IF EXISTS listings;
DROP TABLE IF EXISTS chats;
DROP TABLE IF EXISTS listing_chat;

CREATE TABLE listings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    platform TEXT NOT NULL,
    listing_id TEXT NOT NULL,
    created TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    title TEXT NOT NULL,
    price TEXT NOT NULL,
    image TEXT,
	seller TEXT NOT NULL,
	url TEXT NOT NULL
);

CREATE TABLE chats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id TEXT NOT NULL
);

CREATE TABLE keywords (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    keyword_str TEXT NOT NULL,
    filter_str TEXT
);

CREATE TABLE keyword_chat (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    keyword_id INTEGER,
    chat_id INTEGER,
    FOREIGN KEY(keyword_id) REFERENCES keywords(id),
    FOREIGN KEY(chat_id) REFERENCES chats(id)
);

CREATE TABLE listing_chat (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    chat_id INTEGER,
    listing_id INTEGER,
    FOREIGN KEY(chat_id) REFERENCES chats(id),
    FOREIGN KEY(listing_id) REFERENCES listings(id)
);