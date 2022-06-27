import sqlite3 as sql

db = sql.connect("finance.db",
	isolation_level=None, # enables autocommit
	check_same_thread=False # allows multithread
)
db.row_factory = sql.Row # uses dict-like objects instead of tuples

username1 = "lk512"
username2 = "lard"
password = "culo"

ins_return = db.execute("""
	insert into users (username,hash)
	values  (:username1, :password),
			(:username2, :password)
	returning id
	""", 
	{'username1':username1, 'username2':username2, 'password':password}
).fetchall() # converts cursor to list of row objects

print(dict(ins_return[0]))