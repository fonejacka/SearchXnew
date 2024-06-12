import streamlit as st
import requests
from urllib.parse import urlparse
from pyhunter import PyHunter
import time
import json
import os
import pandas as pd

# API keys
SERPAPI_KEY = 'eb7f752229c6a385d08c6fffecbc1f357de474e6a97895dc2ff3746b45970f50'
HUNTER_API_KEY = 'b74a99a492b674e97821c3e952e7b757956a9738'  # Replace with your Hunter.io API key

# Configure Hunter.io API
hunter = PyHunter(HUNTER_API_KEY)

# Load excluded domains from JSON file
def load_excluded_domains(file_path='excluded_domains.json'):
    if os.path.exists(file_path):
        with open(file_path, 'r') as file:
            data = json.load(file)
            return data.get('excluded_domains', [])
    return []

# Save excluded domains to JSON file
def save_excluded_domains(excluded_domains, file_path='excluded_domains.json'):
    data = {'excluded_domains': excluded_domains}
    with open(file_path, 'w') as file:
        json.dump(data, file, indent=4)

def search_shops(query, num_pages, api_key, exclude_urls):
    results = []
    for page in range(num_pages):
        params = {
            "engine": "google",
            "q": query,
            "start": page * 10,
            "api_key": api_key
        }
        try:
            response = requests.get("https://serpapi.com/search", params=params, timeout=10).json()
        except Exception as e:
            st.write(f"Error fetching search results: {e}")
            continue

        if "organic_results" in response:
            for result in response["organic_results"]:
                if all(exclude_url not in result["link"] for exclude_url in exclude_urls):
                    results.append(result)
        else:
            st.write(f"No organic results found on page {page + 1}")

    return results

def find_contact_info(domain):
    try:
        response = hunter.domain_search(domain)

        emails = []
        phones = set()
        company_description = "N/A"

        if response:
            if 'emails' in response:
                for email_data in response['emails']:
                    email = email_data['value']
                    confidence = email_data.get('confidence', 'N/A')
                    emails.append((email, confidence))
                    if 'phone_number' in email_data and email_data['phone_number']:
                        phones.add(email_data['phone_number'])
            if 'organization' in response:
                company_description = response['organization']

        return emails, phones, company_description
    except Exception as e:
        st.write(f"Error fetching contact info from {domain}: {e}")
        return [], set(), "N/A"

def process_results(results):
    processed_results = []
    for result in results:
        domain = urlparse(result["link"]).netloc
        emails, phones, company_description = find_contact_info(domain)

        email_str = ", ".join([f"{email} (Confidence: {confidence})" for email, confidence in emails]) if emails else "No emails found"
        phone_str = ", ".join(phones) if phones else "No phones found"

        processed_results.append({
            "URL": result["link"],
            "Title": result.get("title", "N/A"),
            "Snippet": result.get("snippet", "N/A"),
            "Business Description": company_description,
            "Emails": email_str,
            "Phones": phone_str,
            "Emails_List": emails  # Keep the original emails list for filtering
        })
    return processed_results

def export_to_csv(results, only_with_email):
    data = []
    for result in results:
        emails = result.get('Emails_List', [])
        if only_with_email and not emails:
            continue
        email_str = result.get('Emails', "No emails found")
        phone_str = result.get('Phones', "No phones found")
        data.append({
            "URL": result["URL"],
            "Title": result.get("Title", "N/A"),
            "Snippet": result.get("Snippet", "N/A"),
            "Business Description": result.get("Business Description", "N/A"),
            "Emails": email_str,
            "Phones": phone_str
        })
    df = pd.DataFrame(data)
    csv = df.to_csv(index=False)
    return csv

# Custom CSS for the gray background
st.markdown(
    """
    <style>
    .gray-background {
        background-color: #f0f0f0;
        padding: 10px;
        border-radius: 5px;
        margin-bottom: 10px;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# Display the meme GIF
st.image("https://media2.giphy.com/media/gtzIP3mpbzh16/giphy.gif?cid=6c09b952dbea939fpaegqg1qw5g37wlrlqkklpkz1zrkf9qa&ep=v1_gifs_search&rid=giphy.gif&ct=g")

st.title("SearchX By Sam Jacka")

# Layout for search inputs
col1, col2 = st.columns(2)
with col1:
    search_query = st.text_input("Enter search term")
with col2:
    location = st.text_input("Enter location (optional)")

num_pages = st.slider("Number of pages", 1, 20, 1)

# Load existing excluded domains
excluded_domains = load_excluded_domains()

exclude_urls_input = st.text_area("Enter URLs to exclude (comma separated)", value=", ".join(excluded_domains))

if st.button("Add to Excluded Domains", key="add_excluded"):
    new_excludes = [url.strip() for url in exclude_urls_input.split(",") if url.strip()]
    # Update the excluded domains list and save to file
    excluded_domains = list(set(excluded_domains + new_excludes))
    save_excluded_domains(excluded_domains)
    st.success("Excluded domains updated and saved.")

# Container for the export button and checkbox with gray background
with st.container():
    st.markdown('<div class="gray-background">', unsafe_allow_html=True)
    export_col1, export_col2 = st.columns([2, 1])
    with export_col1:
        only_with_email = st.checkbox("Only export results with an email", key="export_filter")
    with export_col2:
        export_button_container = st.empty()
    st.markdown('</div>', unsafe_allow_html=True)

# Ensure search results are preserved
if 'results' not in st.session_state:
    st.session_state['results'] = []
if 'processed_results' not in st.session_state:
    st.session_state['processed_results'] = []

search_button_clicked = st.button("Search", key="search_button")
if search_button_clicked and search_query:
    exclude_urls = excluded_domains
    api_key = SERPAPI_KEY
    full_query = f"{search_query} {location}" if location else search_query
    results = search_shops(full_query, num_pages, api_key, exclude_urls)
    st.session_state['results'] = results  # Store results in session state
    st.session_state['processed_results'] = process_results(results)  # Store processed results in session state

if st.session_state['processed_results']:
    st.write("### Search Results")
    progress_bar = st.progress(0)
    for idx, result in enumerate(st.session_state['processed_results'], 1):
        domain = urlparse(result["URL"]).netloc
        with st.expander(f"{idx}. {domain} - {result['URL']}", expanded=True):
            st.write(f"**URL:** {result['URL']}")
            st.write(f"**Title:** {result.get('Title', 'N/A')}")
            st.write(f"**Snippet:** {result.get('Snippet', 'N/A')}")
            st.write(f"**Business Description:** {result.get('Business Description', 'N/A')}")
            st.write(f"**Emails:** {result.get('Emails', 'No emails found')}")
            st.write(f"**Phones:** {result.get('Phones', 'No phones found')}")
        progress_bar.progress(idx / len(st.session_state['processed_results']))

# Enable and update the export button
if st.session_state['processed_results']:
    csv = export_to_csv(st.session_state['processed_results'], only_with_email)
    export_button_container.download_button(
        label="Export to CSV",
        data=csv,
        file_name='search_results.csv',
        mime='text/csv'
    )
else:
    # Disable the export button when no results are available
    export_button_container.button("Export to CSV", disabled=True)