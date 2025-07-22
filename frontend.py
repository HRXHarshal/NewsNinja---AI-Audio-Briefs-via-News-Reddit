import streamlit as st
import requests
from typing import Literal
import base64 # Import base64 for encoding/decoding binary data (audio content)

# Constants
SOURCE_TYPES = Literal["news", "reddit", "both"]
BACKEND_URL = "http://localhost:1234"  # Define the URL of the FastAPI backend server

def main(): 
    # Set the title and a descriptive markdown header for the Streamlit app
    st.title("🥷 NewsNinja")
    st.markdown("#### 🎙️ News & Reddit Audio Summarizer")
   
    # Initialize session state variables if they don't already exist.
    # Session state persists data across reruns of the Streamlit app.
    if 'topics' not in st.session_state:
        st.session_state.topics = [] # List to store topics entered by the user
    if 'input_key' not in st.session_state:
        st.session_state.input_key = 0 # Key to manage unique text input widgets for topics
    if 'news_summary_text' not in st.session_state:
        st.session_state.news_summary_text = "" # Stores the generated text summary

    # Sidebar for application settings and instructions
    with st.sidebar:
        st.header("Settings") # Header for the settings section
        # Dropdown to select data sources (news, reddit, or both)
        source_type = st.selectbox(
            "Data Sources",
            options=["both", "news", "reddit"],
            # Custom format function to display options with emojis and capitalized text
            format_func=lambda x: f"🌐 {x.capitalize()}" if x == "news" else f"📑 {x.capitalize()}"
        )

        st.markdown("---") # Horizontal rule for visual separation
        st.header("How to Use") # Header for instructions
        # Markdown text providing step-by-step instructions for using the app
        st.markdown("""
        1.  **Select Data Sources:** Choose between 'News', 'Reddit', or 'Both' for your summary.
        2.  **Add Topic:** Enter a single topic (e.g., "Artificial Intelligence") and click 'Add'.
        3.  **Generate Summary:** Click 'Generate Summary' to get your audio and text briefing.
        4.  **Download & Read:** Listen to the audio summary or read the text output below.
        """)

    # Moved Features section to the main page for better visibility
    st.markdown("---") # Horizontal rule for visual separation
    st.header("Features") # Header for application features
    # Markdown text describing the key features of the NewsNinja app
    st.markdown("""
    -   **🌐 Multi-Source News Analysis:** Scrape and analyze news from Google News and Reddit discussions to get comprehensive coverage of any topic.
    -   **🎙️ AI-Powered Audio Generation:** Convert news summaries into high-quality audio using Murf AI's advanced text-to-speech technology with 99.38% pronunciation accuracy.
    -   **🤖 Smart Summarization:** Uses Google Gemini 2.0 Flash to create broadcast-quality news scripts from raw headlines and discussions.
    -   **📱 Instant Access:** Get your personalized news summary in both text and audio format within seconds.
    """)
    st.markdown("---") # Add a separator after features

    # Section for managing topics
    st.markdown("##### 📝 Topic Management") # Subheader for topic management
    col1, col2 = st.columns([4, 1]) # Create two columns for input field and add button
    with col1:
        # Text input field for entering new topics.
        # The key is dynamically generated to ensure the widget resets when a topic is added.
        new_topic = st.text_input(
            "Enter a topic to analyze",
            key=f"topic_input_{st.session_state.input_key}",
            placeholder="e.g. Artificial Intelligence"
        )
    with col2:
        # "Add" button for topics. It's disabled if 3 topics are already added.
        add_disabled = len(st.session_state.topics) >= 3
        if st.button("Add ➕", disabled=add_disabled):
            if new_topic.strip():
                st.session_state.topics.append(new_topic.strip()) # Add the new topic to the list
                st.session_state.input_key += 1 # Increment key to reset the text input field
                st.rerun() # Rerun the app to update the displayed topics

    # Display selected topics
    if st.session_state.topics: # Only show this section if there are topics
        st.subheader("✅ Selected Topics") # Subheader for selected topics
        # Iterate through the first 3 topics (as per the limit)
        for i, topic in enumerate(st.session_state.topics[:3]):
            cols = st.columns([4, 1]) # Create columns for topic display and remove button
            cols[0].write(f"{i+1}. {topic}") # Display the topic
            # "Remove" button for each topic
            if cols[1].button("Remove ❌", key=f"remove_{i}"):
                del st.session_state.topics[i] # Delete the topic from the list
                st.rerun() # Rerun the app to update the displayed topics

    # Analysis controls and output sections
    st.markdown("---") # Horizontal rule for visual separation
    st.subheader("🔊 Audio Generation") # Subheader for audio output
    st.subheader("📄 Text Summary") # Subheader for text summary output

    # "Generate Summary" button. Disabled if no topics are selected.
    if st.button("🚀 Generate Summary", disabled=len(st.session_state.topics) == 0):
        if not st.session_state.topics: # Check if topics list is empty
            st.error("Please add at least one topic") # Display error if no topics
        else:
            # Display a spinner while processing
            with st.spinner("🔍 Analyzing topics and generating audio..."):
                try:
                    # Make a POST request to the backend API
                    response = requests.post(
                        f"{BACKEND_URL}/generate-news-audio",
                        json={ # Send topics and source type as JSON payload
                            "topics": st.session_state.topics,
                            "source_type": source_type
                        }
                    )

                    if response.status_code == 200: # Check if the request was successful
                        st.session_state.news_summary_text = "" # Clear previous summary text
                        
                        # Parse the JSON response from the backend
                        response_data = response.json()
                        
                        # Decode the base64 encoded audio content
                        audio_bytes = base64.b64decode(response_data['audio_content'])
                        st.audio(audio_bytes, format="audio/mpeg") # Play the audio in Streamlit
                        
                        # Provide a download button for the audio file
                        st.download_button(
                            "Download Audio Summary",
                            data=audio_bytes, # Use decoded bytes for download
                            file_name="news-summary.mp3",
                            type="primary"
                        )
                        
                        # Store and display the text summary
                        st.session_state.news_summary_text = response_data['summary_text']

                    else:
                        # Call error handler if API request was not successful
                        handle_api_error(response)

                except requests.exceptions.ConnectionError:
                    # Handle connection errors (e.g., backend not running)
                    st.error("🔌 Connection Error: Could not reach the backend server")
                    st.session_state.news_summary_text = "Error: Could not connect to the backend server."
                except Exception as e:
                    # Catch any other unexpected errors
                    st.error(f"⚠️ Unexpected Error: {str(e)}")
                    st.session_state.news_summary_text = f"Error: {str(e)}"
    
    # Display the text summary section only if there is summary text available
    if st.session_state.news_summary_text:
        st.markdown("---") # Horizontal rule before the summary
        st.subheader("📄 Text Summary") # Subheader for the text summary
        # Display the text summary within a styled HTML div for better presentation
        st.markdown(
            f'<div style="background-color: #26272e; padding: 20px; border-radius: 10px; border: 1px solid #e0e2e6;">'
            f'<p style="font-family: \'Inter\', sans-serif; font-size: 16px; line-height: 1.6; color: #FAFAFA;">'
            f'{st.session_state.news_summary_text}'
            f'</p>'
            f'</div>',
            unsafe_allow_html=True # Allow rendering of custom HTML
        )

def handle_api_error(response):
    """
    Handles API error responses from the backend.
    This function attempts to parse error details from the JSON response.
    """
    try:
        # Attempt to get error detail from JSON response, default to "Unknown error"
        error_detail = response.json().get("detail", "Unknown error")
        st.error(f"API Error ({response.status_code}): {error_detail}") # Display error message
        st.session_state.news_summary_text = f"API Error ({response.status_code}): {error_detail}" # Store error in session state
    except ValueError:
        # If response is not valid JSON, display raw response text
        st.error(f"Unexpected API Response: {response.text}")
        st.session_state.news_summary_text = f"Unexpected API Response: {response.text}"

if __name__ == "__main__":
    main() # Run the main function when the script is executed