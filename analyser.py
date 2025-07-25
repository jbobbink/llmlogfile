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
        ip = extract_ip(line)
        url = extract_url(line)
        date = extract_date(line)
        if user_agent:
            log_entries.append({"raw": line, "user_agent": user_agent, "ip": ip, "url": url, "date": date})
    return pd.DataFrame(log_entries)

def extract_user_agent(log_line):
    matches = re.findall(r'"(.*?)"', log_line)
    if len(matches) >= 3:
        return matches[-1]  # user-agent is often the last quoted string
    return None

def extract_ip(log_line):
    match = re.match(r'^(\S+)', log_line)
    return match.group(1) if match else None

def extract_url(log_line):
    matches = re.findall(r'"(.*?)"', log_line)
    if len(matches) >= 1:
        request = matches[0]  # First quoted string usually contains GET /path HTTP/1.1
        parts = request.split()
        if len(parts) >= 2:
            return parts[1]  # The requested path (e.g., /wp-login.php)
    return None

def extract_date(log_line):
    match = re.search(r'\[(\d{2}/[A-Za-z]{3}/\d{4})', log_line)
    return match.group(1) if match else None

def detect_llm_bots(df):
    df['llm_name'] = df['user_agent'].apply(lambda ua: next((bot for bot in LLM_BOTS if bot.lower() in ua.lower()), None))
    df['llm_bot'] = df['llm_name'].notnull()
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

    st.dataframe(df_llm[['llm_name', 'user_agent', 'ip', 'url', 'date', 'raw']])

    st.subheader("Counts per LLM")
    st.dataframe(df_llm['llm_name'].value_counts().reset_index().rename(columns={'index': 'LLM Bot', 'llm_name': 'Count'}))

    st.subheader("Counts per Requested URL")
    llm_filter = st.selectbox("Filter by LLM Bot", options=["All"] + sorted(df_llm['llm_name'].unique()))
    if llm_filter != "All":
        filtered_df = df_llm[df_llm['llm_name'] == llm_filter]
    else:
        filtered_df = df_llm
    url_counts = filtered_df['url'].value_counts().reset_index().rename(columns={'index': 'URL', 'url': 'Count'})
    st.dataframe(url_counts)

    st.subheader("List of IPs per LLM")
    ip_per_llm = df_llm.groupby('llm_name')['ip'].unique().reset_index()
    ip_per_llm['ip'] = ip_per_llm['ip'].apply(lambda x: ', '.join(x))
    st.dataframe(ip_per_llm.rename(columns={'llm_name': 'LLM Bot', 'ip': 'IPs'}))

    st.subheader("Did any LLM request llms.txt?")
    llms_requests = df_llm[df_llm['url'].str.contains("llms.txt", case=False, na=False)]
    if not llms_requests.empty:
        st.success(f"{len(llms_requests)} LLM requests for 'llms.txt' detected:")
        st.dataframe(llms_requests[['llm_name', 'ip', 'url', 'date', 'user_agent']])
    else:
        st.info("No LLM requests for 'llms.txt' were detected.")

    st.subheader("Request Volume per Day")
    llm_filter_chart = st.selectbox("Filter chart by LLM Bot", options=["All"] + sorted(df_llm['llm_name'].unique()), key="chart_filter")
    if llm_filter_chart != "All":
        chart_df = df_llm[df_llm['llm_name'] == llm_filter_chart]
    else:
        chart_df = df_llm

    chart_df['date'] = pd.to_datetime(chart_df['date'], format='%d/%b/%Y', errors='coerce')
    daily_counts = chart_df.groupby('date').size().reset_index(name='Count').set_index('date')

    st.line_chart(daily_counts)

    csv = df_llm.to_csv(index=False).encode('utf-8')
    st.download_button("Download LLM Bot Entries as CSV", data=csv, file_name="llm_bot_hits.csv", mime="text/csv")
