import os
import streamlit as st
import pandas as pd
from langchain_experimental.agents.agent_toolkits import create_csv_agent
from langchain_google_genai import ChatGoogleGenerativeAI
import tempfile

# Set up Google API Key
os.environ["GOOGLE_API_KEY"] = "AIzaSyDIYgJ01me6YE6yAzaJkyeZx3jHGxWKAR0"

# Define helper functions
def get_enriched_prompt(query):

    context = (
        "You are a data analyst with access to a dataset. "
        "If the query involves listing or filtering data (like finding details about a person), "
        "perform an exact match by converting both the dataset and the input to lowercase and removing extra spaces. "
        "If the query is asking for structured data, respond in CSV format with headers. "
        "For summaries, use natural language."
    )
    return f"{context}\n\nUser Query: {query}"

# def create_agents(excel_file):
#     df = pd.read_excel(excel_file, dtype=str)

#     # Create temporary CSVs
#     temp_main = tempfile.NamedTemporaryFile(delete=False, suffix=".csv")
#     temp_comments = tempfile.NamedTemporaryFile(delete=False, suffix=".csv")

#     df_main = df.drop(columns=['Comments'], errors='ignore')
#     df_comments = df[['Employee Name', 'Comments']] if 'Comments' in df.columns else pd.DataFrame()

#     df_main.to_csv(temp_main.name, index=False)
#     if not df_comments.empty:
#         df_comments.to_csv(temp_comments.name, index=False)

#     # Initialize LLM
#     llm = ChatGoogleGenerativeAI(model="gemma-3-27b-it")

#     # Create agents
#     main_agent = create_csv_agent(llm, temp_main.name, verbose=False, allow_dangerous_code=True)
#     comments_agent = None
#     if not df_comments.empty:
#         comments_agent = create_csv_agent(llm, temp_comments.name, verbose=False, allow_dangerous_code=True)

#     return main_agent, comments_agent


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
    # llm = ChatGoogleGenerativeAI(model="gemma-3-27b-it")
    llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash-preview-05-20")


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
#     if 'comment' in query.lower() or 'feedback' in query.lower():
#         if comments_agent:
#             return comments_agent.run(final_query)
#         else:
#             return "No comments data available in the uploaded file."
#     else:
#         return main_agent.run(final_query)

def handle_user_query(query, main_agent, comments_agent):
    final_query = get_enriched_prompt(query)
    agent = comments_agent if ('comment' in query.lower() or 'feedback' in query.lower()) else main_agent

    try:
        return agent.run(final_query)
    except ValueError as e:
        error_text = str(e)
        if "Could not parse LLM output:" in error_text:
            summary = error_text.split("Could not parse LLM output:", 1)[-1].strip()
            return f"[Summary Fallback] {summary}"
        else:
            raise e  # Let Streamlit handle it


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
                main_agent, comments_agent = create_agents(uploaded_file)
                result = handle_user_query(query, main_agent, comments_agent)
                st.write("### Response:")

                # Check for output parsing error and extract summary if present
                parsing_error_prefix = "Could not parse LLM output: "
                if isinstance(result, str) and parsing_error_prefix in result:
                    # Extract everything after the error prefix
                    summary = result.split(parsing_error_prefix, 1)[-1].strip()
                    st.info("The assistant provided a summary instead of a table. Displaying summary below:")
                    st.write(summary)
                else:
                    if result.strip().count('\n') < 3 or ',' not in result:
                        st.info("The response is likely a summary or natural language answer:")
                        st.write(result)
                    else:
                    # Try to parse result into a DataFrame if possible
                        from io import StringIO
                        import re
                        parsed = False
                        csv_match = re.search(r"^(.*\n)?([\w\s,]+\n([\w\s,.-]+\n)+)", result, re.MULTILINE)
                        if csv_match:
                            try:
                                result_df = pd.read_csv(StringIO(csv_match.group(2)))
                                st.dataframe(result_df, use_container_width=True)
                                parsed = True
                                before = result[:csv_match.start(2)].strip()
                                after = result[csv_match.end(2):].strip()
                                if before:
                                    st.write(before)
                                if after:
                                    st.write(after)
                            except Exception:
                                pass
                        if not parsed:
                            st.write(result)

                    # Append to chat history
                    st.session_state.chat_history.append({
                        'user': query,
                        'assistant': result
                    })

            except Exception as e:
                st.error(f"Error: {e}")
