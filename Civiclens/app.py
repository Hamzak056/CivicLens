import base64
import json
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from flask import Flask, render_template, request, jsonify
from google import genai

app = Flask(__name__)

# ---- Put your keys directly here ----
GEMINI_API_KEY = "AQ.Ab8RN6K3_Z3JDH-4vLeEg8AEbx6rMTkhsah1HLeBHm0YAJ4cCQ"
EMAIL_USER = "azkakhaliq100204@gmail.com"
EMAIL_PASS = "sdevtkgyqoxkpfeu"
# --------------------------------------

# Models are tried in order until one works
MODELS_TO_TRY = ['gemini-2.5-flash', 'gemini-2.0-flash', 'gemini-3.5-flash-lite']


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/analyze', methods=['POST'])
def analyze():
    try:
        if not GEMINI_API_KEY or GEMINI_API_KEY.startswith("PASTE_"):
            return jsonify({'error': 'Set GEMINI_API_KEY in app.py'}), 500

        data = request.json
        image_data = data.get('image')
        location = data.get('location')
        coords = data.get('coords')

        if not image_data:
            return jsonify({'error': 'Image is required'}), 400

        if ',' in image_data:
            image_bytes = base64.b64decode(image_data.split(',')[1])
        else:
            image_bytes = base64.b64decode(image_data)

        location_context = (
            f"GPS Coordinates: Latitude {coords.get('lat')}, Longitude {coords.get('lng')}. Exact Location: {location}"
            if coords else f"Exact Location: {location or 'Rawalpindi / Islamabad, Pakistan'}"
        )

        prompt = f"""
You are an expert AI civic infrastructure assistant for Pakistan (working with authorities like CDA, RDA, WASA, and TMA).
Analyze this image of a civic issue (such as an open manhole, pothole, or garbage).
Context Location: {location_context}

Provide a JSON response strictly adhering to this structure, with no markdown formatting around it (return raw JSON):
{{
  "issueType": "Short name of the issue",
  "department": "Responsible Municipal Department",
  "severity": "Low" | "Medium" | "High",
  "exactLocation": "{location}",
  "englishComplaint": "A formal official complaint letter in English referencing the exact location and safety hazard.",
  "urduComplaint": "A formal official municipal application in Urdu script referencing the exact location.",
  "mitigationSteps": [
    "Step 1 safety precaution",
    "Step 2 temporary marker advice"
  ],
  "helpline": "Helpline number"
}}
        """

        ai_client = genai.Client(api_key=GEMINI_API_KEY)

        response = None
        last_error = None

        for model_name in MODELS_TO_TRY:
            try:
                print(f"Trying model: {model_name}...")
                response = ai_client.models.generate_content(
                    model=model_name,
                    contents=[
                        prompt,
                        {
                            'inline_data': {
                                'mime_type': 'image/jpeg',
                                'data': base64.b64encode(image_bytes).decode('utf-8')
                            }
                        }
                    ]
                )
                if response and response.text:
                    break
            except Exception as e:
                last_error = e
                print(f"Model {model_name} failed: {str(e)}")
                continue

        if not response or not response.text:
            raise Exception(f"All models failed. Last error: {str(last_error)}")

        text_response = response.text.strip()
        if text_response.startswith('```'):
            text_response = text_response.split('```')[1]
            if text_response.startswith('json'):
                text_response = text_response[4:]
        text_response = text_response.strip('`').strip()

        result_json = json.loads(text_response)
        return jsonify(result_json)

    except Exception as e:
        print("Error in analyze:", str(e))
        return jsonify({'error': str(e)}), 500


@app.route('/api/send-email', methods=['POST'])
def send_email():
    try:
        data = request.json
        subject = data.get('subject')
        message = data.get('message')

        msg = MIMEMultipart()
        msg['From'] = EMAIL_USER
        msg['To'] = 'hamzakharal058@gmail.com'
        msg['Subject'] = subject
        msg.attach(MIMEText(message, 'plain'))

        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(EMAIL_USER, EMAIL_PASS)
        server.sendmail(EMAIL_USER, 'hamzakharal058@gmail.com', msg.as_string())
        server.quit()

        return jsonify({'success': True, 'message': 'Email sent successfully via Flask server!'})
    except Exception as e:
        print("Email Error:", str(e))
        return jsonify({'error': str(e)}), 500


# This block must be at the left edge (not indented) or the server never starts
if __name__ == '__main__':
    print("DEBUG: Starting Flask server on port 3000...")
    app.run(debug=True, port=3000)