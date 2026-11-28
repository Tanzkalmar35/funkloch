CREATE TABLE IF NOT EXISTS chats (
    chat_id TEXT PRIMARY KEY NOT NULL,
    name TEXT NOT NULL,
    owner_server_id TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS messages (
    message_id TEXT PRIMARY KEY NOT NULL,
    chat_id TEXT NOT NULL,
    sender TEXT NOT NULL,
    content TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    sequence_number INTEGER,

    FOREIGN KEY (chat_id)
        REFERENCES chats(chat_id)
);

CREATE INDEX IF NOT EXISTS idx_messages_chat
ON messages(chat_id);