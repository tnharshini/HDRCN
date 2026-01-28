import os
import cv2
import numpy as np
import tensorflow as tf
import pytesseract
import pandas as pd
from deep_translator import GoogleTranslator
from tensorflow.keras.layers import Conv2D, MaxPooling2D, Flatten, LSTM, Dense, Dropout, Bidirectional
from tensorflow.keras.models import Sequential

# Set Tesseract OCR Path
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# IAM Dataset Path
IAM_DATASET_PATH = "D:/archive/data"

# Ensure model file exists
MODEL_FILE = "handwritten_model.h5"

# Function to preprocess image (Updated to accept an image array)
def preprocess_image(image):
    """Prepares an image array for model prediction"""
    img = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)  # Convert to grayscale
    img = cv2.resize(img, (128, 32))  # Resize for CNN model
    img = img.astype('float32') / 255.0  # Normalize
    img = np.expand_dims(img, axis=[0, -1])  # Add batch & channel dimensions
    return img

# Load IAM Dataset
def load_iam_data():
    """Loads the IAM dataset for training"""
    images, labels = [], []
    label_path = os.path.join(IAM_DATASET_PATH, "IAM_labels.csv")

    if not os.path.exists(label_path):
        print("Error: Labels file not found!")
        return [], []

    df = pd.read_csv(label_path)
    for _, row in df.iterrows():
        image_path = os.path.join(IAM_DATASET_PATH, row['filename'])
        if os.path.exists(image_path):
            img = cv2.imread(image_path)
            images.append(preprocess_image(img))
            labels.append(row['text'])

    return np.array(images), np.array(labels)

# Build CNN + RNN (LSTM) Model
def build_model():
    """Creates and compiles the CNN + LSTM model"""
    model = Sequential([
        Conv2D(32, (3, 3), activation='relu', input_shape=(32, 128, 1)),
        MaxPooling2D(pool_size=(2, 2)),
        Conv2D(64, (3, 3), activation='relu'),
        MaxPooling2D(pool_size=(2, 2)),
        Flatten(),
        Dense(128, activation='relu'),
        Dropout(0.2),
        Bidirectional(LSTM(64, return_sequences=True)),
        Bidirectional(LSTM(32)),
        Dense(256, activation='relu'),
        Dense(128, activation='relu'),
        Dense(27, activation='softmax')  # 26 letters + space
    ])
    
    model.compile(loss='categorical_crossentropy', optimizer='adam', metrics=['accuracy'])
    return model

# Train and Save Model
def train_model():
    """Trains the model on IAM dataset"""
    X, y = load_iam_data()
    if len(X) == 0:
        print("Error: No training data found.")
        return None
    model = build_model()
    model.fit(X, y, epochs=10, batch_size=32, validation_split=0.2)
    model.save(MODEL_FILE)
    print("Model training completed and saved.")
    return model
# Load trained model or train a new one
def load_trained_model():
    """Loads the trained model or trains a new one if not found"""
    if os.path.exists(MODEL_FILE):
        return tf.keras.models.load_model(MODEL_FILE)
    return None  # Return None if no model is found
# Recognize Text using Tesseract only (clean output)
def recognize_text(image):
    """Uses Tesseract OCR to recognize clean handwriting text."""
    ocr_text = pytesseract.image_to_string(image, lang='eng')
    return ocr_text.strip()

# Run test
if __name__ == "__main__":
    test_image_path = input("Enter image path: ")
    img = cv2.imread(test_image_path)
    if img is not None:
        result = recognize_text(img)
        print("Recognized Text:", result)
    else:
        print("Failed to load image.")