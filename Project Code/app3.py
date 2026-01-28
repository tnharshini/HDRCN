import pytesseract
import base64
from flask import flash
from datetime import datetime
from flask import Blueprint, render_template, request, redirect, url_for, session, send_file
from deep_translator import GoogleTranslator
import cv2
import numpy as np
import io
from model import recognize_text  # Importing function from model.py
from database import get_db  # Import database connection

app3 = Blueprint("app3", __name__)

# Set Tesseract OCR Path
pytesseract.pytesseract.tesseract_cmd = r"C:\\Program Files\\Tesseract-OCR\\tesseract.exe"

def translate_text(text, target_language):
    """Translate text using Deep Translator"""
    try:
        translator = GoogleTranslator(source="auto", target=target_language)
        return translator.translate(text)
    except Exception as e:
        return f"Translation Error: {str(e)}"

@app3.route("/index", methods=["GET"])
def index():
    return render_template("index.html")

@app3.route("/upload", methods=["POST"])
def upload():
    if "file" not in request.files:
        return redirect(url_for("app3.index"))
    
    file = request.files["file"]
    if file.filename == "":
        return redirect(url_for("app3.index"))

    # Read file into memory
    file_bytes = np.frombuffer(file.read(), np.uint8)
    image = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)

    # Recognize text from image
    recognized_text = recognize_text(image)

    # Convert image to Base64 for displaying
    _, buffer = cv2.imencode(".png", image)
    encoded_image = base64.b64encode(buffer).decode("utf-8")

    # Store image and text in session (NOT saving to folder)
    session["uploaded_file"] = file.filename  
    session["recognized_text"] = recognized_text.strip()
    session["translated_text"] = ""

    # Get user ID from session
    user_id = session.get("user_id")
    db = get_db()

    # Check if the file already exists for the user
    existing_file = db.execute(""" 
        SELECT * FROM uploaded_files WHERE user_id = ? AND file_name = ? 
    """, (user_id, file.filename)).fetchone()

    if existing_file:
        # File already exists, show flash message
        flash(f"File '{file.filename}' already exists. Please upload a different file .", "warning")
        # Pass the "redirect" flag to inform the front end to redirect
        return render_template("index.html", redirect_to_history=True)

    # Store the image and text in the database if it's a new file
    db.execute(""" 
        INSERT INTO uploaded_files (user_id, file_name, recognized_text, image_data)
        VALUES (?, ?, ?, ?)
    """, (user_id, file.filename, recognized_text.strip(), buffer.tobytes()))
    db.commit()

    return redirect(url_for("app3.display_result"))

@app3.route("/result", methods=["GET", "POST"])
def display_result():
    if request.method == "POST":
        session["recognized_text"] = request.form.get("recognized_text", session.get("recognized_text", ""))
        session["translated_text"] = request.form.get("translated_text", session.get("translated_text", ""))
        
        # Save edited text in database
        user_id = session.get("user_id")
        file_name = session.get("uploaded_file")
        edited_text = session["recognized_text"]
        translated_text = session["translated_text"]
        if user_id and file_name:
            db = get_db()
            db.execute(""" 
                UPDATE uploaded_files 
                SET edited_text = ?, translated_text = ? 
                WHERE user_id = ? AND file_name = ?
            """, (edited_text, translated_text, user_id, file_name))
            db.commit()

    # Fetch the image and text from the database
    user_id = session.get("user_id")
    file_name = session.get("uploaded_file")
    db = get_db()
    cursor = db.execute(""" 
        SELECT file_name, recognized_text, image_data 
        FROM uploaded_files 
        WHERE user_id = ? AND file_name = ?
    """, (user_id, file_name))
    file_data = cursor.fetchone()

    # Convert image to Base64 for displaying in the template
    image_base64 = None
    if file_data and file_data["image_data"]:
        image_base64 = base64.b64encode(file_data["image_data"]).decode("utf-8")

    return render_template("result.html",
                           uploaded_file=session.get("uploaded_file"),
                           recognized_text=session.get("recognized_text", ""),
                           translated_text=session.get("translated_text", ""),
                           image_base64=image_base64)

@app3.route("/translate", methods=["POST"])
def translate():
    language = request.form["language"]
    text = session.get("recognized_text", "")
    translated_text = translate_text(text, language)
    session["translated_text"] = translated_text
    return redirect(url_for("app3.display_result"))

@app3.route("/history")
def history():
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("login"))  # Redirect if not logged in

    db = get_db()
    cursor = db.execute("""
        SELECT file_name, upload_time, recognized_text, edited_text 
        FROM uploaded_files 
        WHERE user_id = ? 
        ORDER BY upload_time DESC
    """, (user_id,))
    files = cursor.fetchall()

    # Convert upload_time to datetime objects
    formatted_files = []
    for file in files:
        upload_time = file["upload_time"]
        if upload_time:
            file = dict(file)  # Convert from Row object to dict
            file["upload_time"] = datetime.strptime(upload_time, "%Y-%m-%d %H:%M:%S")  # Adjust format if needed
        formatted_files.append(file)

    return render_template("history.html", files=formatted_files)

@app3.route("/download/<file_name>")
def download(file_name):
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("login"))

    db = get_db()
    cursor = db.execute(
        "SELECT edited_text, recognized_text FROM uploaded_files WHERE user_id = ? AND file_name = ?",
        (user_id, file_name),
    )
    file_data = cursor.fetchone()

    if file_data:
        text_to_download = file_data["edited_text"] if file_data["edited_text"] else file_data["recognized_text"]
        if text_to_download:
            output = io.BytesIO()
            output.write(text_to_download.encode("utf-8"))
            output.seek(0)
            return send_file(output, as_attachment=True, download_name=f"{file_name}_last_edit.txt", mimetype="text/plain")

    return "No text available."

@app3.route("/delete/<file_name>", methods=["POST"])
def delete_file(file_name):
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("login"))
    
    db = get_db()
    db.execute("""
        DELETE FROM uploaded_files
        WHERE user_id = ? AND file_name = ?
    """, (user_id, file_name))
    db.commit()
    
    return redirect(url_for("app3.history"))

