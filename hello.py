import streamlit as st
import requests
from urllib.parse import urlparse
from pyhunter import PyHunter
import time

# API keys
SERPAPI_KEY = 'eb7f752229c6a385d08c6fffecbc1f357de474e6a97895dc2ff3746b45970f50'
HUNTER_API_KEY = 'b74a99a492b674e97821c3e952e7b757956a9738'  # Replace with your Hunter.io API key

# Configure Hunter.io API
hunter = PyHunter(HUNTER_API_KEY)

def search_shops(query, num_pages, api_key):
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

st.title("SearchX By Sam Jacka")

search_query = st.text_input("Enter search term")
num_pages = st.slider("Number of pages", 1, 20, 1)

if st.button("Search"):
    if search_query:
        api_key = SERPAPI_KEY
        results = search_shops(search_query, num_pages, api_key)
        
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
        st.write("Please enter a search term.")
