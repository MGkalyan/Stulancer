from flask import Flask, render_template, request, redirect, url_for, session
import sqlite3

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# -------------------------------
# Database Connection
# -------------------------------
def get_db_connection():
    conn = sqlite3.connect('database.db')
    conn.row_factory = sqlite3.Row
    return conn

# -------------------------------
# Initialize Database
# -------------------------------
def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Users Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        email TEXT,
        password TEXT
    )
    ''')

    # Tasks Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        title TEXT,
        description TEXT,
        deadline TEXT,
        budget TEXT,
        user_id TEXT
    )
    ''')

    # Applications Table
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS applications (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        task_id INTEGER,
        user_name TEXT
    )
    ''')

    # Messages Table (PRIVATE CHAT)
    cursor.execute('''
    CREATE TABLE IF NOT EXISTS messages (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        task_id INTEGER,
        sender TEXT,
        receiver TEXT,
        message TEXT
    )
    ''')

    conn.commit()
    conn.close()

# -------------------------------
# Routes
# -------------------------------

# Home
@app.route('/')
def home():
    return render_template('home.html')

# Register
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']

        conn = get_db_connection()
        conn.execute(
            'INSERT INTO users (username, email, password) VALUES (?, ?, ?)',
            (username, email, password)
        )
        conn.commit()
        conn.close()

        return redirect(url_for('login'))

    return render_template('register.html')

# Login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        conn = get_db_connection()
        user = conn.execute(
            'SELECT * FROM users WHERE username = ? AND password = ?',
            (username, password)
        ).fetchone()
        conn.close()

        if user:
            session['user'] = user['username']
            return redirect(url_for('home'))
        else:
            return "Invalid Credentials ❌"

    return render_template('login.html')
@app.route('/my_applications')
def my_applications():
    if 'user' not in session:
        return redirect(url_for('login'))

    user_name = session['user']
    conn = get_db_connection()

    # Get applications of this user
    applications = conn.execute(
        'SELECT * FROM applications WHERE user_name = ?',
        (user_name,)
    ).fetchall()

    # Get all tasks
    tasks = conn.execute('SELECT * FROM tasks').fetchall()

    conn.close()

    return render_template('my_applications.html', applications=applications, tasks=tasks)
# Logout
@app.route('/logout')
def logout():
    session.pop('user', None)
    return redirect(url_for('home'))

# Post Task
@app.route('/post_task', methods=['GET', 'POST'])
def post_task():
    if 'user' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        title = request.form['title']
        description = request.form['description']
        deadline = request.form['deadline']
        budget = request.form['budget']

        user_name = session['user']

        conn = get_db_connection()
        conn.execute(
            'INSERT INTO tasks (title, description, deadline, budget, user_id) VALUES (?, ?, ?, ?, ?)',
            (title, description, deadline, budget, user_name)
        )
        conn.commit()
        conn.close()

        return redirect(url_for('dashboard'))

    return render_template('post_task.html')

# View Tasks
@app.route('/tasks')
def view_tasks():
    conn = get_db_connection()
    tasks = conn.execute('SELECT * FROM tasks').fetchall()
    conn.close()

    return render_template('tasks.html', tasks=tasks)

@app.route('/apply/<int:task_id>')
def apply_task(task_id):
    if 'user' not in session:
        return redirect(url_for('login'))

    user_name = session['user']
    conn = get_db_connection()

    # 🔥 Check if already applied
    existing = conn.execute(
        'SELECT * FROM applications WHERE task_id = ? AND user_name = ?',
        (task_id, user_name)
    ).fetchone()

    if existing:
        conn.close()
        return "You already applied for this task ❌"

    # Insert new application
    conn.execute(
        'INSERT INTO applications (task_id, user_name) VALUES (?, ?)',
        (task_id, user_name)
    )
    conn.commit()
    conn.close()

    return "Applied Successfully ✅"
# Dashboard
@app.route('/delete_task/<int:task_id>')
def delete_task(task_id):
    if 'user' not in session:
        return redirect(url_for('login'))

    user_name = session['user']
    conn = get_db_connection()

    # 🔥 Check ownership
    task = conn.execute(
        'SELECT * FROM tasks WHERE id = ? AND user_id = ?',
        (task_id, user_name)
    ).fetchone()

    if task:
        conn.execute('DELETE FROM tasks WHERE id = ?', (task_id,))
        conn.commit()

    conn.close()

    return redirect(url_for('dashboard'))
@app.route('/dashboard')
def dashboard():
    if 'user' not in session:
        return redirect(url_for('login'))

    user_name = session['user']
    conn = get_db_connection()

    tasks = conn.execute(
        'SELECT * FROM tasks WHERE user_id = ?',
        (user_name,)
    ).fetchall()

    applications = conn.execute('SELECT * FROM applications').fetchall()

    conn.close()

    return render_template('dashboard.html', tasks=tasks, applications=applications)

# PRIVATE CHAT (FIXED)
@app.route('/chat/<int:task_id>/<username>', methods=['GET', 'POST'])
def private_chat(task_id, username):
    if 'user' not in session:
        return redirect(url_for('login'))

    current_user = session['user']
    conn = get_db_connection()

    if request.method == 'POST':
        message = request.form['message']

        conn.execute(
            'INSERT INTO messages (task_id, sender, receiver, message) VALUES (?, ?, ?, ?)',
            (task_id, current_user, username, message)
        )
        conn.commit()

    # ✅ FIXED QUERY (two-way chat)
    messages = conn.execute(
        '''SELECT * FROM messages 
           WHERE task_id = ? AND 
           ((sender = ? AND receiver = ?) OR 
            (sender = ? AND receiver = ?))''',
        (task_id, current_user, username, username, current_user)
    ).fetchall()

    conn.close()

    return render_template('private_chat.html', messages=messages, username=username)

# -------------------------------
# Run App
# -------------------------------
if __name__ == '__main__':
    init_db()
    app.run(debug=True)