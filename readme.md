tm stands for theory marker.
the structure of the excel file is as follows
email, respose1, answer1, response2, answer2, etc

# 📝 Theory Marker

A **Flask-based web application** that automatically grades students’ theory responses against staff-provided reference answers using **Google Gemini API**.  

This tool is designed for developers building **AI-assisted grading systems**. It ingests an Excel file of student responses, applies AI grading logic, and returns structured JSON with scores and reasons.

---

## 🚀 Features
- Upload Excel files with student responses + staff answers.
- Auto-detects columns containing:
  - `response` → student answers
  - `answer` → staff reference answers
  - `email` (optional) → student identifiers
  - `score` (optional) → prefilled marks
- Uses **Google Gemini** for grading:
  - Scores answers on **0–10 scale**.
  - Provides concise reasoning (≤10 words).
- Returns results in JSON format for further integration.
- Lightweight Flask web UI for file upload & testing.

---

## 📂 Project Structure

