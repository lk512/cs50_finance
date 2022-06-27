DROP TABLE history;

CREATE TABLE history (
   id INTEGER PRIMARY KEY AUTOINCREMENT,
   date_time TEXT DEFAULT CURRENT_TIMESTAMP NOT NULL,
   user_id INTEGER NOT NULL,
   type TEXT CHECK(type in ("buy", "sell", "withdraw", "deposit")),
   symbol TEXT NOT NULL,
   shares INTEGER CHECK(shares >= 0),
   price REAL CHECK(price >= 0),
   total REAL NOT NULL,
   FOREIGN KEY(user_id) REFERENCES users(id)
) STRICT;