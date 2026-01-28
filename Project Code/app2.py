from flask import Blueprint, render_template

app2 = Blueprint("app2", __name__)

@app2.route("/users")
def users():
    return render_template("users.html")

@app2.route("/about")
def about():
    return render_template("about.html")

@app2.route("/dashboard")
def dashboard():
    return render_template("dashboard.html")

@app2.route("/smartanalysis")
def smartanalysis():
    return render_template("smartanalysis.html")

@app2.route("/flashspeed")
def flashspeed():
    return render_template("flashspeed.html")

@app2.route("/securereliable")
def securereliable():
    return render_template("securereliable.html")

@app2.route("/features")
def downloads():
    return render_template("features.html")

from flask import Flask, render_template, request, redirect, url_for, send_from_directory, jsonify
import os

app = Flask(__name__)

UPLOAD_FOLDER = "uploads"
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

@app.route("/")
def index():
    return render_template("index.html")

@app.route("/uploads", methods=["POST"])
def upload_file():
    if "file" not in request.files:
        return "No file part", 400
    
    file = request.files["file"]
    if file.filename == "":
        return "No selected file", 400

    file_path = os.path.join(app.config["UPLOAD_FOLDER"], file.filename)
    file.save(file_path)
    
    return redirect(url_for("index"))

@app.route("/get_files", methods=["GET"])
def get_files():
    files = []
    for filename in os.listdir(app.config["UPLOAD_FOLDER"]):
        filepath = os.path.join(app.config["UPLOAD_FOLDER"], filename)
        size = os.path.getsize(filepath) // 1024  # Size in KB
        files.append({"name": filename, "size": size})

    return jsonify(files)

@app.route("/download/<filename>")
def download_file(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename, as_attachment=True)

if __name__ == "__main__":
    app.run(debug=True)
