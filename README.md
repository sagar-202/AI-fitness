
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

## 🧩 Project Structure

