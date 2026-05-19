"""
HabitFlow - Daily Habit Tracker
-------------------------------
Lehman's Law in context:
Lehman's Laws of Software Evolution (specifically the Law of Continuing Change and 
Increasing Complexity) state that a system must be continually adapted or it becomes 
progressively less satisfactory. In HabitFlow, the modular Object-Oriented Programming (OOP) 
structure and separation of concerns (e.g., DatabaseManager, HabitApp) allow for easy future 
adaptations, feature additions, and maintenance without rewriting the entire system.

Deployment Note:
To package this application into a standalone executable for deployment, you can use PyInstaller:
1. pip install pyinstaller
2. pyinstaller --onefile --noconsole habitflow.py
"""

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog
import sqlite3
import hashlib
from datetime import datetime, date, timedelta
import unittest

# --- DATABASE MANAGER ---
# OOP Concept: Encapsulation - We hide the underlying database connection 
# and query details inside the DatabaseManager class.
class DatabaseManager:
    """Handles all SQLite database operations."""
    
    def __init__(self, db_name="habitflow.db"):
        self.db_name = db_name
        self.conn = sqlite3.connect(self.db_name)
        self.init_db()

    def get_connection(self):
        """Returns the active connection to the database."""
        return self.conn

    def init_db(self):
        """Creates the necessary tables if they don't exist."""
        # Exception Handling: Try/Except used to catch database connection/creation errors
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''CREATE TABLE IF NOT EXISTS users (
                                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                                    username TEXT UNIQUE,
                                    password_hash TEXT)''')
                cursor.execute('''CREATE TABLE IF NOT EXISTS habits (
                                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                                    user_id INTEGER,
                                    name TEXT,
                                    category TEXT,
                                    difficulty TEXT,
                                    streak INTEGER DEFAULT 0,
                                    last_completed TEXT)''')
                cursor.execute('''CREATE TABLE IF NOT EXISTS daily_log (
                                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                                    habit_id INTEGER,
                                    user_id INTEGER,
                                    date TEXT,
                                    completed INTEGER)''')
                cursor.execute('''CREATE TABLE IF NOT EXISTS reports (
                                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                                    user_id INTEGER,
                                    week_start TEXT,
                                    completion_percent REAL,
                                    grade TEXT,
                                    feedback TEXT,
                                    saved_on TEXT)''')
                cursor.execute('''CREATE TABLE IF NOT EXISTS categories (
                                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                                    name TEXT UNIQUE)''')
                
                # Insert default categories
                defaults = ["Health", "Study", "Lifestyle", "Fitness", "Other"]
                for c in defaults:
                    try:
                        cursor.execute("INSERT INTO categories (name) VALUES (?)", (c,))
                    except sqlite3.IntegrityError:
                        pass
                conn.commit()
        except sqlite3.Error as e:
            messagebox.showerror("Database Error", f"Error initializing database: {e}")

    def execute_query(self, query, params=()):
        """Executes a query that modifies the database."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, params)
                conn.commit()
                return cursor
        except sqlite3.Error as e:
            messagebox.showerror("Database Error", f"Query error: {e}")
            return None

    def fetch_all(self, query, params=()):
        """Fetches all results from a SELECT query."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, params)
                return cursor.fetchall()
        except sqlite3.Error as e:
            messagebox.showerror("Database Error", f"Fetch error: {e}")
            return []

    def fetch_one(self, query, params=()):
        """Fetches a single result from a SELECT query."""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute(query, params)
                return cursor.fetchone()
        except sqlite3.Error as e:
            messagebox.showerror("Database Error", f"Fetch error: {e}")
            return None

# --- MODELS ---
# OOP Concept: Abstraction - Representing real-world entities (User, Habit) as software objects.
class User:
    """Manages user registration, login, and session state."""
    
    def __init__(self, db_manager):
        self.db = db_manager
        self.current_user_id = None
        self.current_username = None

    def hash_password(self, password):
        """Hashes the password using SHA-256."""
        return hashlib.sha256(password.encode()).hexdigest()

    def register(self, username, password):
        """Registers a new user in the database."""
        if not username or not password:
            raise ValueError("Username and password cannot be empty")
        
        pw_hash = self.hash_password(password)
        try:
            self.db.execute_query("INSERT INTO users (username, password_hash) VALUES (?, ?)", (username, pw_hash))
            return True
        # Exception Handling: Catching duplicate usernames during registration
        except sqlite3.IntegrityError:
            raise ValueError("Username already exists")

    def login(self, username, password):
        """Logs in an existing user."""
        if not username or not password:
            raise ValueError("Username and password cannot be empty")
        
        pw_hash = self.hash_password(password)
        result = self.db.fetch_one("SELECT id, username FROM users WHERE username=? AND password_hash=?", (username, pw_hash))
        if result:
            self.current_user_id = result[0]
            self.current_username = result[1]
            return True
        return False

    def logout(self):
        """Logs out the current user."""
        self.current_user_id = None
        self.current_username = None

class Habit:
    """Represents a single habit entity."""
    
    def __init__(self, id, user_id, name, category, difficulty, streak=0, last_completed=None):
        self.id = id
        self.user_id = user_id
        self.name = name
        self.category = category
        self.difficulty = difficulty
        self.streak = streak
        self.last_completed = last_completed

class StreakManager:
    """Handles logic for calculating and resetting habit streaks."""
    
    @staticmethod
    def check_and_update_streak(habit, db_manager, today_str):
        """Checks if a habit streak should be reset due to missed days."""
        if habit.last_completed:
            # Exception Handling: Catching invalid date formats in the database
            try:
                last_date = datetime.strptime(habit.last_completed, "%Y-%m-%d").date()
                today = datetime.strptime(today_str, "%Y-%m-%d").date()
                delta = (today - last_date).days
                if delta > 1:
                    habit.streak = 0
            except ValueError:
                habit.streak = 0
        else:
            habit.streak = 0
            
        db_manager.execute_query("UPDATE habits SET streak=? WHERE id=?", (habit.streak, habit.id))
        return habit.streak

    @staticmethod
    def increment_streak(habit, db_manager, today_str):
        """Increments the streak if completed today."""
        if habit.last_completed != today_str:
            habit.streak += 1
            habit.last_completed = today_str
            db_manager.execute_query("UPDATE habits SET streak=?, last_completed=? WHERE id=?", (habit.streak, habit.last_completed, habit.id))

class Timer:
    """Manages the midnight reset countdown timer."""
    
    def __init__(self, tk_root, label_widget, reset_callback):
        self.root = tk_root
        self.label = label_widget
        self.reset_callback = reset_callback
        self.update_clock()

    def update_clock(self):
        """Updates the countdown label every second."""
        now = datetime.now()
        tomorrow = datetime(now.year, now.month, now.day) + timedelta(days=1)
        remaining = tomorrow - now
        hours, remainder = divmod(remaining.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        
        time_str = f"Time to Midnight: {hours:02d}:{minutes:02d}:{seconds:02d}"
        
        # Exception Handling: Check if label exists before updating to prevent errors on window close
        if self.label.winfo_exists():
            self.label.config(text=time_str)
            self.root.after(1000, self.update_clock)
        
        if hours == 23 and minutes == 59 and seconds == 59:
            self.root.after(1000, self.reset_callback)

class ReportManager:
    """Calculates weekly stats and generates grades."""
    
    def __init__(self, db_manager, user_id):
        self.db = db_manager
        self.user_id = user_id

    def calculate_weekly_stats(self):
        """Calculates completion percentage and assigns a grade."""
        today = date.today()
        week_start = today - timedelta(days=today.weekday())
        
        habits = self.db.fetch_all("SELECT id FROM habits WHERE user_id=?", (self.user_id,))
        if not habits:
            return 0, "Fail", "No habits added yet."

        total_possible = len(habits) * 7
        
        done_this_week_query = self.db.fetch_one("""SELECT COUNT(*) FROM daily_log 
                                              WHERE user_id=? AND completed=1 
                                              AND date >= ?""", (self.user_id, week_start.strftime("%Y-%m-%d")))
        done_this_week = done_this_week_query[0] if done_this_week_query else 0
        
        percent = (done_this_week / total_possible) * 100 if total_possible > 0 else 0
        
        if percent >= 90:
            grade = "A"
            feedback = "Great job! Keep the streak alive!"
        elif percent >= 75:
            grade = "B"
            feedback = "Good work, but room for improvement."
        elif percent >= 60:
            grade = "C"
            feedback = "You're slipping! Stay consistent."
        else:
            grade = "Fail"
            feedback = "Don't give up! Let's build better habits this week."
            
        return percent, grade, feedback

    def save_report(self, percent, grade, feedback):
        """Saves the generated report history to the database."""
        today = date.today()
        week_start = (today - timedelta(days=today.weekday())).strftime("%Y-%m-%d")
        
        existing = self.db.fetch_one("SELECT id FROM reports WHERE user_id=? AND week_start=? AND saved_on=?", 
                                     (self.user_id, week_start, today.strftime("%Y-%m-%d")))
        if not existing:
            self.db.execute_query("""INSERT INTO reports 
                                     (user_id, week_start, completion_percent, grade, feedback, saved_on) 
                                     VALUES (?, ?, ?, ?, ?, ?)""",
                                  (self.user_id, week_start, percent, grade, feedback, today.strftime("%Y-%m-%d")))

class Admin:
    """Handles admin-level operations like adding and deleting habits."""
    
    def __init__(self, db_manager, user_id):
        self.db = db_manager
        self.user_id = user_id

    def add_habit(self, name, category, difficulty):
        if not name:
            raise ValueError("Habit name cannot be empty")
        self.db.execute_query("INSERT INTO habits (user_id, name, category, difficulty) VALUES (?, ?, ?, ?)", 
                              (self.user_id, name, category, difficulty))

    def edit_habit(self, habit_id, new_name):
        if not new_name:
            raise ValueError("Habit name cannot be empty")
        self.db.execute_query("UPDATE habits SET name=? WHERE id=? AND user_id=?", (new_name, habit_id, self.user_id))

    def delete_habit(self, habit_id):
        self.db.execute_query("DELETE FROM habits WHERE id=? AND user_id=?", (habit_id, self.user_id))
        self.db.execute_query("DELETE FROM daily_log WHERE habit_id=?", (habit_id,))

# --- GUI FRAMEWORK ---
# OOP Concept: Inheritance - Panel inherits from tk.Frame to reuse Tkinter frame functionality.
class Panel(tk.Frame):
    """Base class for all application screens."""
    def __init__(self, parent, app_controller, *args, **kwargs):
        super().__init__(parent, bg="#1a1a2e", *args, **kwargs)
        self.app = app_controller

# OOP Concept: Polymorphism - HabitApp manages different Panel subclasses interchangeably.
class HabitApp(tk.Tk):
    """Main Tkinter application controller."""
    def __init__(self):
        super().__init__()
        self.title("HabitFlow - Daily Habit Tracker")
        self.geometry("800x650")
        self.configure(bg="#1a1a2e")
        
        self.db_manager = DatabaseManager()
        self.user_manager = User(self.db_manager)
        
        # Tkinter ttk styles
        self.style = ttk.Style()
        self.style.theme_use('clam')
        self.style.configure('TButton', background='#e94560', foreground='white', font=('Inter', 11, 'bold'), padding=5, relief=tk.FLAT)
        self.style.map('TButton', background=[('active', '#c81d3d')])
        self.style.configure('TEntry', fieldbackground='#16213e', foreground='white', font=('Inter', 11))
        self.style.configure('TCheckbutton', background='#1a1a2e', foreground='white', font=('Inter', 11))
        self.style.map('TCheckbutton', background=[('active', '#1a1a2e')])
        self.style.configure('Treeview', background='#16213e', foreground='white', fieldbackground='#16213e', borderwidth=0)
        self.style.map('Treeview', background=[('selected', '#e94560')])
        self.style.configure('Treeview.Heading', background='#1a1a2e', foreground='white', font=('Inter', 11, 'bold'))
        self.style.configure('TCombobox', fieldbackground='#16213e', background='#16213e', foreground='white')
        
        self.container = tk.Frame(self, bg="#1a1a2e")
        self.container.pack(fill="both", expand=True)
        
        self.show_frame(LoginScreen)

    def show_frame(self, frame_class, *args):
        """Destroys current view and switches to the provided frame class."""
        # Exception Handling: Safely clearing existing widgets
        try:
            for widget in self.container.winfo_children():
                widget.destroy()
        except Exception as e:
            print(f"Error clearing container: {e}")
            
        frame = frame_class(self.container, self, *args)
        frame.pack(fill="both", expand=True)

class LoginScreen(Panel):
    """Screen for user login."""
    def __init__(self, parent, app):
        super().__init__(parent, app)
        
        tk.Label(self, text="HabitFlow", font=('Inter', 28, 'bold'), bg="#1a1a2e", fg="#e94560").pack(pady=(100, 20))
        
        card = tk.Frame(self, bg="#16213e", padx=40, pady=40)
        card.pack()
        
        tk.Label(card, text="Username", bg="#16213e", fg="white", font=('Inter', 11)).pack(anchor="w")
        self.username_var = tk.StringVar()
        ttk.Entry(card, textvariable=self.username_var, width=30).pack(pady=(0, 15))
        
        tk.Label(card, text="Password", bg="#16213e", fg="white", font=('Inter', 11)).pack(anchor="w")
        self.password_var = tk.StringVar()
        ttk.Entry(card, textvariable=self.password_var, show="*", width=30).pack(pady=(0, 20))
        
        self.error_label = tk.Label(card, text="", bg="#16213e", fg="#e94560", font=('Inter', 10))
        self.error_label.pack()
        
        ttk.Button(card, text="Login", command=self.do_login).pack(fill="x", pady=5)
        ttk.Button(card, text="Register", command=lambda: app.show_frame(RegisterScreen)).pack(fill="x")

    def do_login(self):
        try:
            if self.app.user_manager.login(self.username_var.get(), self.password_var.get()):
                self.app.show_frame(DashboardScreen)
            else:
                self.error_label.config(text="Invalid credentials")
        except ValueError as e:
            self.error_label.config(text=str(e))

class RegisterScreen(Panel):
    """Screen for user registration."""
    def __init__(self, parent, app):
        super().__init__(parent, app)
        
        tk.Label(self, text="Register", font=('Inter', 28, 'bold'), bg="#1a1a2e", fg="#e94560").pack(pady=(80, 20))
        
        card = tk.Frame(self, bg="#16213e", padx=40, pady=40)
        card.pack()
        
        tk.Label(card, text="Username", bg="#16213e", fg="white", font=('Inter', 11)).pack(anchor="w")
        self.username_var = tk.StringVar()
        ttk.Entry(card, textvariable=self.username_var, width=30).pack(pady=(0, 10))
        
        tk.Label(card, text="Password", bg="#16213e", fg="white", font=('Inter', 11)).pack(anchor="w")
        self.password_var = tk.StringVar()
        ttk.Entry(card, textvariable=self.password_var, show="*", width=30).pack(pady=(0, 10))
        
        tk.Label(card, text="Confirm Password", bg="#16213e", fg="white", font=('Inter', 11)).pack(anchor="w")
        self.confirm_var = tk.StringVar()
        ttk.Entry(card, textvariable=self.confirm_var, show="*", width=30).pack(pady=(0, 20))
        
        self.error_label = tk.Label(card, text="", bg="#16213e", fg="#e94560", font=('Inter', 10))
        self.error_label.pack()
        
        ttk.Button(card, text="Register", command=self.do_register).pack(fill="x", pady=5)
        ttk.Button(card, text="Back to Login", command=lambda: app.show_frame(LoginScreen)).pack(fill="x")

    def do_register(self):
        u = self.username_var.get()
        p = self.password_var.get()
        c = self.confirm_var.get()
        
        if p != c:
            self.error_label.config(text="Passwords do not match")
            return
            
        try:
            if self.app.user_manager.register(u, p):
                messagebox.showinfo("Success", "Registration successful. Please login.")
                self.app.show_frame(LoginScreen)
        except ValueError as e:
            self.error_label.config(text=str(e))

class DashboardScreen(Panel):
    """Main dashboard screen displaying habits and progress."""
    def __init__(self, parent, app):
        super().__init__(parent, app)
        self.today_str = date.today().strftime("%Y-%m-%d")
        
        header = tk.Frame(self, bg="#1a1a2e")
        header.pack(fill="x", padx=20, pady=20)
        
        tk.Label(header, text=f"Welcome, {app.user_manager.current_username}!", font=('Inter', 18, 'bold'), bg="#1a1a2e", fg="white").pack(side="left")
        
        self.timer_label = tk.Label(header, font=('Inter', 11), bg="#1a1a2e", fg="#e94560")
        self.timer_label.pack(side="right")
        self.timer = Timer(app, self.timer_label, self.reset_dashboard)
        
        self.content = tk.Frame(self, bg="#1a1a2e")
        self.content.pack(fill="both", expand=True, padx=20)
        
        self.load_habits()
        
        nav = tk.Frame(self, bg="#1a1a2e")
        nav.pack(fill="x", side="bottom", padx=20, pady=20)
        
        ttk.Button(nav, text="Add Habit", command=lambda: app.show_frame(AddHabitScreen)).pack(side="left", padx=5)
        ttk.Button(nav, text="📊 Stats", command=lambda: app.show_frame(StatsScreen)).pack(side="left", padx=5)
        ttk.Button(nav, text="Admin Panel", command=lambda: app.show_frame(AdminPanel)).pack(side="left", padx=5)
        ttk.Button(nav, text="Logout", command=self.logout).pack(side="right", padx=5)

    def reset_dashboard(self):
        self.today_str = date.today().strftime("%Y-%m-%d")
        self.app.show_frame(DashboardScreen)

    def load_habits(self):
        rows = self.app.db_manager.fetch_all("SELECT id, name, category, difficulty, streak, last_completed FROM habits WHERE user_id=?", (self.app.user_manager.current_user_id,))
        
        if not rows:
            tk.Label(self.content, text="No habits added yet. Start by adding one!", font=('Inter', 14), bg="#1a1a2e", fg="gray").pack(pady=50)
            return

        self.habit_vars = {}
        total = len(rows)
        done_count = 0

        for r in rows:
            h = Habit(r[0], self.app.user_manager.current_user_id, r[1], r[2], r[3], r[4], r[5])
            
            StreakManager.check_and_update_streak(h, self.app.db_manager, self.today_str)
            
            card = tk.Frame(self.content, bg="#16213e", padx=15, pady=10)
            card.pack(fill="x", pady=5)
            
            is_done_row = self.app.db_manager.fetch_one("SELECT completed FROM daily_log WHERE habit_id=? AND date=?", (h.id, self.today_str))
            is_done = is_done_row[0] if is_done_row else 0
            var = tk.IntVar(value=is_done)
            if is_done == 1:
                done_count += 1
                
            self.habit_vars[h.id] = (var, h)
            
            checkbox_text = f"✅ {h.name} ({h.difficulty})" if is_done == 1 else f"{h.name} ({h.difficulty})"
            
            cb = tk.Checkbutton(card, text=checkbox_text, variable=var, bg="#16213e", fg="white", font=('Inter', 12), selectcolor="#16213e", activebackground="#16213e", activeforeground="white", command=lambda hid=h.id: self.toggle_habit(hid))
            cb.pack(side="left")
            
            tk.Label(card, text=f"🔥 {h.streak} days", bg="#16213e", fg="#e94560", font=('Inter', 11, 'bold')).pack(side="right")

        # Progress bar
        prog_frame = tk.Frame(self.content, bg="#1a1a2e")
        prog_frame.pack(fill="x", pady=20)
        tk.Label(prog_frame, text="Today's Progress:", bg="#1a1a2e", fg="white", font=('Inter', 11)).pack(anchor="w", pady=(0,5))
        
        style = ttk.Style()
        style.theme_use('clam')
        style.configure("red.Horizontal.TProgressbar", foreground='#e94560', background='#e94560')
        
        prog = ttk.Progressbar(prog_frame, style="red.Horizontal.TProgressbar", length=100, mode='determinate')
        prog.pack(fill="x")
        prog['value'] = (done_count / total) * 100 if total > 0 else 0

    def toggle_habit(self, habit_id):
        var, h = self.habit_vars[habit_id]
        completed = var.get()
        
        existing = self.app.db_manager.fetch_one("SELECT id FROM daily_log WHERE habit_id=? AND date=?", (habit_id, self.today_str))
        if existing:
            self.app.db_manager.execute_query("UPDATE daily_log SET completed=? WHERE id=?", (completed, existing[0]))
        else:
            self.app.db_manager.execute_query("INSERT INTO daily_log (habit_id, user_id, date, completed) VALUES (?, ?, ?, ?)", (habit_id, self.app.user_manager.current_user_id, self.today_str, completed))
            
        if completed == 1:
            StreakManager.increment_streak(h, self.app.db_manager, self.today_str)
        else:
            if h.last_completed == self.today_str:
                h.streak = max(0, h.streak - 1)
                h.last_completed = None
                self.app.db_manager.execute_query("UPDATE habits SET streak=?, last_completed=NULL WHERE id=?", (h.streak, h.id))
        
        self.app.show_frame(DashboardScreen)

    def logout(self):
        self.app.user_manager.logout()
        self.app.show_frame(LoginScreen)

class AddHabitScreen(Panel):
    """Screen to add a new habit."""
    def __init__(self, parent, app):
        super().__init__(parent, app)
        
        tk.Label(self, text="Add New Habit", font=('Inter', 24, 'bold'), bg="#1a1a2e", fg="#e94560").pack(pady=30)
        
        card = tk.Frame(self, bg="#16213e", padx=40, pady=40)
        card.pack()
        
        tk.Label(card, text="Habit Name", bg="#16213e", fg="white", font=('Inter', 11)).pack(anchor="w")
        self.name_var = tk.StringVar()
        ttk.Entry(card, textvariable=self.name_var, width=30).pack(pady=(0, 15))
        
        tk.Label(card, text="Category", bg="#16213e", fg="white", font=('Inter', 11)).pack(anchor="w")
        
        cats = [row[0] for row in app.db_manager.fetch_all("SELECT name FROM categories")]
        if not cats: cats = ["Other"]
        
        self.cat_var = tk.StringVar(value=cats[0])
        ttk.Combobox(card, textvariable=self.cat_var, values=cats, state="readonly", width=28).pack(pady=(0, 15))
        
        tk.Label(card, text="Difficulty", bg="#16213e", fg="white", font=('Inter', 11)).pack(anchor="w")
        self.diff_var = tk.StringVar(value="Medium")
        ttk.Combobox(card, textvariable=self.diff_var, values=["Easy", "Medium", "Hard"], state="readonly", width=28).pack(pady=(0, 20))
        
        self.error_label = tk.Label(card, text="", bg="#16213e", fg="#e94560", font=('Inter', 10))
        self.error_label.pack()
        
        btn_frame = tk.Frame(card, bg="#16213e")
        btn_frame.pack(fill="x")
        ttk.Button(btn_frame, text="Save", command=self.save_habit).pack(side="left", expand=True, fill="x", padx=(0, 5))
        ttk.Button(btn_frame, text="Cancel", command=lambda: app.show_frame(DashboardScreen)).pack(side="right", expand=True, fill="x", padx=(5, 0))

    def save_habit(self):
        try:
            admin = Admin(self.app.db_manager, self.app.user_manager.current_user_id)
            admin.add_habit(self.name_var.get(), self.cat_var.get(), self.diff_var.get())
            self.app.show_frame(DashboardScreen)
        except ValueError as e:
            self.error_label.config(text=str(e))

class StatsScreen(Panel):
    """Screen displaying weekly statistics."""
    def __init__(self, parent, app):
        super().__init__(parent, app)
        
        tk.Label(self, text="Weekly Report", font=('Inter', 24, 'bold'), bg="#1a1a2e", fg="#e94560").pack(pady=20)
        
        rm = ReportManager(app.db_manager, app.user_manager.current_user_id)
        percent, grade, feedback = rm.calculate_weekly_stats()
        rm.save_report(percent, grade, feedback)
        
        card = tk.Frame(self, bg="#16213e", padx=30, pady=30)
        card.pack(fill="x", padx=40)
        
        tk.Label(card, text=f"Completion: {percent:.1f}%", font=('Inter', 14), bg="#16213e", fg="white").pack()
        tk.Label(card, text=f"Grade: {grade}", font=('Inter', 20, 'bold'), bg="#16213e", fg="#e94560").pack(pady=10)
        tk.Label(card, text=feedback, font=('Inter', 12, 'italic'), bg="#16213e", fg="lightgray").pack()
        
        canvas_frame = tk.Frame(self, bg="#1a1a2e")
        canvas_frame.pack(pady=20)
        tk.Label(canvas_frame, text="Habits Completed Last 7 Days", bg="#1a1a2e", fg="white", font=('Inter', 12)).pack()
        
        c = tk.Canvas(canvas_frame, width=400, height=150, bg="#16213e", highlightthickness=0)
        c.pack(pady=10)
        
        today = date.today()
        for i in range(7):
            d = (today - timedelta(days=6-i)).strftime("%Y-%m-%d")
            count_res = app.db_manager.fetch_one("SELECT COUNT(*) FROM daily_log WHERE user_id=? AND date=? AND completed=1", (app.user_manager.current_user_id, d))
            count = count_res[0] if count_res else 0
            
            x0 = 10 + i * 55
            y0 = max(20, 140 - (count * 20)) # scale factor
            x1 = x0 + 40
            y1 = 140
            
            c.create_rectangle(x0, y0, x1, y1, fill="#e94560")
            c.create_text(x0+20, 145, text=(today - timedelta(days=6-i)).strftime("%a"), fill="white", font=('Inter', 8))

        ttk.Button(self, text="Back to Dashboard", command=lambda: app.show_frame(DashboardScreen)).pack(pady=10)

class AdminPanel(Panel):
    """Admin screen to manage habits and categories."""
    def __init__(self, parent, app):
        super().__init__(parent, app)
        
        tk.Label(self, text="Admin Panel", font=('Inter', 24, 'bold'), bg="#1a1a2e", fg="#e94560").pack(pady=20)
        
        columns = ("id", "name", "category", "difficulty", "streak")
        self.tree = ttk.Treeview(self, columns=columns, show="headings", height=10)
        self.tree.heading("id", text="ID")
        self.tree.heading("name", text="Habit Name")
        self.tree.heading("category", text="Category")
        self.tree.heading("difficulty", text="Difficulty")
        self.tree.heading("streak", text="Streak")
        
        self.tree.column("id", width=50)
        self.tree.column("name", width=200)
        self.tree.column("category", width=150)
        self.tree.column("difficulty", width=100)
        self.tree.column("streak", width=100)
        
        self.tree.pack(pady=10, padx=20, fill="x")
        
        self.load_data()
        
        btn_frame = tk.Frame(self, bg="#1a1a2e")
        btn_frame.pack(pady=10)
        
        ttk.Button(btn_frame, text="Edit Selected", command=self.edit_selected).pack(side="left", padx=10)
        ttk.Button(btn_frame, text="Delete Selected", command=self.delete_selected).pack(side="left", padx=10)
        ttk.Button(btn_frame, text="Add Category", command=self.add_category).pack(side="left", padx=10)
        
        ttk.Button(self, text="Back to Dashboard", command=lambda: app.show_frame(DashboardScreen)).pack(pady=10)

    def load_data(self):
        for item in self.tree.get_children():
            self.tree.delete(item)
            
        rows = self.app.db_manager.fetch_all("SELECT id, name, category, difficulty, streak FROM habits WHERE user_id=?", (self.app.user_manager.current_user_id,))
        for r in rows:
            self.tree.insert("", "end", values=r)

    def edit_selected(self):
        selected = self.tree.selection()
        if not selected:
            return
        item = self.tree.item(selected[0])
        habit_id = item['values'][0]
        
        new_name = simpledialog.askstring("Edit Habit", "Enter new habit name:", initialvalue=item['values'][1])
        if new_name is not None:
            try:
                admin = Admin(self.app.db_manager, self.app.user_manager.current_user_id)
                admin.edit_habit(habit_id, new_name)
                self.load_data()
            except ValueError as e:
                messagebox.showerror("Error", str(e))

    def delete_selected(self):
        selected = self.tree.selection()
        if not selected:
            return
            
        item = self.tree.item(selected[0])
        habit_id = item['values'][0]
        
        admin = Admin(self.app.db_manager, self.app.user_manager.current_user_id)
        admin.delete_habit(habit_id)
        self.load_data()

    def add_category(self):
        new_cat = simpledialog.askstring("Add Category", "Enter new category name:")
        if new_cat:
            try:
                self.app.db_manager.execute_query("INSERT INTO categories (name) VALUES (?)", (new_cat,))
                messagebox.showinfo("Success", f"Category '{new_cat}' added.")
            except sqlite3.IntegrityError:
                messagebox.showerror("Error", "Category already exists.")

# --- UNIT TESTS ---
class TestHabitFlow(unittest.TestCase):
    def setUp(self):
        # Use in-memory database for isolated tests
        self.db = DatabaseManager(":memory:")
        self.user = User(self.db)
        # Suppress messageboxes during tests
        # The db manager initializes tables safely
        try:
            self.user.register("testuser", "password123")
        except ValueError:
            pass # ignore if already exists in some weird edge case
        self.user.login("testuser", "password123")

    def test_login_valid_user(self):
        self.assertTrue(self.user.login("testuser", "password123"))

    def test_login_invalid_password(self):
        self.assertFalse(self.user.login("testuser", "wrongpass"))

    def test_empty_habit_name_validation(self):
        admin = Admin(self.db, self.user.current_user_id)
        with self.assertRaises(ValueError):
            admin.add_habit("", "Health", "Easy")

    def test_streak_increment(self):
        admin = Admin(self.db, self.user.current_user_id)
        admin.add_habit("Read", "Study", "Easy")
        
        h_row = self.db.fetch_one("SELECT id, name, category, difficulty, streak, last_completed FROM habits")
        habit = Habit(h_row[0], self.user.current_user_id, h_row[1], h_row[2], h_row[3], h_row[4], h_row[5])
        
        today_str = "2026-05-19"
        StreakManager.increment_streak(habit, self.db, today_str)
        
        self.assertEqual(habit.streak, 1)
        self.assertEqual(habit.last_completed, today_str)

    def test_streak_reset_on_missed_day(self):
        self.db.execute_query("INSERT INTO habits (user_id, name, category, difficulty, streak, last_completed) VALUES (?, ?, ?, ?, ?, ?)",
                              (self.user.current_user_id, "Run", "Fitness", "Hard", 5, "2026-05-17"))
        
        h_row = self.db.fetch_one("SELECT id, name, category, difficulty, streak, last_completed FROM habits WHERE name='Run'")
        habit = Habit(h_row[0], self.user.current_user_id, h_row[1], h_row[2], h_row[3], h_row[4], h_row[5])
        
        today_str = "2026-05-19"
        streak = StreakManager.check_and_update_streak(habit, self.db, today_str)
        
        self.assertEqual(streak, 0)

    def test_grade_calculation(self):
        rm = ReportManager(self.db, self.user.current_user_id)
        
        admin = Admin(self.db, self.user.current_user_id)
        admin.add_habit("Code", "Study", "Hard")
        h_row = self.db.fetch_one("SELECT id FROM habits")
        habit_id = h_row[0]
        
        today = date.today()
        week_start = today - timedelta(days=today.weekday())
        
        for i in range(7):
            d = (week_start + timedelta(days=i)).strftime("%Y-%m-%d")
            self.db.execute_query("INSERT INTO daily_log (habit_id, user_id, date, completed) VALUES (?, ?, ?, ?)",
                                  (habit_id, self.user.current_user_id, d, 1))
            
        percent, grade, feedback = rm.calculate_weekly_stats()
        self.assertEqual(percent, 100.0)
        self.assertEqual(grade, "A")


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        sys.argv.pop(1) # Remove 'test' argument so unittest doesn't complain
        unittest.main()
    else:
        app = HabitApp()
        app.mainloop()
