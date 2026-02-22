PREREQUISITES
Before you begin, ensure you have the following installed on your system:
* Python 3.8 : https://www.python.org/downloads/
* Web Browser: Google Chrome, Edge, or Firefox (for camera access).
* Webcam: Built-in or external USB camera.


INSTALLATION INSTRUCTIONS
1. Download/Clone the Project
    cd /path/to/my-exercise-tracker

2. Create a Virtual Environment (Recommended)

Windows:
    python -m venv venv
    venv\Scripts\activate

Mac/Linux:
    python3 -m venv venv
    source venv/bin/activate

3. Install Dependencies
Install the required Python packages using pip:
    pip install -r requirements.txt

CONFIGURATION
Generative AI Setup (Optional but Recommended)
1. Get a free key here: https://aistudio.google.com/app/apikey
2. Set it as an environment variable in your terminal before running the app:

Windows PowerShell:
    $env:GEMINI_API_KEY = "YOUR_API_KEY_HERE"

Mac/Linux:
    export GEMINI_API_KEY="YOUR_API_KEY_HERE"


HOW TO RUN THE APPLICATION
1. Make sure your virtual environment is active.
2. Run the main application file:
    python main.py
3. You should see output indicating the server is running:
    * Running on http://127.0.0.1:5000
4. Open your web browser and go to: http://127.0.0.1:5000


