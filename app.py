import os
import streamlit as st
import pandas as pd
from langchain_experimental.agents.agent_toolkits import create_csv_agent
from langchain_google_genai import ChatGoogleGenerativeAI
import tempfile

# Set up Google API Key
os.environ["GOOGLE_API_KEY"] = "AIzaSyDIYgJ01me6YE6yAzaJkyeZx3jHGxWKAR0"

# os.environ["GOOGLE_API_KEY"] = st.secrets["GOOGLE_API_KEY"]


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
    llm = ChatGoogleGenerativeAI(model="gemma-3-27b-it")

    # Create agents
    main_agent = create_csv_agent(llm, temp_main.name, verbose=False, allow_dangerous_code=True)
    comments_agent = None
    if not df_comments.empty:
        comments_agent = create_csv_agent(llm, temp_comments.name, verbose=False, allow_dangerous_code=True)

    return main_agent, comments_agent


def handle_user_query(query, main_agent, comments_agent):
    final_query = get_enriched_prompt(query)
    if 'comment' in query.lower() or 'feedback' in query.lower():
        if comments_agent:
            return comments_agent.run(final_query)
        else:
            return "No comments data available in the uploaded file."
    else:
        return main_agent.run(final_query)

# ---------- Streamlit UI ----------
st.title("📊 Excel Q&A Agent with Comments Support")

uploaded_file = st.file_uploader("Upload an Excel file", type=["xlsx"])

if uploaded_file:
    st.success("File uploaded successfully!")

    # Cache agents in session_state
    if 'main_agent' not in st.session_state:
        with st.spinner("Setting up the agent..."):
            try:
                main_agent, comments_agent = create_agents(uploaded_file)
                st.session_state['main_agent'] = main_agent
                st.session_state['comments_agent'] = comments_agent
            except Exception as e:
                st.error(f"Agent setup failed: {e}")
                st.stop()
    else:
        main_agent = st.session_state['main_agent']
        comments_agent = st.session_state['comments_agent']

    # Accept user query
    query = st.text_input("Enter your question about the data:")

    if query:
        with st.spinner("Processing your query..."):
            try:
                result = handle_user_query(query, main_agent, comments_agent)
                st.write("### Response:")

                # Try to parse result into a DataFrame
                try:
                    from io import StringIO
                    result_df = pd.read_csv(StringIO(result))
                    st.dataframe(result_df, use_container_width=True)
                except Exception:
                    st.write(result)

            except Exception as e:
                st.error(f"Error: {e}")
