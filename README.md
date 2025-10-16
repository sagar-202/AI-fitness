
# 🏋️‍♂️ AI Fitness Trainer (Flask + MediaPipe + OpenCV)

An AI-powered fitness trainer web app built with **Flask**, **OpenCV**, and **MediaPipe** that detects human poses, counts exercise repetitions, and visualizes workout progress.  
Users can **log in**, **track workouts**, and **view personalized reports** — all from a simple, modern web interface.

---

## 🚀 Features

- 🔐 **User Authentication**
  - Register, log in, and manage sessions (Flask + SQLite)
  - Secure password hashing with Werkzeug
  - Session-based user management

- 🧍‍♂️ **Pose Estimation & Rep Counting**
  - Counts repetitions for exercises (Push-ups, Squats, Curls, Crunches, etc.)
  - Built on MediaPipe Pose detection
  - Uses heuristic thresholds to detect form accuracy

- 💾 **Workout Tracking**
  - Logs all workouts to a local SQLite database
  - Saves `exercise_name`, `reps`, `avg_form_score`, and `date`

- 📊 **Reports & Analytics**
  - Summary of total reps per day/exercise
  - Interactive graphs with Chart.js / Matplotlib
  - Export as CSV (optional)

- 🌐 **Responsive Frontend**
  - Built using TailwindCSS
  - Mobile-friendly and modern interface

---


---

## ⚙️ Installation (Local Development)

### 1️⃣ Clone the Repository
```bash
git clone https://github.com/<your-username>/AI-Fitness-Trainer.git
cd AI-Fitness-Trainer

2️⃣ Create and Activate Virtual Environment
python -m venv venv
venv\Scripts\activate      # On Windows
source venv/bin/activate   # On macOS/Linux

3️⃣ Install Dependencies
pip install -r requirements.txt

4️⃣ Run the App
python app.py


Then open your browser and go to 👉 http://127.0.0.1:5000

🌍 Deployment Guide
🔹 Option 1: Deploy on Render (Recommended for Flask)
Step 1: Create a Render Account

👉 https://render.com

Step 2: Push Your Project to GitHub
git init
git add .
git commit -m "Initial commit"
git remote add origin https://github.com/<your-username>/AI-Fitness-Trainer.git
git push -u origin main

Step 3: Create a New Web Service

Go to Render Dashboard

Click New → Web Service

Connect your GitHub repo

Set:

Environment: Python

Build Command: pip install -r requirements.txt

Start Command: gunicorn app:app

Click Deploy

Your app will go live at:

https://ai-fitness-trainer.onrender.com

🔹 Option 2: Deploy on PythonAnywhere
Step 1: Upload Files

Log in to https://www.pythonanywhere.com/

Create a new Flask Web App

Upload app.py, templates/, and static/ folders

Step 2: Virtual Environment

Create and activate venv

Install dependencies:

pip install -r requirements.txt

Step 3: Configure WSGI

Open Web → WSGI configuration file

Update it to point to your app variable in app.py:

from app import app as application

Step 4: Reload App

Visit your live Flask site 🎉

🔹 Option 3: Deploy on Vercel (via Flask Adapter)
Step 1: Install vercel CLI
npm install -g vercel

Step 2: Create a vercel.json File
{
  "builds": [{ "src": "app.py", "use": "@vercel/python" }],
  "routes": [{ "src": "/(.*)", "dest": "app.py" }]
}

Step 3: Deploy
vercel


Your Flask app will be deployed at:

https://ai-fitness-trainer.vercel.app

🛠️ Tech Stack
Component	Technology
Frontend	HTML5, CSS3, TailwindCSS, Chart.js
Backend	Flask (Python)
Database	SQLite
Computer Vision	OpenCV, MediaPipe
Authentication	Werkzeug (password hashing), Flask sessions
Visualization	Matplotlib / Chart.js
📊 Reports Overview

Bar Chart: Exercise vs Total Reps

Line Graph: Progress Over Time

Summary Cards: Total Workouts, Reps, Avg Form Score

Example:

Push-ups: 120 reps
Squats: 80 reps
Bicep Curls: 65 reps

🧑‍💻 Future Enhancements

Add AI-based real-time form feedback

Integrate cloud sync (Firebase / Supabase)

Add personal goals and achievements dashboard

Export progress reports to PDF

