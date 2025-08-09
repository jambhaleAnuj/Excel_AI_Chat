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

# Set up Google API Key (from env or Streamlit secrets)
api_key = st.secrets.get("GOOGLE_API_KEY", os.getenv("GOOGLE_API_KEY"))
if not api_key:
    st.error("Google API key missing. Set GOOGLE_API_KEY in environment or .streamlit/secrets.toml")
    st.stop()
os.environ["GOOGLE_API_KEY"] = api_key

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


    # Explicit column-to-values mapping (custom guide for disambiguation)
    column_value_guide = {
    "Resource Pool": [
        "JavaScript", "CSS", "QA", "Java", "Project Management", "Finance", "Ruby",
        "Management", "IT", "QA-Auto", "QA-Manual", "Graphics", "ADMIN", "Microsoft",
        "Sales & Mkting", ".Net", "Angular", "Mobile", "HR", "Recruitment", "BA",
        "Purchase", "PHP", "Footage Review", "Image Review", "Stock Photography",
        "Image Moderation", "Video Editing", "Salesforce", "FrontEnd", "Front End Website Developer",
        "Research", "SEO-SEM-SMM", "Content", "MIS", "Content Writing", "Writing",
        "Data Enrichment", "iOS development", "React JS", "Marketing", "Workday",
        "Training", "Android", "Cloud Computing", "Design", "UI/UX", "Python",
        "SQL,DB", "Mongo DB", "RPA", "HR-MIS", "Gurmukhi script", "DevOps", ".Netcore",
        "L&D", "Shopify Platform", "Testing", "UI", "RMG", "QA Lead",
        "Resource Management and Bench Management", "UI/UX Design", "LAN/WAN", "Analyst",
        "System Admin", "Technical Scale", "Databricks", "Snowflake", "ROR",
        "Marketing Cloud", "Compliance Reviewer", "Salesforce CRM", "AWS",
        "Team Management", "Azure DevOps", "Service Cloud", "AWS Cloud Support",
        "HTML/CSS", "AWS Salesforce", "Azure and Gen AI", "Account Management",
        "Site Auditor", "PostgreSQL", "Data Engineering", "Salesforce Support",
        "Katalon Automation Engineer", "Accounting", "Fullstack", "Business Development",
        "Chartered Accountant", "Automation engineer", "Business Analyst",
        "Power automate", "Mulesoft", "Tamil Writer", "Mobile Development",
        "Bhojpuri Writer"
    ],
    "Primary Skills": [
        "Vue JS", "css 3", "QA-MANUAL", "Api testing", "Java", "Ruby/Rails",
        "Accounting - Quickbooks", "nodejs", "UI/UX", "Team Management", "O365 Administration",
        "QA-AUTO", "Administration", "ExpressJs", "sketch", "Admin Backend Support",
        "microsoft", ".Net", ".Net Core", "Salesforce", "Project Management",
        "Delivery Leadership", "Software Testing", "Android", "HR Management",
        "Recruitment", "Business Analysis", "Angular", "Angular 16", "Purchase",
        "excel", "functional testing", "css", "React JS", "javascript", "AWS",
        "html5/css3", "ITIL", "Accounting - Tally", "Asset Management", "Admin Front Desk",
        "photoshop", "PHP", "video reviewing", "image reviewing", "video editing",
        "APEX development - Salesforce", "hmtl5", "CPQ", "Firewall Administration",
        "Typescript", "Marketing", "image editing", "Film Making", "Angular 8.0",
        "Digital Marketing", "Networking", "manual testing", "Lightning Components",
        "Marketing cloud", "Data Science", "Branding", "Copywriter", "Design",
        "Data Enrichment", "data entry", "Datorama", "Salesforce Administrator",
        "Salesforce DevOps (CD/CI)", "bootstrap 3", "Customer Support-Email",
        "Workday", "xml", "ASP.NET", "Salesforce- Marketing cloud", "core java",
        "Python", "amazon web services", "Monitoring", "ElasticSearch",
        "Technical Troubleshooting", "Program Management", "Cloud", "Lightning Web Components",
        "Sales Cloud", "Content writing", "GCP", "Java Spring Boot", "SQL",
        "Graphics Design", "Customer Success", "MongoDB", "Automation-Playwright Test",
        "UiPath", "Script Writing", "Gurmukhi script", "Resource Management and Bench Management",
        "React", "MIS", "L&D", "Resource Management", "Shopify Platform", "Onboarding",
        "Data Engineering", "Active Directory", "Kafka", "Sales", "Email Campaign",
        "Spring Boot", "Java 8", "GitHub", "Research and Curation", "Performance Testing",
        "image reviewing; image reviewing", "Ansible", "Desktop Support", "Business & Function",
        "Production support", "Power BI", "Customer Support", "Postgres", "HTML/CSS",
        "Salesforce Developer", "Chartered Accountant", "BRD", "Power Automate", "selenium",
        "mule", "Photography", "Kotlin"
    ],
    "Employment Status": [
        "3rd Party Contract", "Confirmed", "Probation", "On Notice",
        "Probation Extended", "Direct Contract"
    ],
    "Project Name": [
        "0339-Rev-CCMH-Proj-CCMH", "0359-Rev-Parkofon-Proj-Sheeva-ai", "0328-Rev-AboveBoard-Proj-AboveBoard",
        "0241-Rev-Vet24seven-PROJ-Vet24seven", "5501-Inv-V2Solutions-Proj-Digital Engineering Bench",
        "0249-Rev-Specialty Inspection-Proj-Specialty", "6003-Inv-V2Solutions-OPS-Finance",
        "0220-Rev-Shoulet Blunt-Proj-Imago", "5401-Inv-V2Solutions-Proj-Digital Experience Bench",
        "6001-Inv-V2Solutions-OPS-Corporate", "0408-Rev-Imdex-Proj-Imdex", "0366-Rev-Natural Retreats-Proj-Natural Retreats",
        "6005-Inv-V2Solutions-OPS-IT", "0405-Rev-Entelect-Proj-Entelect", "0196-Rev-Shutterstock-Proj-Shutterstock",
        "0390-Rev-Pension Technology-Proj-Pension Technology", "6001-Inv-V2Solutions-OPS-Corporate-US",
        "6007-Inv-V2Solutions-OPS-Admin & Purchase", "0339-Rev-CCMH-Proj-CCMH-US", "7121-Inv-V2Solutions-Proj-Sales-US",
        "7201-Inv-V2Solutions-Proj-S&I-US", "7111-Inv-V2Solutions-Proj-Others AM-US", "5703-Inv-V2Solutions-Proj-Salesforce S&M - US",
        "5519-Inv-V2Solutions-Proj-Digital Engineering VWR Rewrite", "0231-Rev-Adobe-Proj-Backlog Review",
        "0231-Rev-Adobe-Proj-Site Audit", "0336-Rev-ThriveTRM-Proj-ThriveTRM", "6002-Inv-V2Solutions-OPS-BU-HR",
        "6002-Inv-V2Solutions-OPS-TAG", "0185-Rev-LendingTree-Proj-LendingTree", "0407-Rev-HealthEdge-Proj-HealthEdge",
        "0398-Rev-Sunnova-Proj-Sunnova", "6011-Inv-V2Solutions-OPS-Inventory", "0404-Rev-Vendelux-Proj-Vendelux",
        "5703-Inv-V2Solutions-Proj-Salesforce S&M", "0327-Rev-Rubrik-Proj-Rubrik", "5702-Inv-V2Solutions-Proj-Digital Platform Competency Building",
        "0263-Rev-Kyra Solutions -Proj-Kyra Transportation MVP", "0334-Rev-Realm-Proj-Realm", "5706-Inv-V2Solutions-Proj-Digital Platform Internal Project",
        "5701-Inv-V2Solutions-Proj-Digital Platform Bench", "0403-Rev-We Insure-Proj-We Insure", "0361-Rev-Pacaso-Proj-Pacaso",
        "0263-Rev-Kyra Solutions -Proj-Kyra", "0315-Rev-LuminaDatamatics-Proj-LuminaDatamatics", "5405-Inv-V2Solutions-Proj-DCT Tool",
        "7152-Inv-V2Solutions-Proj-Marketing", "0275-Rev-RentalBeast-Proj-Content Service-Research & Sourcing", "3007-Rev-FNS-Proj-V2Solutions",
        "0348-Rev-ValleyROP-Proj-ValleyROP", "0399-Rev-Implentio-Proj-Implentio", "0354-Rev-Twitch-Proj-Twitch",
        "0401-Rev-Fieldist-Proj-Fieldist", "0275-Rev-RentalBeast-Proj-RentalBeast", "7123-Inv-V2Solutions-Proj-Inside Sales",
        "5201-Inv-V2Solutions-Proj-Content Service Bench", "0309-Rev-LyricFind-Proj-LyricFind", "5517-Inv-V2Solutions-Proj-Digital Engineering Internal Project VWR",
        "0213-Rev-iSpot_Drmetrix-Proj-DRmetrix - Phase II", "0320-Rev-GroupBy-Proj-GroupBy DEngg", "0351-Rev-Right Skale-Proj-Bespin",
        "0351-Rev-Right Skale-Proj-Pure Storage", "0196-Rev-Shutterstock-Proj-Sales Process Documentation", "7112-Inv-V2Solutions-Proj-Others AM",
        "7125-Inv-V2Solutions-Proj-Enterprise Sales", "7120-Inv-V2Solutions-Proj-Sales", "0362-Rev-First National Bank-Proj-FNB",
        "0362-Rev-First National Bank-Proj-FNB-US", "7151-Inv-V2Solutions-Proj-Marketing-US", "0402-Rev-Auro Wellness-Proj-Auro Wellness",
        "0365-Rev-JustCall-Proj-JustCall", "0203-Rev-Avail-Proj-Avail", "0397-Rev-Monday.Com-Proj-Monday.Com",
        "0394-Rev-Rev.Com-Proj-Rev.Com", "0270-Rev-HealthCare-Solutions-Proj-HCS", "0217-Rev-CureMD-Proj-CureMD",
        "0325-Rev-Kin Insurance-Proj-Kin Insurance", "0369-Rev-Otter.ai-Proj-Otter.ai", "6002-Inv-V2Solutions-OPS-TAG-US"
    ],
    "Availability Status": [
        "Available for billing", "Mapped for future billing opportunity", "Not Available for billing", "Management"
    ],
    "Billable Status": [
        "Billable", "Non Billable"
    ],
    "Employment Type": [
        "Contractor", "FTE"
    ],
    "Sub Practice Area": [
        "Salesforce S&M", "Digital Engineering", "Digital Platform", "Inside Sales", "Salesforce S&M - US",
        "Digital Platform Competency Building", "Digital Platform Internal Project", "Enterprise Sales", "Sales",
        "Others AM", "Marketing", "Digital Engineering Bench", "Digital Experience Bench", "Content Service Bench",
        "Salesforce Support"
    ],
    "Business Unit": [
        "V2Solutions", "Digital Platform", "Sales & Marketing"
    ]
}


    # Convert mapping to string
    guide_lines = ["**Column-to-Value Reference (for disambiguation):**"]
    for col, values in column_value_guide.items():
        values_str = ", ".join(values)
        guide_lines.append(f"- {col}: {values_str}")
    guide_text = "\n".join(guide_lines)

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
        f"{guide_text}\n\n"

        )
    else:
        context = (
            "You are a data analyst with access to a dataset. "
            "Respond to the user's query in natural language. "
            "If My Query asks for comment.**return the full comment exactly as it appears in the data without any truncation or summarization.**. Do not add your own explanation. Just return the full comment."
            "Ensure exact match filtering where possible by converting both dataset values and user inputs to lowercase and trimming whitespace."
            "Only use CSV format if the user explicitly asks for tabular or structured output."
            f"{guide_text}\n\n"

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
