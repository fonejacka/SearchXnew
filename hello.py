import streamlit as st
import requests
from urllib.parse import urlparse
from pyhunter import PyHunter
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

# Initialize session state
if 'excluded_domains' not in st.session_state:
    st.session_state.excluded_domains = load_excluded_domains()

if 'expander_open' not in st.session_state:
    st.session_state.expander_open = False

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
        confidences = []
        phones = set()
        company_description = "N/A"

        if response:
            if 'emails' in response:
                for email_data in response['emails']:
                    email = email_data['value']
                    confidence = email_data.get('confidence', 'N/A')
                    emails.append(email)
                    confidences.append(confidence)
                    if 'phone_number' in email_data and email_data['phone_number']:
                        phones.add(email_data['phone_number'])
            if 'organization' in response:
                company_description = response['organization']

        return emails, confidences, phones, company_description
    except Exception as e:
        st.write(f"Error fetching contact info from {domain}: {e}")
        return [], [], set(), "N/A"

def process_results(results):
    processed_results = []
    for result in results:
        domain = urlparse(result["link"]).netloc
        emails, confidences, phones, company_description = find_contact_info(domain)

        processed_results.append({
            "URL": result["link"],
            "Title": result.get("title", "N/A"),
            "Snippet": result.get("snippet", "N/A"),
            "Business Description": company_description,
            "Emails": emails,
            "Confidences": confidences,
            "Phones": ", ".join(phones) if phones else "No phones found"
        })
    return processed_results

def export_to_csv(results):
    flattened_results = []
    for result in results:
        emails = result.get('Emails', [])
        confidences = result.get('Confidences', [])
        if emails:
            for email, confidence in zip(emails, confidences):
                flattened_results.append({
                    "URL": result["URL"],
                    "Title": result.get("Title", "N/A"),
                    "Snippet": result.get("Snippet", "N/A"),
                    "Business Description": result.get("Business Description", "N/A"),
                    "Email": email,
                    "Confidence": confidence,
                    "Phones": result.get("Phones", "No phones found")
                })
        else:
            flattened_results.append({
                "URL": result["URL"],
                "Title": result.get("Title", "N/A"),
                "Snippet": result.get("Snippet", "N/A"),
                "Business Description": result.get("Business Description", "N/A"),
                "Email": "No emails found",
                "Confidence": "N/A",
                "Phones": result.get("Phones", "No phones found")
            })
    df = pd.DataFrame(flattened_results)
    csv = df.to_csv(index=False)
    return csv

# Custom CSS for the gray background and smaller delete button
st.markdown(
    """
    <style>
    .gray-background {
        background-color: #f0f0f0;
        padding: 10px;
        border-radius: 5px;
        margin-bottom: 10px;
    }
    .cross-button {
        color: red;
        font-weight: bold;
        cursor: pointer;
        font-size: 0.7em;
        padding: 2px 6px;
        margin-left: 5px;
        text-decoration: none;
    }
    .compact-list {
        display: flex;
        align-items: center;
        justify-content: space-between;
    }
    </style>
    """,
    unsafe_allow_html=True
)

# Display the meme GIF
st.image("https://media3.giphy.com/media/fSYmbgG5Ug8S11K0FU/giphy.gif?cid=6c09b952lpcceszzvqsykw8gnc980seejlsrvge593brd0yc&ep=v1_gifs_search&rid=giphy.gif&ct=g")

st.title("SearchX By Sam Jacka")

# Layout for search inputs
col1, col2 = st.columns(2)
with col1:
    search_query = st.text_input("Enter search term")
with col2:
    location = st.text_input("Enter location (optional)")

num_pages = st.slider("Number of pages", 1, 20, 1)

# Editable list for excluded domains inside an expander
with st.expander("Excluded Domains", expanded=st.session_state.expander_open):
    st.write("### Excluded Domains")
    for i, url in enumerate(st.session_state.excluded_domains):
        cols = st.columns([8, 2])
        with cols[0]:
            st.markdown(f"<div class='compact-list'><span>{url}</span></div>", unsafe_allow_html=True)
        with cols[1]:
            if st.button("❌", key=f"delete_{i}", help="Delete URL"):
                st.session_state.excluded_domains.pop(i)
                save_excluded_domains(st.session_state.excluded_domains)
                st.session_state.expander_open = True  # Keep the expander open
                st.rerun()  # Refresh the page to update the list

    # Add new URLs to the excluded domains list
    new_exclude_urls = st.text_area("Add new URLs to exclude (comma separated)")
    if st.button("Add URLs", key="add_exclude"):
        if new_exclude_urls:
            new_urls = [url.strip() for url in new_exclude_urls.split(",") if url.strip()]
            st.session_state.excluded_domains.extend(new_urls)
            save_excluded_domains(st.session_state.excluded_domains)
            st.session_state.expander_open = True  # Keep the expander open
            st.rerun()  # Refresh the page to update the list

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
    exclude_urls = st.session_state.excluded_domains
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
            st.write(f"**Phones:** {result.get('Phones', 'No phones found')}")
            st.write("**Emails and Confidences:**")
            emails = result.get('Emails', [])
            confidences = result.get('Confidences', [])
            if emails:
                for email, confidence in zip(emails, confidences):
                    st.write(f"{email} (Confidence: {confidence})")
            else:
                st.write("No emails found")
        progress_bar.progress(idx / len(st.session_state['processed_results']))

# Enable and update the export button
if st.session_state['processed_results']:
    csv = export_to_csv(st.session_state['processed_results'])
    export_button_container.download_button(
        label="Export to CSV",
        data=csv,
        file_name='search_results.csv',
        mime='text/csv'
    )
else:
    # Disable the export button when no results are available
    export_button_container.button("Export to CSV", disabled=True)
