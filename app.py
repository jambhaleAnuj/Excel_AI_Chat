import os
import streamlit as st
import pandas as pd
from langchain_experimental.agents.agent_toolkits import create_csv_agent
from langchain_google_genai import ChatGoogleGenerativeAI
import tempfile
from io import StringIO
import re

import json
from pathlib import Path

# Set up Google API Key
os.environ["GOOGLE_API_KEY"] = "AIzaSyDIYgJ01me6YE6yAzaJkyeZx3jHGxWKAR0"

# --- File Path for History ---
HISTORY_FILE = Path("chat_history.json")

# --- Load/Save Chat History ---
def load_chat_history():
    if HISTORY_FILE.exists():
        with open(HISTORY_FILE, "r") as f:
            return json.load(f)
    return []

def save_chat_history(history):
    with open(HISTORY_FILE, "w") as f:
        json.dump(history, f, indent=2)

# Define helper functions
# def get_enriched_prompt(query):
#     context = (
#         "You are a data analyst with access to a dataset. "
#         "If the query involves listing or filtering data (like finding details about a person), "
#         "perform an exact match by converting both the dataset and the input to lowercase and removing extra spaces. "
#         "If the query is asking for structured data, respond in CSV format with headers. "
#         "For summaries, use natural language."
#     )
#     return f"{context}\n\nUser Query: {query}"

def get_enriched_prompt(query):
    query_lower = query.lower()

    # Keywords that *strongly* imply needing tabular output
    csv_keywords = ["list", "show", "filter", "table", "display", "all employees", "summary of", "csv","tabular", "structured", "answer in table format", "answer in csv format", "answer in tabular format", "answer in structured format"]

    if any(kw in query_lower for kw in csv_keywords):
        context = (
            # "You are a data analyst with access to a dataset. "
            # "For this query, you MUST return the results **strictly** in CSV format with headers as the first row. "
            # "Use comma `,` as the separator, and ensure each row corresponds to one record. "
            # "DO NOT add any explanations, notes, or markdown formatting. Output only the CSV content."
            # "Ensure exact match filtering where possible by converting both dataset values and user inputs to lowercase and trimming whitespace."
            # "Even if the answer is a single record, return it in CSV format with headers."
            # "Each line is a separate row.\n\n"
            # "**Example:**\nEmployee Name\nJohn Doe\nJane Smith\nRobert Brown\n\n"
            # "For this query, return the result in CSV format ONLY, with no explanation or markdown. "
             "You are a data analyst with access to a dataset. "
        "Return the result **strictly** in CSV format. "
        "Use a comma `,` as the separator. Start the output with a header row. "
        "Do NOT include any explanations or markdown formatting. "
        "Return the CSV inside a code block marked with ```csv and ``` so that it is easy to extract."
        "Example:\n```csv\nEmployee Name\nJohn Doe\nJane Smith\n```\n"
        "Ensure exact matching by converting both dataset and input to lowercase and removing whitespace.\n"

        )
    else:
        context = (
            "You are a data analyst with access to a dataset. "
            "Respond to the user's query in natural language. "
            "If My Query asks for comment. Do not truncate the comment. Do not add your own explanation. Just return the full comment."
            "Ensure exact match filtering where possible by converting both dataset values and user inputs to lowercase and trimming whitespace."
            "Only use CSV format if the user explicitly asks for tabular or structured output."
        )

    return f"{context}\n\nUser Query: {query}"



def create_agents(excel_file):
    df = pd.read_excel(excel_file, dtype=str)

    # Strip leading/trailing whitespaces from all string cells
    df = df.applymap(lambda x: x.strip() if isinstance(x, str) else x)

    # Create temporary CSVs
    # temp_main = tempfile.NamedTemporaryFile(delete=False, suffix=".csv")
    # temp_comments = tempfile.NamedTemporaryFile(delete=False, suffix=".csv")
    temp_main = tempfile.NamedTemporaryFile(delete=False, suffix=".csv", mode='w', newline='')
    temp_comments = tempfile.NamedTemporaryFile(delete=False, suffix=".csv", mode='w', newline='')



    df_main = df.drop(columns=['RMG Comments'], errors='ignore')
    df_comments = df[['Employee Name', 'RMG Comments']] if 'RMG Comments' in df.columns else pd.DataFrame()

    df_main.to_csv(temp_main.name, index=False)
    if not df_comments.empty:
        df_comments.to_csv(temp_comments.name, index=False)
    
    # Initialize LLM
    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash-preview-05-20")

    # Create agents
    main_agent = create_csv_agent(
        llm, temp_main.name, verbose=True, allow_dangerous_code=True
    )
    comments_agent = None
    if not df_comments.empty:
        comments_agent = create_csv_agent(
            llm, temp_comments.name, verbose=True, allow_dangerous_code=True
        )

    return main_agent, comments_agent

# def handle_user_query(query, main_agent, comments_agent):
#     final_query = get_enriched_prompt(query)
#     agent = comments_agent if ('comment' in query.lower() or 'feedback' in query.lower()) else main_agent

#     try:
#         return agent.run(final_query)
#     except ValueError as e:
#         error_text = str(e)
#         if "Could not parse LLM output:" in error_text:
#             summary = error_text.split("Could not parse LLM output:", 1)[-1].strip()
#             return f"[Summary Fallback] {summary}"
#         else:
#             raise e
        

# --- Run Query + Detect Intent ---
def handle_user_query(query, main_agent, comments_agent):
    final_query = get_enriched_prompt(query)
    use_comments = 'comment' in query.lower() or 'feedback' in query.lower()
    is_structured = any(kw in query.lower() for kw in ["list", "table", "csv", "show", "display", "filter"])

    agent = comments_agent if use_comments else main_agent

    try:
        result = agent.run(final_query)
        return {"result": result, "is_structured": is_structured}
    except ValueError as e:
        error_text = str(e)
        if "Could not parse LLM output:" in error_text:
            summary = error_text.split("Could not parse LLM output:", 1)[-1].strip()
            return {"result": summary, "is_structured": False}
        else:
            raise e


# def try_parse_csv(text):
#     try:
#         # Try reading entire response as CSV
#         df = pd.read_csv(StringIO(text))
#         if df.shape[1] > 1:
#             return df
#     except Exception:
#         pass

#     # Try extracting a CSV block
#     csv_block = re.search(r"((?:[^\n]*,)+[^\n]*\n(?:.*\n?)+)", text)
#     if csv_block:
#         try:
#             df = pd.read_csv(StringIO(csv_block.group(1)))
#             if df.shape[1] > 1:
#                 return df
#         except Exception:
#             pass
#     return None
def try_parse_csv_or_table(text):
    from io import StringIO

    # Try CSV code block
    csv_block = re.search(r"```csv\n(.*?)```", text, re.DOTALL)
    if csv_block:
        try:
            return pd.read_csv(StringIO(csv_block.group(1)))
        except Exception:
            pass

    # Try plain CSV
    try:
        df = pd.read_csv(StringIO(text))
        if not df.empty and df.shape[1] > 0:
            return df
    except Exception:
        pass

    # Try markdown table (e.g. | Employee Name | ...)
    try:
        lines = text.strip().splitlines()
        table_lines = [line for line in lines if '|' in line and not line.strip().startswith("#")]
        if len(table_lines) >= 2:
            raw_table = '\n'.join(table_lines)
            df = pd.read_csv(StringIO(raw_table), sep="|", engine="python", skipinitialspace=True)
            df = df.dropna(axis=1, how='all')  # Drop empty columns created by separators
            df.columns = [col.strip() for col in df.columns]
            df = df.applymap(lambda x: x.strip() if isinstance(x, str) else x)
            return df
    except Exception:
        pass

    return None



# --- Cleanup Output ---
def clean_llm_output(text: str) -> str:
    text = text.replace("[Summary Fallback]", "").strip()
    text = text.replace(
        "For troubleshooting, visit: https://python.langchain.com/docs/troubleshooting/errors/OUTPUT_PARSING_FAILURE",
        ""
    ).strip()
    return text


# ---------- Streamlit UI ----------
st.markdown("""
    <style>
        body {
            font-family: 'Segoe UI', sans-serif;
        }
        .title {
            background: linear-gradient(to right, #6a11cb, #2575fc);
            padding: 20px;
            border-radius: 10px;
            text-align: center;
            font-size: 32px;
            font-weight: bold;
            color: white;
        }
        .chat-message.user {
            background-color: rgba(33, 150, 243, 0.1);
            border-left: 5px solid #2196f3;
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 10px;
            color: inherit;
        }
        .chat-message.assistant {
            background-color: rgba(76, 175, 80, 0.1);
            border-left: 5px solid #4caf50;
            padding: 15px;
            border-radius: 8px;
            margin-bottom: 20px;
            color: inherit;
        }
        .sidebar-title {
            background-color: #3f51b5;
            padding: 10px;
            border-radius: 5px;
            text-align: center;
            color: white;
            margin-bottom: 10px;
        }
    </style>
""", unsafe_allow_html=True)


st.title("📊 RMG ChatBot")

# Load history
if "chat_history" not in st.session_state:
    st.session_state.chat_history = load_chat_history()


# # Initialize chat history
# if "chat_history" not in st.session_state:
#     st.session_state.chat_history = []

# Sidebar for chat history
with st.sidebar:
    st.markdown('<div class="sidebar-title">🕘 Chat History</div>', unsafe_allow_html=True)

    for i, chat in enumerate(st.session_state.chat_history):
        with st.expander(f"📌 Q{i+1}: {chat['user'][:30]}..."):
            st.markdown(f"<div class='chat-message user'><strong>User:</strong><br>{chat['user']}</div>", unsafe_allow_html=True)
            st.markdown(f"<div class='chat-message assistant'><strong>Assistant:</strong><br>{chat['assistant']}</div>", unsafe_allow_html=True)
            if st.button("🗑️ Delete This", key=f"delete_{i}"):
                st.session_state.chat_history.pop(i)
                save_chat_history(st.session_state.chat_history)
                st.rerun()

    st.markdown("---")
    if st.button("🧹 Clear All History"):
        st.session_state.chat_history = []
        if HISTORY_FILE.exists():
            HISTORY_FILE.unlink()
        st.rerun()

with st.container():
    st.markdown("<div class='file-upload-box'><b>📂 Upload Excel File</b></div>", unsafe_allow_html=True)
    uploaded_file = st.file_uploader("", type=["xlsx"])

if uploaded_file:
    
    st.success("✅ File uploaded Successfully! Ask your questions below.")
    st.markdown("---")
    query = st.chat_input("Enter your question about the data:")

    if query:
        st.chat_message("user").write(query)
        with st.spinner("🤖 Thinking..."):
            try:
                # main_agent, comments_agent = create_agents(uploaded_file)
                # result = handle_user_query(query, main_agent, comments_agent)
                # st.write("### Response:")
                main_agent, comments_agent = create_agents(uploaded_file)
                response = handle_user_query(query, main_agent, comments_agent)
                result = clean_llm_output(response["result"])
                is_structured = response["is_structured"]

                # Try parsing CSV
                parsed_df = try_parse_csv_or_table(result)

                with st.chat_message("assistant"):
                    
                    if parsed_df is not None:
                        st.dataframe(parsed_df.reset_index(drop=True).rename(lambda x: x + 1, axis="index"), use_container_width=True)
                    else:
                        st.info("The response is likely a summary or natural language answer:")
                        st.write(result)

                # Store in chat history
                st.session_state.chat_history.append({
                    'user': query,
                    'assistant': result
                })
                save_chat_history(st.session_state.chat_history)


            except Exception as e:
                st.error(f"Error: {e}")
