# 🏋️‍♂️ AI Fitness Trainer (Flask + MediaPipe + OpenCV)

An AI-powered fitness trainer web app built with **Flask**, **OpenCV**, and **MediaPipe** that detects human poses, counts exercise repetitions, and visualizes workout progress.  
Users can **log in**, **track workouts**, and **view personalized reports** — all from a simple, modern web interface.

---

## 🚀 Features

### 🔐 User Authentication
- Register, log in, and manage sessions (**Flask + SQLite**)
- Secure password hashing with **Werkzeug**
- Session-based user management for persistent login

### 🧍‍♂️ Pose Estimation & Rep Counting
- Counts repetitions for exercises such as:
  - Push-ups
  - Squats
  - Bicep Curls
  - Crunches
- Built using **MediaPipe Pose detection**
- Uses heuristic thresholds to determine proper form and count valid reps

### 💾 Workout Tracking
- Logs all workouts to a **local SQLite database**
- Saves fields:
  - `exercise_name`
  - `reps`
  - `avg_form_score`
  - `session_date`

### 📊 Reports & Analytics
- Displays a **summary of total reps** per exercise and per day
- Interactive charts built with **Chart.js** or **Matplotlib**
- Option to export progress as CSV (coming soon)

### 🌐 Responsive Frontend
- Built using **TailwindCSS**
- Mobile-friendly and modern user interface

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

Your app will be live at:
🌐 https://ai-fitness-trainer.onrender.com

🔹 Option 2: Deploy on PythonAnywhere
Step 1: Upload Files

Log in to https://www.pythonanywhere.com/

Create a new Flask Web App

Upload app.py, templates/, and static/ folders

Step 2: Virtual Environment
pip install -r requirements.txt

Step 3: Configure WSGI

Edit the WSGI configuration file:

from app import app as application

Step 4: Reload App

Visit your live Flask site 🎉


🤝 Contributing
Contributions are always welcome!

1.Fork the repository

2.Create a new branch (feature/your-feature)

3.Commit your changes

4.Submit a pull request
