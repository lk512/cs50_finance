import os

import sqlite3 as sql
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, lookup, usd

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = sql.connect("finance.db",
	isolation_level=None, # enables autocommit
	check_same_thread=False # allows multithread
)
db.row_factory = sql.Row # uses dict-like objects instead of tuples

# Make sure API key is set
if not os.environ.get("API_KEY"):
	raise RuntimeError("API_KEY not set")


@app.after_request
def after_request(response):
	"""Ensure responses aren't cached"""
	response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
	response.headers["Expires"] = 0
	response.headers["Pragma"] = "no-cache"
	return response


@app.route("/login", methods=["GET", "POST"])
def login():
	"""Log user in"""

	# Forget any user_id
	session.clear()

	# User reached route via POST (as by submitting a form via POST)
	if request.method == "POST":

		username = request.form.get("username")
		password = request.form.get("password")

		# Ensure username was submitted
		if not username:
			return apology("must provide username", 403)

		# Ensure password was submitted
		elif not password:
			return apology("must provide password", 403)

		# Query database for username
		rows = db.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchall()

		# Ensure username exists and password is correct
		if len(rows) != 1 or not check_password_hash(rows[0]["hash"], password):
			return apology("invalid username and/or password", 403)

		# Remember which user has logged in
		session["user_id"] = rows[0]["id"]

		# Redirect user to home page
		return redirect("/")

	# User reached route via GET (as by clicking a link or via redirect)
	else:
		return render_template("login.html")


@app.route("/register", methods=["GET", "POST"])
def register():
	"""Register user"""

	 # User reached route via POST (as by submitting a form via POST)
	if request.method == "POST":

		username = request.form.get("username")
		password = request.form.get("password")
		confirmation = request.form.get("confirmation")

		# Ensure username was submitted
		if not username:
			return apology("must provide username", 400)

		rows = db.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchall()
		# Check if username already exists
		if len(rows) > 0:
			return apology(f"username {username} already exists", 400)

		# Ensure password was submitted and correctly confirmed
		if not password:
			return apology("must provide password", 400)
		elif password != confirmation:
			return apology("Passwords are not matching", 400)

		# stores credentials in database
		hash = generate_password_hash(password)
		db.execute("INSERT INTO users (username, hash) VALUES (?, ?)", (username, hash))

		# Automatically logs in and redirects to home page
		rows = db.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchall()
		session["user_id"] = rows[0]["id"]
		return redirect("/")

	# User reached route via GET (as by clicking a link or via redirect)
	else:
		return render_template("register.html")


@app.route("/")
@login_required
def index():
	"""Show portfolio of stocks"""

	# retrieves cash
	rows = db.execute("SELECT * FROM users WHERE id = ?", (session["user_id"],)).fetchall()
	if len(rows) == 0:
		return redirect("/login")
	username = rows[0]["username"]
	cash = rows[0]["cash"]

	# initialize grand total
	gtotal = cash

	rows = db.execute("SELECT * FROM portfolios WHERE user_id = ? AND shares > 0", (session["user_id"],)).fetchall()
	drows = [dict(row) for row in rows]  # row object does not support assignments :(

	for row in drows:
		symbol = row["symbol"]
		try:
			price = lookup(symbol)["price"]
		except:
			return apology(f"price for symbol {symbol} not found", 400)

		# adds a price and total keys to each row dictionary
		row["price"] = price
		row["total"] = price * row["shares"]

		# computes grand total
		gtotal += row["total"]

	return render_template("index.html", username=username, rows=drows, cash=cash, gtotal=gtotal)


@app.route("/quote", methods=["GET", "POST"])
@login_required
def quote():
	"""Get stock quote."""

	if request.method == "POST":
		symbol = request.form.get("symbol")
		if not symbol:
			return apology("must provide symbol", 400)

		answer = lookup(symbol)
		if not answer:
			return apology("symbol not found", 400)

		return render_template("quoted.html", answer=answer)

	else:
		return render_template("quote.html")


@app.route("/buy", methods=["GET", "POST"])
@login_required
def buy():
	"""Buy shares of stock"""
	user_id = session["user_id"]

	# retrieves cash balance for user
	rows = db.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchall()
	if len(rows) == 0:
		return apology("cash balance not found", 400)
	cash = rows[0]["cash"]

	if request.method == "POST":
		symbol = request.form.get("symbol")
		try:
			shares = int(request.form.get("shares"))
		except ValueError:
			return apology("must select at least 1 share", 400)

		if not symbol:
			return apology("must provide symbol", 400)

		if shares < 1:
			return apology("must select at least 1 share", 400)

		answer = lookup(symbol)
		if not answer:
			return apology("symbol not found", 400)

		price = answer["price"]
		total = shares * price

		if cash < total:
			return apology("insufficient cash for the purchase", 403)

		# inserts the new stock in user's portfolio or updates the existing shares count
		db.execute("""
			INSERT INTO portfolios (user_id, symbol, shares) VALUES (:user_id, :symbol, :shares)
			ON CONFLICT(user_id, symbol) DO UPDATE SET shares = shares + :shares
		""", {'user_id': user_id, 'symbol': symbol, 'shares': shares})

		# updates the cash balance
		db.execute("update users set cash = cash - ? where id = ?", (total, user_id))

		# records the transaction
		db.execute("""
			INSERT INTO history (user_id, type, symbol, shares, price, total)
			VALUES (?, ?, ?, ?, ?, ?)
		""", (user_id, "buy", symbol, shares, price, total))

		return redirect("/")
	else:
		return render_template("buy.html", cash=cash)


@app.route("/sell", methods=["GET", "POST"])
@login_required
def sell():
	"""Sell shares of stock"""
	user_id = session["user_id"]

	if request.method == "POST":
		symbol = request.form.get("symbol")
		try:
			shares = int(request.form.get("shares"))
		except ValueError:
			return apology("must select at least 1 share", 400)

		if not symbol:
			return apology("must provide symbol", 400)

		rows = db.execute("SELECT * FROM portfolios WHERE user_id = ? AND symbol = ?", (user_id, symbol)).fetchall()
		if len(rows) == 0:
			return apology("not enough shares in portfolio", 400)

		my_shares = int(rows[0]["shares"])
		if shares < 1:
			return apology("must sell at leat 1 share", 400)
		elif my_shares < shares:
			return apology("not enough shares in portfolio", 400)

		answer = lookup(symbol)
		if not answer:
			return apology("symbol not found", 400)

		price = answer["price"]
		total = shares * price

		 # removes the shars in user's portfolio
		db.execute("""
			UPDATE portfolios
			SET shares = shares - ?
			WHERE user_id = ?
			AND symbol = ?
		""", (shares, user_id, symbol))

		# updates the cash balance
		db.execute("update users set cash = cash + ? where id = ?", (total, user_id))

		# records the transaction
		db.execute("""
			INSERT INTO history (user_id, type, symbol, shares, price, total)
			VALUES (?, ?, ?, ?, ?, ?)
		""", (user_id, "sell", symbol, shares, price, -total))

		return redirect("/")

	else:
		# retrieves cash balance for user
		rows = db.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchall()
		if len(rows) == 0:
			return apology("cash balance not found", 400)
		cash = rows[0]["cash"]

		# retrieves portfolio for user
		rows = db.execute("SELECT * FROM portfolios WHERE user_id = ? AND shares > 0", (user_id,)).fetchall()
		if len(rows) == 0:
			return apology("portfolio is empty", 400)

		return render_template("sell.html", cash=cash, rows=rows)


@app.route("/withdraw", methods=["POST"])
@login_required
def withdraw():
	"""Withdraw money from account"""
	user_id = session["user_id"]

	# retrieves cash balance for user
	rows = db.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchall()
	if len(rows) == 0:
		return apology("cash balance not found", 400)
	cash = int(rows[0]["cash"])

	try:
		amount = int(request.form.get("amount"))
	except ValueError:
		return apology("must select at least 1$", 400)

	if amount < 1:
		return apology("must select at least 1$", 400)
	elif amount > cash:
		return apology("not enough cash available", 400)

	# updates the cash balance
	db.execute("UPDATE users SET cash = cash - ? WHERE id = ?", (amount, user_id))

	# records the transaction
	db.execute("""
		INSERT INTO history (user_id, type, symbol, shares, price, total)
		VALUES (?, ?, ?, ?, ?, ?)
	""", (user_id, "withdraw", "CASH", 0, 0, -amount))

	return redirect("/")


@app.route("/deposit", methods=["POST"])
@login_required
def deposit():
	"""Deposit money into account"""
	user_id = session["user_id"]

	# retrieves cash balance for user
	rows = db.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchall()
	if len(rows) == 0:
		return apology("cash balance not found", 400)
	cash = int(rows[0]["cash"])

	try:
		amount = int(request.form.get("amount"))
	except ValueError:
		return apology("must select at least 1$", 400)

	if amount < 1:
		return apology("must select at least 1$", 400)

	# updates the cash balance
	db.execute("UPDATE users SET cash = cash + ? WHERE id = ?", (amount, user_id))

	# records the transaction
	db.execute("""
		INSERT INTO history (user_id, type, symbol, shares, price, total)
		VALUES (?, ?, ?, ?, ?, ?)
	""", (user_id, "deposit", "CASH", 0, 0, amount))

	return redirect("/")


@app.route("/history")
@login_required
def history():
	"""Show history of transactions"""

	rows = db.execute("SELECT SUM(total) as gtotal FROM history WHERE user_id = ?", (session["user_id"],)).fetchall()
	gtotal = rows[0]["gtotal"]

	rows = db.execute("SELECT * FROM history WHERE user_id = ?", (session["user_id"],)).fetchall()
	return render_template("history.html", rows=rows, gtotal=gtotal)


@app.route("/logout")
def logout():
	"""Log user out"""

	# Forget any user_id
	session.clear()

	# Redirect user to login form
	return redirect("/")