import pandas as pd
from flask import Flask, request, jsonify, render_template, send_file
from google import genai
from google.genai import types
import json
from io import BytesIO
from openpyxl import Workbook
import re


app = Flask(__name__)


API_KEY = "AIzaSyB08vDyFoEZ5g6i4OTzNM0W-C4A1UbO2qU"
client = genai.Client(api_key=API_KEY)

def extract_json(text):
    """
    Extracts the first valid JSON object from a given text.
    Handles cases where JSON is wrapped in markdown (```json ... ```), 
    mixed with other text, or in unexpected formats.
    """
    try:
        
        text = re.sub(r"```[\w]*\n(.*?)\n```", r"\1", text, flags=re.DOTALL).strip()
        
        
        json_match = re.search(r"\{.*\}", text, re.DOTALL)
        if json_match:
            json_text = json_match.group(0)
            return json.loads(json_text)  
    except json.JSONDecodeError:
        return None  
    
    return None  

def mark_answer(studentResponse, staffAnswer):
    try:
        if not studentResponse:
            return {"error": "Student response is required"}, 400

        staffInstruction = """
            You are grading a student's response based on the provided staff answer.  
            Follow these grading rules strictly:  

            1. Grade on a scale of 0 to 10.  
            2. If the student's response is at least 99 percent similar to the staff answer, give full marks (10/10).  
            3. If the response is only partially correct, reduce marks accordingly.  
            4. If the response is completely incorrect or unrelated, give 0/10.  
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

                You are a strict grader marking a student's response using the following staff instruction.
                staff instruction: {staffInstruction}
                """
            )
        )

        response_text = response.text.strip()
        print("response: ", response_text)

        response_data = extract_json(response_text)

        if response_data is None:
            return {"error": "Failed to extract valid JSON from AI response"}

        score = response_data.get("score", "N/A")
        reason = response_data.get("reason", "No reason provided")

        return {"score": score, "reason": reason}

    except Exception as e:
        return {"error": str(e)}
    

@app.route('/')
def index():
    return render_template('index3.html')

@app.route('/readfile', methods=['POST'])
def readfile():
    try:
        uploaded_file = request.files.get('file')

        if uploaded_file.filename == '':
            return "No file selected", 400
        
        df = pd.read_excel(BytesIO(uploaded_file.read()))
        df.columns = df.columns.str.lower()
        filename = uploaded_file.filename.rsplit('.', 1)[0] 

        # Find name column and question columns (excluding timestamp)
        name_column = None
        response_columns = []
        
        for col in df.columns:
            if "name" in col.lower():
                name_column = col
            elif "timestamp" not in col.lower():
                response_columns.append(col)
            
        if not response_columns:
            return "No question columns found", 400
        if not name_column:
            return "No name column found", 400
        
        # Find teacher answers
        teacher_answers = {}
        for i, row in df.iterrows():
            if str(row[name_column]).lower() == "teacher":
                for j, response_col in enumerate(response_columns):
                    teacher_answers[j] = row[response_col]
        
        if not teacher_answers:
            return "No teacher answers found", 400
        
        # Add score and reason columns
        for j in range(len(response_columns)):
            score_column_name = f"score_{j+1}"
            reason_column_name = f"reason_{j+1}"
            if score_column_name not in df.columns:
                df[score_column_name] = ""
            if reason_column_name not in df.columns:
                df[reason_column_name] = ""
        
        # Add total score and percentage columns
        df['total_score'] = ""
        df['percentage'] = ""
        
        # Grade student responses
        for i, row in df.iterrows():
            if str(row[name_column]).lower() != "teacher":
                total_score = 0
                for j in range(len(response_columns)):
                    studentResponse = row[response_columns[j]]
                    teacherAnswer = teacher_answers.get(j, "N/A")
                    score_data = mark_answer(studentResponse, teacherAnswer)
                    
                    score = score_data.get('score', 0)
                    if isinstance(score, (int, float)):
                        total_score += score
                    
                    df.at[i, f'score_{j+1}'] = score
                    df.at[i, f'reason_{j+1}'] = score_data['reason']
                
                # Calculate percentage
                max_possible_score = len(response_columns) * 10
                percentage = (total_score / max_possible_score) * 100 if max_possible_score > 0 else 0
                
                df.at[i, 'total_score'] = total_score
                df.at[i, 'percentage'] = f"{percentage:.1f}%"

        # Save the updated DataFrame to a new Excel file
        output_file = BytesIO()
        df.to_excel(output_file, index=False)
        output_file.seek(0)

        return send_file(output_file, download_name=f"{filename}_graded.xlsx", as_attachment=True)

    except Exception as e:
        return f"Error: {str(e)}", 500

if __name__ == "__main__":
    app.run(debug=True)