drop table portfolios;

create table portfolios (
   id INTEGER PRIMARY KEY AUTOINCREMENT,
   user_id INTEGER NOT NULL,
   symbol TEXT NOT NULL,
   shares INTEGER CHECK(shares >= 0),
   FOREIGN KEY(user_id) REFERENCES users(id)
   UNIQUE(user_id, symbol)
) STRICT;