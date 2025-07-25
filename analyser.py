import streamlit as st
import pandas as pd
import re
from io import StringIO, BytesIO
import gzip

# List of known LLM bots (extendable)
LLM_BOTS = [
    'ChatGPT-User', 'GPTBot', 'ClaudeBot', 'Google-Extended', 'CCBot', 'facebookexternalhit',
    'Anthropic', 'AI21', 'Bard', 'OpenAI', 'PerplexityBot', 'youchat', 'cohere', 'mistral',
    'Sogou web spider', 'Bytespider', 'Amazonbot'
]

@st.cache_data
def parse_log_file(uploaded_file):
    if uploaded_file.name.endswith(".gz"):
        with gzip.open(uploaded_file, 'rt', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
    else:
        stringio = StringIO(uploaded_file.getvalue().decode("utf-8", errors='ignore'))
        lines = stringio.readlines()
    
    log_entries = []
    for line in lines:
        user_agent = extract_user_agent(line)
        if user_agent:
            log_entries.append({"raw": line, "user_agent": user_agent})
    return pd.DataFrame(log_entries)


def extract_user_agent(log_line):
    matches = re.findall(r'"(.*?)"', log_line)
    if len(matches) >= 3:
        return matches[-1]  # user-agent is often the last quoted string
    return None


def detect_llm_bots(df):
    df['llm_bot'] = df['user_agent'].apply(lambda ua: any(bot.lower() in ua.lower() for bot in LLM_BOTS))
    return df[df['llm_bot'] == True]


# Streamlit UI
st.title("LLM Bot Log Analyzer")

uploaded_file = st.file_uploader("Upload a server log file (.log or .gz)", type=["log", "gz"])

if uploaded_file:
    st.write("Parsing log file...")
    df_logs = parse_log_file(uploaded_file)
    st.success(f"Parsed {len(df_logs)} log lines.")

    df_llm = detect_llm_bots(df_logs)
    st.write(f"Found {len(df_llm)} entries from known LLM bots.")

    st.dataframe(df_llm[['user_agent', 'raw']])

    csv = df_llm.to_csv(index=False).encode('utf-8')
    st.download_button("Download LLM Bot Entries as CSV", data=csv, file_name="llm_bot_hits.csv", mime="text/csv")
