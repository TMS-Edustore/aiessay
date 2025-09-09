import pandas as pd
from flask import Flask, request, jsonify, render_template, send_file
from google import genai
from google.genai import types
import json
from io import BytesIO
from openpyxl import Workbook
import re
from flask_socketio import SocketIO
import time
import threading

# Initialize Flask app
app = Flask(__name__)
socketio = SocketIO(app, debug=True, async_mode='eventlet', cors_allowed_origins="*")

# Initialize Gemini Client (Replace with your actual API Key)
API_KEY = "AIzaSyB08vDyFoEZ5g6i4OTzNM0W-C4A1UbO2qU"
client = genai.Client(api_key=API_KEY)

def extract_json(text):
    """
    Extracts the first valid JSON object from a given text.
    Handles cases where JSON is wrapped in markdown (```json ... ```), 
    mixed with other text, or in unexpected formats.
    """
    try:
        # Remove markdown-style blocks (handles ```json, ```python, etc.)
        text = re.sub(r"```[\w]*\n(.*?)\n```", r"\1", text, flags=re.DOTALL).strip()
        
        # Find first valid JSON using regex (handles misplaced text)
        json_match = re.search(r"\{.*\}", text, re.DOTALL)
        if json_match:
            json_text = json_match.group(0)
            return json.loads(json_text)  # Ensure it's valid JSON

    except json.JSONDecodeError:
        return None  # JSON is invalid
    return None  # No JSON found

def mark_answer(studentResponse, staffAnswer):
    try:
        if not studentResponse:
            return {"error": "Student response is required"}, 400

        staffInstruction = """
            You are grading a student's response based on the provided staff answer.  
            Follow these grading rules strictly:  

            1. Grade on a scale of 0 to 10.  
            2. If the student's response is at least 80 percent similar to the staff answer, give full marks (10/10).  
            3. If the response is only partially correct, reduce marks accordingly.  
            4. If the response is completely incorrect or unrelated, give 2/10.  
            5. Always explain your score** in 10 words or less.  
            6. If there is no response, give 0/10.

            Response Format (JSON only):  
            {"score": X, "reason": "Your reason here"}  
            """

        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=[studentResponse],
            config=types.GenerateContentConfig(
                system_instruction=f"""
                the answer to the question the student is been asked is: {staffAnswer}

                You are a lenient grader marking a student's response using the following staff instruction.
                staff instruction: {staffInstruction}
                """
            )
        )

        response_text = response.text.strip()
        response_data = extract_json(response_text)

        if response_data is None:
            return {"error": "Failed to extract valid JSON from AI response"}

        score = response_data.get("score", "N/A")
        reason = response_data.get("reason", "No reason provided")

        return {"score": score, "reason": reason}

    except Exception as e:
        return {"error": str(e)}

def background_grading_task(df, response_columns, answer_columns, filename):
    global grading_progress
    global grading_progress_percentage

    total_rows = len(df)
    grading_progress = 0

    for i, row in df.iterrows():
        for j in range(len(response_columns)):
            studentResponse = row[response_columns[j]]
            staffAnswer = row[answer_columns[j]] if j < len(answer_columns) else "N/A"
            score_data = mark_answer(studentResponse, staffAnswer)

            df.at[i, f'score_{j+1}'] = score_data['score']
            df.at[i, f'reason_{j+1}'] = score_data['reason']

        # Update progress
        grading_progress += 1
        grading_progress_percentage = int((grading_progress / total_rows) * 100)
        socketio.emit('progress_update', {'progress': grading_progress_percentage})

    # Save the updated DataFrame to a new Excel file
    print(f'completed background work')
    output_file = BytesIO()
    df.to_excel(output_file, index=False)
    output_file.seek(0)

    # Notify the client that the file is ready
    socketio.emit('file_ready', {'filename': f"{filename}_graded.xlsx"})

@app.route('/')
def index():
    return render_template('index.html')

@socketio.on('connect')
def handle_connect():
    print("Client connected")
    socketio.emit('message', {'message': 'Connected to server!'})

@app.route('/readfile', methods=['POST'])
def readfile():
    try:
        uploaded_file = request.files.get('file')
        if uploaded_file.filename == '':
            return "No file selected", 400
        
        df = pd.read_excel(BytesIO(uploaded_file.read()))
        df.columns = df.columns.str.lower()
        filename = uploaded_file.filename.rsplit('.', 1)[0] 

        response_columns = [col for col in df.columns if "response" in col]
        answer_columns = [col for col in df.columns if "answer" in col]

        if not response_columns:
            return "No 'response' column found", 400

        # Insert score and reason columns if they don't exist
        for j in range(len(response_columns)):
            score_column_name = f"score_{j+1}"
            reason_column_name = f"reason_{j+1}"

            if score_column_name not in df.columns:
                df.insert(df.columns.get_loc(answer_columns[j]) + 1, score_column_name, "")
            if reason_column_name not in df.columns:
                df.insert(df.columns.get_loc(answer_columns[j]) + 2, reason_column_name, "")

        # Start the background grading task
        socketio.start_background_task(background_grading_task, df, response_columns, answer_columns, filename)

        return jsonify({"message": "Grading started"}), 200

    except Exception as e:
        return f"Error: {str(e)}", 500

if __name__ == "__main__":
    socketio.run(app, debug=True, allow_unsafe_werkzeug=True)