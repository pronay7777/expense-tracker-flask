import sqlite3, os
from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    flash
)

app = Flask(__name__)
app.secret_key = os.environ.get(
    "SECRET KEY", 
    "development-secret-key"
)

DATABASE = "expense_tracker.db"


def get_db_connection():
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    return connection


def init_db():
    connection = get_db_connection()

    connection.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            amount REAL NOT NULL,
            transaction_type TEXT NOT NULL,
            category TEXT NOT NULL,
            date TEXT NOT NULL
        )
    """)

    connection.commit()
    connection.close()

@app.template_filter("format_date")
def format_date(date_value):
    year, month, day = date_value.split("-")
    return f"{day}-{month}-{year}"

@app.route("/")
def home():
    search = request.args.get("search", "").strip()
    transaction_type = request.args.get("type", "")
    category = request.args.get("category", "")
    sort = request.args.get("sort", "newest")

    connection = get_db_connection()

    query = "SELECT * FROM transactions WHERE 1=1"
    parameters = []

    if search:
        query += " AND title LIKE ?"
        parameters.append(f"%{search}%")

    if transaction_type in ["Income", "Expense"]:
        query += " AND transaction_type = ?"
        parameters.append(transaction_type)

    valid_categories = [
        "Food",
        "Transport",
        "Shopping",
        "Bills",
        "Entertainment",
        "Other"
    ]

    if category in valid_categories:
        query += " AND category = ?"
        parameters.append(category)

    # Use a whitelist instead of inserting arbitrary user input into SQL.
    sort_options = {
        "newest": "date DESC, id DESC",
        "oldest": "date ASC, id ASC",
        "highest": "amount DESC, id DESC",
        "lowest": "amount ASC, id ASC"
    }

    order_by = sort_options.get(sort, sort_options["newest"])

    query += f" ORDER BY {order_by}"

    transactions = connection.execute(
        query,
        parameters
    ).fetchall()

    total_income = connection.execute("""
        SELECT COALESCE(SUM(amount), 0)
        FROM transactions
        WHERE transaction_type = 'Income'
    """).fetchone()[0]

    total_expenses = connection.execute("""
        SELECT COALESCE(SUM(amount), 0)
        FROM transactions
        WHERE transaction_type = 'Expense'
    """).fetchone()[0]

    connection.close()

    total_balance = total_income - total_expenses

    filters_active = bool(
        search or transaction_type or category
    )

    return render_template(
        "index.html",
        transactions=transactions,
        total_income=total_income,
        total_expenses=total_expenses,
        total_balance=total_balance,
        search=search,
        selected_type=transaction_type,
        selected_category=category,
        selected_sort=sort,
        filters_active=filters_active
    )


@app.route("/add", methods=["POST"])
def add_transaction():
    title = request.form.get("title", "").strip()
    amount = request.form.get("amount", "").strip()
    transaction_type = request.form.get("transaction_type", "")
    category = request.form.get("category", "")
    date = request.form.get("date", "")

    if not title or not amount or not transaction_type or not category or not date:
        flash("All fields are required.", "error")
        return redirect(url_for("home"))

    try:
        amount = float(amount)

        if amount <= 0:
            raise ValueError

    except ValueError:
        flash("Amount must be a number greater than zero.", "error")
        return redirect(url_for("home"))

    if transaction_type not in ["Income", "Expense"]:
        flash("Please select a valid transaction type.", "error")
        return redirect(url_for("home"))

    valid_categories = [
        "Food",
        "Transport",
        "Shopping",
        "Bills",
        "Entertainment",
        "Other"
    ]

    if category not in valid_categories:
        flash("Please select a valid category.", "error")
        return redirect(url_for("home"))

    connection = get_db_connection()

    connection.execute(
        """
        INSERT INTO transactions
        (title, amount, transaction_type, category, date)
        VALUES (?, ?, ?, ?, ?)
        """,
        (title, amount, transaction_type, category, date)
    )

    connection.commit()
    connection.close()

    flash("Transaction added successfully.", "success")

    return redirect(url_for("home"))

@app.route("/edit/<int:transaction_id>", methods=["GET", "POST"])
def edit_transaction(transaction_id):
    connection = get_db_connection()

    transaction = connection.execute(
        "SELECT * FROM transactions WHERE id = ?",
        (transaction_id,)
    ).fetchone()

    if transaction is None:
        connection.close()
        return redirect(url_for("home"))

    if request.method == "POST":
        title = request.form["title"]
        amount = request.form["amount"]
        transaction_type = request.form["transaction_type"]
        category = request.form["category"]
        date = request.form["date"]

        connection.execute(
            """
            UPDATE transactions
            SET title = ?,
                amount = ?,
                transaction_type = ?,
                category = ?,
                date = ?
            WHERE id = ?
            """,
            (
                title,
                amount,
                transaction_type,
                category,
                date,
                transaction_id
            )
        )

        connection.commit()
        connection.close()
        
        # Succcess  message
        flash("Transaction updated successfully.", "success")

        return redirect(url_for("home"))

    connection.close()

    return render_template(
        "edit.html",
        transaction=transaction
    )


@app.route("/delete/<int:transaction_id>", methods=["POST"])
def delete_transaction(transaction_id):
    connection = get_db_connection()

    connection.execute(
        "DELETE FROM transactions WHERE id = ?",
        (transaction_id,)
    )

    connection.commit()
    connection.close()
    
    # Success message
    flash("Transaction deleted successfully.", "success")

    return redirect(url_for("home"))

# Initialize the database when the application starts.
init_db()

if __name__ == "__main__":
    app.run(debug=True)