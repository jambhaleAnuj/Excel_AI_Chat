# Excel Q&A Agent with Comments Support

A Streamlit web app that allows you to upload an Excel file and ask questions about your data using natural language. The app leverages Google Generative AI (Gemma) via LangChain to answer queries, including those related to comments or feedback columns in your dataset.

---

## Features
- **Upload Excel files** (`.xlsx`)
- **Ask questions** about your data in plain English
- **Handles comments/feedback** columns separately for targeted queries
- **Displays results** as tables or text, depending on the query

---

## Installation

### 1. Clone the Repository
```powershell
git clone https://github.com/jambhaleAnuj/Excel_AI_Chat.git
cd Excel_chat_streamlit 
```

### 2. Set Up a Python Environment (Recommended)
It is recommended to use a virtual environment:
```powershell
python -m venv venv
.\venv\Scripts\activate
```

### 3. Install Dependencies
```powershell
pip install -r requirements.txt
```

### 4. Set Up Google Generative AI API Key
- Obtain an API key for Google Generative AI (Gemma) from [Google AI Studio](https://aistudio.google.com/app/apikey).
- You can set the key in your environment variables or directly in the code (for demo purposes, the key is hardcoded in `app.py`).
- **For production, use environment variables or Streamlit secrets for security.**

#### To set as an environment variable (Windows PowerShell):
```powershell
$env:GOOGLE_API_KEY="your-google-api-key"
```

---

## Usage

### 1. Start the Streamlit App
```powershell
streamlit run app.py
```

### 2. In Your Browser
- Open the provided local URL (usually `http://localhost:8501`)
- Upload your Excel file (`.xlsx`)
- Enter your question in the text box (e.g., "Show all employees in the Sales department" or "List all comments for John Doe")
- View the AI-generated response as a table or text

---

## Example Queries
- `List all employees with a rating above 4.`
- `Show comments for employee Jane Smith.`
- `Summarize the feedback for the marketing team.`

---

## Notes
- The app processes your Excel data in-memory and does not store files.
- For best results, ensure your Excel file has clear headers and, if using comments, a column named `Comments`.
- The AI model may take a few seconds to respond, depending on query complexity and API speed.

---

## Troubleshooting
- **ModuleNotFoundError**: Ensure all dependencies are installed with `pip install -r requirements.txt`.
- **API Key Errors**: Double-check your Google API key and environment variable setup.
- **Excel Read Errors**: Make sure your file is `.xlsx` format and not open in another program.

---

## License
This project is for educational/demo purposes. Please secure your API keys and do not share sensitive data.

---

## Credits
- [Streamlit](https://streamlit.io/)
- [LangChain](https://python.langchain.com/)
- [Google Generative AI](https://aistudio.google.com/)
