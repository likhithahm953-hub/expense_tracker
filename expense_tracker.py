import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
from tkcalendar import Calendar, DateEntry
import sqlite3
import matplotlib.pyplot as plt
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas as pdf_canvas
import datetime
import os

# ---------- DB Setup ----------
conn = sqlite3.connect('expense_db.sqlite')
c = conn.cursor()

c.execute('''CREATE TABLE IF NOT EXISTS users (
    username TEXT PRIMARY KEY,
    password TEXT)''')

c.execute('''CREATE TABLE IF NOT EXISTS expenses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT,
    date TEXT,
    category TEXT,
    amount REAL,
    description TEXT)''')

c.execute('''CREATE TABLE IF NOT EXISTS budgets (
    username TEXT PRIMARY KEY,
    amount REAL)''')

conn.commit()

# ---------- Main Application ----------
class ExpenseTracker:
    def __init__(self, root, username):
        self.root = root
        self.username = username
        self.currency = tk.StringVar(value="₹")
        self.setup_ui()
        self.view_expenses()

    def setup_ui(self):
        self.root.title(f"Expense Tracker - {self.username}")
        self.root.configure(bg='#2e2e2e')

        form_frame = tk.Frame(self.root, bg='#2e2e2e')
        form_frame.pack(pady=10)

        labels = ["Date", "Category", "Amount", "Description", "Currency"]
        self.entries = []

        self.date_entry = DateEntry(form_frame, date_pattern='yyyy-mm-dd', background='darkblue', foreground='white')
        self.cat_entry = tk.Entry(form_frame)
        self.amount_entry = tk.Entry(form_frame)
        self.desc_entry = tk.Entry(form_frame)
        self.currency_combo = ttk.Combobox(form_frame, textvariable=self.currency, values=["₹", "$", "€", "£"], width=5)
        self.currency_combo.current(0)

        self.entries = [self.date_entry, self.cat_entry, self.amount_entry, self.desc_entry, self.currency_combo]

        for i, (label_text, entry) in enumerate(zip(labels, self.entries)):
            tk.Label(form_frame, text=label_text, fg='white', bg='#2e2e2e').grid(row=0, column=i, padx=5)
            entry.grid(row=1, column=i, padx=5)

        btn_frame = tk.Frame(self.root, bg='#2e2e2e')
        btn_frame.pack(pady=10)

        ttk.Button(btn_frame, text="Add Expense", command=self.add_expense).grid(row=0, column=0, padx=5)
        ttk.Button(btn_frame, text="Delete Selected", command=self.delete_selected).grid(row=0, column=1, padx=5)
        ttk.Button(btn_frame, text="Summary", command=self.show_summary).grid(row=0, column=2, padx=5)
        ttk.Button(btn_frame, text="Pie Chart", command=self.show_pie_chart).grid(row=0, column=3, padx=5)
        ttk.Button(btn_frame, text="Calendar View", command=self.show_calendar).grid(row=0, column=4, padx=5)
        ttk.Button(btn_frame, text="PDF Report", command=self.generate_pdf).grid(row=0, column=5, padx=5)
        ttk.Button(btn_frame, text="Set Budget", command=self.set_budget).grid(row=0, column=6, padx=5)
        ttk.Button(btn_frame, text="Logout", command=self.logout).grid(row=0, column=7, padx=5)

        self.tree = ttk.Treeview(self.root, columns=("Date", "Category", "Amount", "Description"), show='headings')
        for col in self.tree['columns']:
            self.tree.heading(col, text=col)
        self.tree.pack(pady=10)

    def add_expense(self):
        date = self.date_entry.get()
        category = self.cat_entry.get()
        amount = float(self.amount_entry.get())
        description = self.desc_entry.get()
        c.execute("INSERT INTO expenses (username, date, category, amount, description) VALUES (?, ?, ?, ?, ?)",
                  (self.username, date, category, amount, description))
        conn.commit()
        self.view_expenses()
        self.check_budget()

    def view_expenses(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
        c.execute("SELECT date, category, amount, description FROM expenses WHERE username=? ORDER BY date DESC",
                  (self.username,))
        for row in c.fetchall():
            self.tree.insert('', 'end', values=row)

    def delete_selected(self):
        selected = self.tree.selection()
        if not selected:
            return
        values = self.tree.item(selected[0])['values']
        c.execute("DELETE FROM expenses WHERE username=? AND date=? AND category=? AND amount=? AND description=?",
                  (self.username, *values))
        conn.commit()
        self.view_expenses()

    def show_summary(self):
        c.execute("SELECT category, SUM(amount) FROM expenses WHERE username=? GROUP BY category", (self.username,))
        data = c.fetchall()
        summary = "\n".join(f"{cat}: {self.currency.get()}{amt:.2f}" for cat, amt in data)
        messagebox.showinfo("Summary", summary)

    def show_pie_chart(self):
        c.execute("SELECT category, SUM(amount) FROM expenses WHERE username=? GROUP BY category", (self.username,))
        data = c.fetchall()
        if not data:
            return messagebox.showinfo("Info", "No data to display")
        labels, sizes = zip(*data)
        plt.pie(sizes, labels=labels, autopct='%1.1f%%')
        plt.title("Spending Distribution")
        plt.show()

    def show_calendar(self):
        win = tk.Toplevel(self.root)
        cal = Calendar(win, selectmode='day', date_pattern='yyyy-mm-dd')  # FIXED format
        cal.pack()

        def show_exp():
            date = cal.get_date()  # Already yyyy-mm-dd
            c.execute("SELECT category, amount, description FROM expenses WHERE username=? AND date=?",
                      (self.username, date))
            rows = c.fetchall()
            if rows:
                msg = "\n".join(f"{cat}: {amt} - {desc}" for cat, amt, desc in rows)
            else:
                msg = "No expenses found for this date."
            messagebox.showinfo("Expenses", msg)

        ttk.Button(win, text="View", command=show_exp).pack()

    def generate_pdf(self):
        filename = f"{self.username}_report.pdf"
        pdf = pdf_canvas.Canvas(filename, pagesize=letter)
        pdf.drawString(100, 750, f"Expense Report for {self.username}")
        y = 720
        c.execute("SELECT date, category, amount, description FROM expenses WHERE username=?", (self.username,))
        for row in c.fetchall():
            pdf.drawString(50, y, f"{row[0]} | {row[1]} | {row[2]:.2f} | {row[3]}")
            y -= 20
        pdf.save()
        messagebox.showinfo("Exported", f"PDF saved as {filename}")

    def set_budget(self):
        amt = simpledialog.askfloat("Budget", "Enter monthly budget:")
        if amt:
            c.execute("REPLACE INTO budgets (username, amount) VALUES (?, ?)", (self.username, amt))
            conn.commit()
            messagebox.showinfo("Budget", "Budget set successfully")

    def check_budget(self):
        c.execute("SELECT amount FROM budgets WHERE username=?", (self.username,))
        result = c.fetchone()
        if not result:
            return
        budget = result[0]
        month = datetime.date.today().isoformat()[:7]
        c.execute("SELECT SUM(amount) FROM expenses WHERE username=? AND substr(date,1,7)=?",
                  (self.username, month))
        total = c.fetchone()[0] or 0
        if total > budget:
            messagebox.showwarning("Budget Alert",
                                   f"You've exceeded your monthly budget of {self.currency.get()}{budget:.2f}")

    def logout(self):
        self.root.destroy()
        login_screen()

# ---------- Login UI ----------
def login_screen():
    win = tk.Tk()
    win.title("Login")
    win.configure(bg='#2e2e2e')
    win.geometry("350x220+500+250")

    tk.Label(win, text="Username", bg='#2e2e2e', fg='white').pack(pady=5)
    username_entry = tk.Entry(win)
    username_entry.pack()

    tk.Label(win, text="Password", bg='#2e2e2e', fg='white').pack(pady=5)
    password_entry = tk.Entry(win, show='*')
    password_entry.pack()

    def toggle():
        if password_entry.cget('show') == '*':
            password_entry.config(show='')
        else:
            password_entry.config(show='*')

    ttk.Checkbutton(win, text="Show Password", command=toggle).pack()

    def login():
        username = username_entry.get()
        password = password_entry.get()
        c.execute("SELECT * FROM users WHERE username=? AND password=?", (username, password))
        if c.fetchone():
            win.destroy()
            root = tk.Tk()
            ExpenseTracker(root, username)
            root.mainloop()
        else:
            messagebox.showerror("Error", "Invalid Credentials")

    def register():
        username = username_entry.get()
        password = password_entry.get()
        try:
            c.execute("INSERT INTO users VALUES (?, ?)", (username, password))
            conn.commit()
            messagebox.showinfo("Success", "Registered successfully")
        except sqlite3.IntegrityError:
            messagebox.showerror("Error", "Username already exists")

    ttk.Button(win, text="Login", command=login).pack(pady=5)
    ttk.Button(win, text="Register", command=register).pack(pady=5)
    win.mainloop()


if __name__ == "__main__":
    login_screen()
