import sqlite3 as sql

# Configure CS50 Library to use SQLite database
db = sql.connect("finance.db",
	isolation_level=None, # enables autocommit
	check_same_thread=False # allows multithread
)
db.row_factory = sql.Row # uses dict-like objects instead of tuples

def SQL(statement, *pos_var, **name_var): 
	# simpler syntax for variables, returns list of Row obj instead of Cursor obj
	if len(pos_var) > 0 and len(name_var) > 0:
		raise SyntaxError("Cannot use both positional and named variables")

	if len(name_var) > 0:
		return db.execute(statement, name_var).fetchall()
	
	return db.execute(statement, pos_var).fetchall()

try:
	inserted_row_id = SQL("""
			insert into portfolios (user_id, symbol, shares)
			values (:user_id, :symbol, :shares)
			returning id
		""",
		user_id=25, symbol="ACN", shares=100
	)
	print(f"Inserted row with id: {inserted_row_id[0]['id']}")
except sql.IntegrityError:
	print("stock already in portfolio")

rows = SQL("""
		select * from portfolios where user_id = ? and symbol = ?
	""", 
	25, "ACN"
)

print("Table content:")
for row in rows:
	print(dict(row))