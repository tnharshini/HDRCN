from flask import Flask, render_template, request, jsonify, redirect, url_for, session
import sqlite3
import bcrypt
from app2 import app2  # Import Blueprint from app2.py
from app3 import app3  # Import Blueprint from app3.py

app = Flask(__name__)
app.secret_key = "your_secret_key"

app.register_blueprint(app2)
app.register_blueprint(app3)

# Database setup
def init_db():
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT,
            email TEXT UNIQUE,
            dob TEXT,
            phno TEXT,
            address TEXT,
            password TEXT
        )
    ''')

    # Create uploaded_files table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS uploaded_files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            file_name TEXT NOT NULL,
            image_data BLOB,  -- Stores image in binary format
            recognized_text TEXT,  -- Stores extracted text  
            edited_text TEXT, -- Stores user-modified text
            translated_text TEXT,  -- Stores translations
            translated_edited_text TEXT,  -- Stores user-modified translated text
            upload_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users(id)
            UNIQUE(user_id, file_name)  -- Ensures a user can't have duplicate file names
        )
    ''')
    
    conn.commit()
    conn.close()

init_db()  # Initialize the database

# Route to serve login page
@app.route("/")
def login():
    return render_template("login.html")

# Handle login authentication
@app.route("/login", methods=["POST"])
def login_user():
    data = request.json
    email = data.get("email")
    password = data.get("password")

    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, name, password FROM users WHERE email = ?", (email,))
    user = cursor.fetchone()
    conn.close()

    if user and bcrypt.checkpw(password.encode("utf-8"), user[2]):
        session["user_id"] = user[0]
        session["name"] = user[1]
        session["email"] = email
        return jsonify({"success": True, "message": "Login successful!"})
    
    return jsonify({"success": False, "message": "Invalid credentials!"})

# Route to serve registration page
@app.route("/register")
def register():
    return render_template("register.html")

# Handle registration form submission
@app.route("/register", methods=["POST"])
def register_user():
    data = request.json
    name = data.get("name")
    email = data.get("email")
    dob = data.get("dob")
    phno = data.get("phno")
    address = data.get("address")
    password = data.get("password")

    # Validate email and phone number
    if not email or "@" not in email:
        return jsonify({"success": False, "message": "Invalid email address!"})

    if not phno.isdigit() or len(phno) != 10:
        return jsonify({"success": False, "message": "Invalid phone number! Must be 10 digits."})

    # Hash the password
    hashed_password = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())

    try:
        conn = sqlite3.connect("users.db")
        cursor = conn.cursor()
        cursor.execute("INSERT INTO users (name, email, dob, phno, address, password) VALUES (?, ?, ?, ?, ?, ?)", 
                       (name, email, dob, phno, address, hashed_password))
        conn.commit()
        conn.close()
        return jsonify({"success": True, "message": "Registration successful!"})
    except sqlite3.IntegrityError:
        return jsonify({"success": False, "message": "Email already registered!"})

# Profile Route - Show only logged-in user's details
@app.route("/profile")
def profile():
    if "user_id" not in session:
        return redirect(url_for("login"))
    
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute("SELECT name, email, dob, phno, address FROM users WHERE id = ?", (session["user_id"],))
    user = cursor.fetchone()
    conn.close()
    
    return render_template("profile.html", user=user)

@app.route("/update_profile", methods=["POST"])
def update_profile():
    if "user_id" not in session:
        return jsonify({"success": False, "message": "Not logged in!"})
    
    data = request.json
    name = data.get("name")
    dob = data.get("dob")
    phno = data.get("phno")
    address = data.get("address")

    if not phno.isdigit() or len(phno) != 10:
        return jsonify({"success": False, "message": "Invalid phone number! Must be 10 digits."})

    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET name = ?, dob = ?, phno = ?, address = ? WHERE id = ?",
                   (name, dob, phno, address, session["user_id"]))
    conn.commit()
    conn.close()

    return jsonify({"success": True, "message": "Profile updated successfully!"})

# Logout Route
@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

if __name__ == "__main__":
    app.run(debug=True)
