# Infix_ServiceHive - AutoStream AI Sales Agent 🎬

This repository contains the assignment project for the Machine Learning Intern position. 

The main application is located in the `autostream-agent` directory. It is a LangGraph-based conversational agent powered by Google Gemini 2.5 Flash, handling intent detection, RAG-based Q&A, and lead capture.

## How to Run

### Option 1: Quick Start (Windows)
1. Clone this repository to your PC.
2. Double-click the `run.bat` file in the root directory. 
3. The script will automatically:
   - Create a Python virtual environment.
   - Install all required dependencies.
   - Set up the `.env` file for you.
4. If it's your first time running, the script will pause and ask you to add your `GOOGLE_API_KEY` (or a comma-separated list of keys for `GOOGLE_API_KEYS` if you want key rotation) to the newly created `autostream-agent/.env` file. Once added, run `run.bat` again to start the agent!

### Option 2: Manual Setup (Any OS)
1. Navigate to the agent directory:
   ```bash
   cd autostream-agent
   ```
2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   # Windows:
   venv\Scripts\activate
   # macOS/Linux:
   source venv/bin/activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Set up your environment variables:
   ```bash
   cp .env.example .env
   ```
   *Edit the `.env` file and add your `GOOGLE_API_KEY` (or `GOOGLE_API_KEYS` for multiple keys).*

5. Run the application:
   ```bash
   python agent.py
   ```

## Project Structure
- `autostream-agent/` - Contains the Python application, knowledge base, and specific README.
- `Machine Learning Intern – Assignment Project.pdf` - The original assignment requirements.
- `run.bat` - Windows batch script for automated setup and running.
