from flask import Flask, render_template, request, jsonify, send_from_directory
import requests
import os
from dotenv import load_dotenv
import pytesseract

from PIL import Image
import uuid
from werkzeug.utils import secure_filename
import base64
import io
# At the top of your app.py
import platform
import pytesseract

# Configure Tesseract path - modify this path to match your installation
TESSERACT_PATH = r'C:\Program Files\Tesseract-OCR\tesseract.exe'  # Default path
# Alternative common paths:
# TESSERACT_PATH = r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe'
# TESSERACT_PATH = r'D:\Program Files\Tesseract-OCR\tesseract.exe'

if platform.system() == 'Windows':
    # Verify if Tesseract exists at the specified path
    if os.path.exists(TESSERACT_PATH):
        pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH
    else:
        print(f"Warning: Tesseract not found at {TESSERACT_PATH}")
        print("Please install Tesseract or update the path in the code.")
        # You can either exit here or let it try to use system PATH
        # sys.exit(1)

# Test Tesseract availability
try:
    # Simple test to check if Tesseract is working
    test_image = Image.new('RGB', (50, 50), color='white')
    pytesseract.image_to_string(test_image)
    print("Tesseract is working correctly!")
except Exception as e:
    print(f"Error testing Tesseract: {str(e)}")
    print("Please check Tesseract installation and path")
# Load environment variables
load_dotenv()

app = Flask(__name__)

# Configure upload settings
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

class OpenRouterAI:
    def __init__(self):
        self.api_key = os.getenv("OPENROUTER_API_KEY")
        if not self.api_key:
            raise ValueError("OpenRouter API Key is missing. Please set OPENROUTER_API_KEY in .env file.")
        self.base_url = "https://openrouter.ai/api/v1/chat/completions"
    
    def generate_response(self, messages):
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "http://localhost:5000",
            "X-Title": "Flask OpenRouter Chat"
        }
        
        payload = {
            "model": "anthropic/claude-3-haiku",
            "messages": messages
        }
        
        try:
            response = requests.post(self.base_url, headers=headers, json=payload)
            response.raise_for_status()
            return response.json()['choices'][0]['message']['content']
        except Exception as e:
            return f"An error occurred: {str(e)}"

# Initialize OpenRouter AI
ai = OpenRouterAI()

def process_image(image_path):
    """Extract text from image using OCR"""
    try:
        image = Image.open(image_path)
        text = pytesseract.image_to_string(image)
        return text.strip()
    except Exception as e:
        return f"Error processing image: {str(e)}"

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    data = request.get_json()
    messages = data.get('messages', [])
    
    if not messages:
        return jsonify({"error": "No messages provided"}), 400
    
    response = ai.generate_response(messages)
    return jsonify({"response": response})

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files and 'image' not in request.form:
        return jsonify({"error": "No file provided"}), 400
    
    try:
        if 'file' in request.files:
            # Handle regular file upload
            file = request.files['file']
            if file.filename == '':
                return jsonify({"error": "No selected file"}), 400
            
            if file and allowed_file(file.filename):
                filename = secure_filename(str(uuid.uuid4()) + os.path.splitext(file.filename)[1])
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
        else:
            # Handle base64 image data from camera
            image_data = request.form['image'].split(',')[1]
            image_bytes = base64.b64decode(image_data)
            image = Image.open(io.BytesIO(image_bytes))
            filename = f"{uuid.uuid4()}.jpg"
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            image.save(filepath)

        # Process the image with OCR
        extracted_text = process_image(filepath)
        
        return jsonify({
            "success": True,
            "text": extracted_text,
            "filename": filename
        })
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

if __name__ == '__main__':
    app.run(debug=True)
