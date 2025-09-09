# theory marker


from flask import Flask, request, jsonify, render_template
from google import genai
from google.genai import types
import json
import pandas as pd
from io import BytesIO

# Initialize Flask app
app = Flask(__name__)

# Initialize Gemini Client (Replace with your actual API Key)
API_KEY = "AIzaSyB08vDyFoEZ5g6i4OTzNM0W-C4A1UbO2qU"
client = genai.Client(api_key=API_KEY)

# Reference answer by staff
# staffAnswer = "Physics can be defined as the study of energy and its interactions"

def mark_answer(studentResponse, staffAnswer):
    try:
        # Get student response from form data
        # studentResponse = request.form.get("student_response", "").strip()

        if not studentResponse:
            return jsonify({"error": "Student response is required"}), 400

        # Instruction for grading
        staffInstruction = """
        Grade the answer in the content on a scale of 0 to 10.
        Provide a reason for the grade in no more than 10 words.

        mark based on the staff answer not what you think is correct
        if the student's response is related to the staff answer upto 80 percent, give the student full mark
        Format your response as: {"score": X, "reason": "Your reason here"}
        """

        # Generate AI response
        response = client.models.generate_content(
            model="gemini-2.0-flash",
            contents=[studentResponse],
            config=types.GenerateContentConfig(
                system_instruction=f"""
                the answer to the question the student is been asked is: {staffAnswer}

                You are a lenient grader marking a student's response.
                staff instruction: {staffInstruction}
                """
            )
        )

        # Extract and parse response text
        response_text = response.text.strip()

        # Convert AI response to JSON
        response_data = json.loads(response_text)
        print(f'i got here {response_data}')

        # Extract values
        score = response_data.get("score", "N/A")
        reason = response_data.get("reason", "No reason provided")

        return {"score": score, "reason": reason}

    except json.JSONDecodeError:
        return {"error":"failed to whatever"}

    except Exception as e:
        return {"error":str(e)}

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/readfile', methods=['POST'])
def readfile():
    try:
        # Get the uploaded file
        uploaded_file = request.files.get('file')
        
        if uploaded_file.filename == '':
            return "No file selected", 400  # Handle case when no file is uploaded
        
        # Read the Excel file into a DataFrame
        df = pd.read_excel(BytesIO(uploaded_file.read()))  # Convert file to bytes and read it

        # Convert column names to lowercase for case-insensitive search
        df.columns = df.columns.str.lower()
        print(f'columns are {df.columns}') # print the columns of the dataframe (df.columns)

        # Find the column that contains the word 'response'
        response_columns = []
        answer_columns = []
        score_columns = []
        email_columns = []

        for col in df.columns:
            if "response" in col:  # Check if "response" is in the column name
                response_columns.append(col)
            if "answer" in col:  # Check if "response" is in the column name
                answer_columns.append(col)
            if "score" in col:  # Check if "response" is in the column name
                score_columns.append(col)
            if "email" in col:  # Check if "response" is in the column name
                email_columns.append(col)
                print(f'email column is {col}')
                # break  # Stop when found

            
        if not response_columns:
            return "No 'response' column found", 400
        
        responses = {}

        for _, row in df.iterrows():
            email = row[email_columns[0]] if email_columns else "Unknown"
            student_responses = {}

            for i in range(len(response_columns)):
                studentResponse = row[response_columns[i]]
                staffAnswer = row[answer_columns[i]] if i < len(answer_columns) else "N/A"
                score_data = mark_answer(studentResponse, staffAnswer)
                student_responses[response_columns[i]] = {
                    "studentResponse": studentResponse, 
                    "staffAnswer": staffAnswer, 
                    "score": score_data["score"],
                    "reason": score_data["reason"]
                }
                print(f'all data is: {student_responses}')

            responses[email] = student_responses

        
        


        return jsonify({"response_column(s)": response_columns, "responses": responses})
        # return jsonify({"response":"nothing"})

    except Exception as e:
        print(f'error is: {str(e)}')
        return f"Error: {str(e)}", 500



# Run the Flask app
if __name__ == '__main__':
    app.run(debug=True)



