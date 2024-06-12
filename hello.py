import streamlit as st
import requests
from urllib.parse import urlparse
from pyhunter import PyHunter
import time
import json
import os

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

def search_shops(query, location, num_pages, api_key, exclude_urls):
    results = []
    for page in range(num_pages):
        params = {
            "engine": "google",
            "q": query,
            "location": location,
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
                    results.append(result["link"])
        else:
            st.write(f"No organic results found on page {page + 1}")

    return results

def find_contact_info(domain):
    try:
        st.write(f"Fetching contact info from {domain}")

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

# Display the meme GIF
st.image("https://media2.giphy.com/media/gtzIP3mpbzh16/giphy.gif?cid=6c09b952dbea939fpaegqg1qw5g37wlrlqkklpkz1zrkf9qa&ep=v1_gifs_search&rid=giphy.gif&ct=g")

st.title("SearchX By Sam Jacka")

search_query = st.text_input("Enter search term")
location = st.text_input("Enter location (e.g., United States, Ohio)")
num_pages = st.slider("Number of pages", 1, 20, 1)

# Load existing excluded domains
excluded_domains = load_excluded_domains()

exclude_urls_input = st.text_area("Enter URLs to exclude (comma separated)", value=", ".join(excluded_domains))

if st.button("Add to Excluded Domains"):
    new_excludes = [url.strip() for url in exclude_urls_input.split(",") if url.strip()]
    # Update the excluded domains list and save to file
    excluded_domains = list(set(excluded_domains + new_excludes))
    save_excluded_domains(excluded_domains)
    st.success("Excluded domains updated and saved.")

if st.button("Search"):
    if search_query and location:
        exclude_urls = excluded_domains
        api_key = SERPAPI_KEY
        results = search_shops(search_query, location, num_pages, api_key, exclude_urls)

        if results:
            st.write("### Search Results")
            progress_bar = st.progress(0)
            progress_text = st.empty()
            progress_text.text("Getting SearchX lead information...")

            for idx, result in enumerate(results, 1):
                try:
                    domain = urlparse(result).netloc
                    emails, phones, company_description = find_contact_info(domain)

                    email_str = ", ".join([f"{email} (Confidence: {confidence})" for email, confidence in emails]) if emails else "No emails found"
                    phone_str = ", ".join(phones) if phones else "No phones found"

                    with st.expander(f"{idx}. {domain} - {result}", expanded=True):
                        st.write(f"**URL:** {result}")
                        st.write(f"**Business Description:** {company_description}")
                        st.write(f"**Emails:** {email_str}")
                        st.write(f"**Phones:** {phone_str}")

                    progress_bar.progress(idx / len(results))
                    time.sleep(1)  # Add delay to simulate processing time

                except Exception as e:
                    st.write(f"Error processing {result}: {e}")
                    continue

            progress_text.text("Lead information retrieval complete.")
    else:
        st.write("Please enter a search term and location.")
