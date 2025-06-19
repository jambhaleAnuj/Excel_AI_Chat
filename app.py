import os
import streamlit as st
import pandas as pd
from langchain_experimental.agents.agent_toolkits import create_csv_agent
from langchain_google_genai import ChatGoogleGenerativeAI
import tempfile
from io import StringIO
import re

# Set up Google API Key
os.environ["GOOGLE_API_KEY"] = "AIzaSyDIYgJ01me6YE6yAzaJkyeZx3jHGxWKAR0"

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
    csv_keywords = ["list", "show", "filter", "table", "display", "all employees", "summary of", "csv"]

    if any(kw in query_lower for kw in csv_keywords):
        context = (
            "You are a data analyst with access to a dataset. "
            "For this query, return the results in CSV format with headers. "
            "Ensure exact match filtering where possible by converting both dataset values and user inputs to lowercase and trimming whitespace."
        )
    else:
        context = (
            "You are a data analyst with access to a dataset. "
            "Respond to the user's query in natural language. "
            "Only use CSV format if the user explicitly asks for tabular or structured output."
        )

    return f"{context}\n\nUser Query: {query}"



def create_agents(excel_file):
    df = pd.read_excel(excel_file, dtype=str)

    # Strip leading/trailing whitespaces from all string cells
    df = df.applymap(lambda x: x.strip().lower() if isinstance(x, str) else x)

    # Create temporary CSVs
    temp_main = tempfile.NamedTemporaryFile(delete=False, suffix=".csv")
    temp_comments = tempfile.NamedTemporaryFile(delete=False, suffix=".csv")

    df_main = df.drop(columns=['Comments'], errors='ignore')
    df_comments = df[['Employee Name', 'Comments']] if 'Comments' in df.columns else pd.DataFrame()

    df_main.to_csv(temp_main.name, index=False)
    if not df_comments.empty:
        df_comments.to_csv(temp_comments.name, index=False)

    # Initialize LLM
    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash-preview-05-20",temperature=0.5)

    # Create agents
    main_agent = create_csv_agent(
        llm, temp_main.name, verbose=False, allow_dangerous_code=True, handle_parsing_errors=True
    )
    comments_agent = None
    if not df_comments.empty:
        comments_agent = create_csv_agent(
            llm, temp_comments.name, verbose=False, allow_dangerous_code=True, handle_parsing_errors=True
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


def try_parse_csv(text):
    try:
        # Try reading entire response as CSV
        df = pd.read_csv(StringIO(text))
        if df.shape[1] > 1:
            return df
    except Exception:
        pass

    # Try extracting a CSV block
    csv_block = re.search(r"((?:[^\n]*,)+[^\n]*\n(?:.*\n?)+)", text)
    if csv_block:
        try:
            df = pd.read_csv(StringIO(csv_block.group(1)))
            if df.shape[1] > 1:
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
st.title("📊 Excel Q&A Agent with Comments Support")

# Initialize chat history
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

# Sidebar for chat history
with st.sidebar:
    st.header("💬 Chat History")
    for i, chat in enumerate(st.session_state.chat_history):
        with st.expander(f"Q{i+1}: {chat['user'][:30]}..."):
            st.markdown(f"**User:** {chat['user']}")
            st.markdown(f"**Assistant:** {chat['assistant']}")

    if st.sidebar.button("🗑️ Clear Chat History"):
        st.session_state.chat_history = []

uploaded_file = st.file_uploader("Upload an Excel file", type=["xlsx"])

if uploaded_file:
    st.success("File uploaded successfully!")

    query = st.chat_input("Enter your question about the data:")

    if query:
        st.chat_message("user").write(query)
        with st.spinner("Processing your query..."):
            try:
                # main_agent, comments_agent = create_agents(uploaded_file)
                # result = handle_user_query(query, main_agent, comments_agent)
                # st.write("### Response:")
                main_agent, comments_agent = create_agents(uploaded_file)
                response = handle_user_query(query, main_agent, comments_agent)
                result = clean_llm_output(response["result"])
                is_structured = response["is_structured"]

                # Try parsing CSV
                parsed_df = try_parse_csv(result)

                if parsed_df is not None:
                    st.dataframe(parsed_df, use_container_width=True)
                else:
                    st.info("The response is likely a summary or natural language answer:")
                    st.chat_message("assistant").write(result)

                # Store in chat history
                st.session_state.chat_history.append({
                    'user': query,
                    'assistant': result
                })

            except Exception as e:
                st.error(f"Error: {e}")
