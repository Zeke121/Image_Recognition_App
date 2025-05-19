import os
import cv2
import numpy as np
from flask import Flask, render_template, request, jsonify, url_for, send_from_directory
from werkzeug.utils import secure_filename
import uuid # For unique filenames

app = Flask(__name__)

# Configuration
UPLOAD_FOLDER = 'uploads'
MODEL_FOLDER = 'models'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload size

# Ensure upload folder exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Load pre-trained model and class names
PROTOTXT_PATH = os.path.join(MODEL_FOLDER, "MobileNetSSD_deploy.prototxt.txt")
MODEL_PATH = os.path.join(MODEL_FOLDER, "MobileNetSSD_deploy.caffemodel")

if not os.path.exists(PROTOTXT_PATH) or not os.path.exists(MODEL_PATH):
    print("ERROR: Model files not found. Please download them and place in the 'models' directory.")
    # You might want to exit or handle this more gracefully
    # For now, the app will likely crash if OpenCV tries to load non-existent files.

CLASSES = ["background", "aeroplane", "bicycle", "bird", "boat",
           "bottle", "bus", "car", "cat", "chair", "cow", "diningtable",
           "dog", "horse", "motorbike", "person", "pottedplant", "sheep",
           "sofa", "train", "tvmonitor"]
COLORS = np.random.uniform(0, 255, size=(len(CLASSES), 3))

try:
    net = cv2.dnn.readNetFromCaffe(PROTOTXT_PATH, MODEL_PATH)
    print("DNN Model loaded successfully.")
except cv2.error as e:
    print(f"Error loading DNN model: {e}")
    net = None # Set net to None if loading fails


def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Route to serve uploaded files
@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/')
def index():
    # List of dummy logos for the carousel
    logos = [
        {"name": "Python", "path": url_for('static', filename='img/python_logo.png')},
        {"name": "Flask", "path": url_for('static', filename='img/flask_logo.png')},
        {"name": "OpenCV", "path": url_for('static', filename='img/opencv_logo.png')},
        {"name": "Numpy", "path": url_for('static', filename='img/numpy_logo.png')},
        {"name": "JavaScript", "path": url_for('static', filename='img/js_logo.png')},
        {"name": "HTML5", "path": url_for('static', filename='img/html5_logo.png')},
        {"name": "CSS3", "path": url_for('static', filename='img/css3_logo.png')}
    ]
    # You'd create these logo images (e.g., python_logo.png) in static/img/
    # For simplicity, I'll make them generic if not found
    for logo in logos:
        if not os.path.exists(os.path.join(app.static_folder, 'img', os.path.basename(logo['path']))):
            # Create placeholder images if they don't exist (very basic)
            placeholder_img_path = os.path.join(app.static_folder, 'img', os.path.basename(logo['path']))
            if not os.path.exists(placeholder_img_path): # check again to avoid race
                os.makedirs(os.path.dirname(placeholder_img_path), exist_ok=True)
                try:
                    img = np.zeros((50, 150, 3), dtype=np.uint8)
                    img[:] = (60,60,60) # Dark grey
                    cv2.putText(img, logo['name'], (10, 35), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (200,200,200), 2)
                    cv2.imwrite(placeholder_img_path, img)
                    print(f"Created placeholder for {placeholder_img_path}")
                except Exception as e:
                    print(f"Error creating placeholder image: {e}")
            logo['path'] = url_for('static', filename='img/' + os.path.basename(logo['path']))


    return render_template('index.html', logos=logos)

@app.route('/analyze', methods=['POST'])
def analyze_image():
    if net is None:
        return jsonify({"error": "Model not loaded. Check server logs."}), 500

    if 'file' not in request.files:
        return jsonify({"error": "No file part"}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400

    if file and allowed_file(file.filename):
        original_filename = secure_filename(file.filename)
        ext = original_filename.rsplit('.', 1)[1].lower()
        unique_fn_stem = str(uuid.uuid4())
        
        input_filename = f"{unique_fn_stem}_input.{ext}"
        output_filename = f"{unique_fn_stem}_output.{ext}"

        input_filepath = os.path.join(app.config['UPLOAD_FOLDER'], input_filename)
        output_filepath = os.path.join(app.config['UPLOAD_FOLDER'], output_filename)
        
        file.save(input_filepath)

        image = cv2.imread(input_filepath)
        if image is None:
            # It's good to remove the saved file if it can't be read
            if os.path.exists(input_filepath):
                os.remove(input_filepath)
            return jsonify({"error": "Could not read image file. It might be corrupted or not a valid image."}), 400
        
        (h, w) = image.shape[:2]
        blob = cv2.dnn.blobFromImage(cv2.resize(image, (300, 300)), 0.007843, (300, 300), 127.5)

        net.setInput(blob)
        detections = net.forward()
        detected_objects = []

        for i in np.arange(0, detections.shape[2]):
            confidence = detections[0, 0, i, 2]
            if confidence > 0.3:
                idx = int(detections[0, 0, i, 1])
                if idx >= len(CLASSES):
                    print(f"Warning: Detected class index {idx} out of bounds for CLASSES list (len {len(CLASSES)}). Skipping.")
                    continue
                box = detections[0, 0, i, 3:7] * np.array([w, h, w, h])
                (startX, startY, endX, endY) = box.astype("int")
                label = "{}: {:.2f}%".format(CLASSES[idx], confidence * 100)
                detected_objects.append({
                    "label": CLASSES[idx],
                    "confidence": float(confidence),
                    "box": [int(startX), int(startY), int(endX), int(endY)]
                })
                cv2.rectangle(image, (startX, startY), (endX, endY), COLORS[idx], 2)
                y = startY - 15 if startY - 15 > 15 else startY + 15
                cv2.putText(image, label, (startX, y), cv2.FONT_HERSHEY_SIMPLEX, 0.5, COLORS[idx], 2)
        
        cv2.imwrite(output_filepath, image)

        # ***** THIS IS THE IMPORTANT CHANGE *****
        return jsonify({
            "success": True,
            "original_image_url": url_for('uploaded_file', filename=input_filename), # Use the new route
            "processed_image_url": url_for('uploaded_file', filename=output_filename), # Use the new route
            "detections": detected_objects
        })
    else:
        return jsonify({"error": "File type not allowed"}), 400

if __name__ == '__main__':
    app.run(debug=True)