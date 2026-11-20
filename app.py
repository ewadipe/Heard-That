import os
import html
from dotenv import load_dotenv


import requests
import streamlit as st
load_dotenv()
# This code does 4 things: asks for live markets, listens to rumors, matches to a rumor, and shows the results

# some more design stuff
st.set_page_config(
    page_title="Heard That!",
    page_icon="🏈",
    layout="wide"
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap');

.stApp {
    background: #0B0F19;
    color: #F9FAFB;
    font-family: 'Inter', sans-serif;
}

.block-container {
    max-width: 1150px;
    padding-top: 2rem;
    padding-bottom: 4rem;
}

/* Hide the default Streamlit menu and footer */
#MainMenu, footer {
    visibility: hidden;
}

/* Typography */
h1, h2, h3 {
    color: #FFFFFF !important;
    font-weight: 800 !important;
    letter-spacing: -0.5px;
}

p, label {
    color: #CBD5E1;
}

/* Input fields */
.stTextInput input {
    background: #171F2D !important;
    color: white !important;
    border: 1px solid #374151 !important;
    border-radius: 10px !important;
    padding: 13px !important;
}

.stTextInput input:focus {
    border: 1px solid #E63946 !important;
    box-shadow: 0 0 0 1px #E63946 !important;
}

/* Buttons */
.stButton button, 
.stFormSubmitButton button {
    background: #E63946 !important;
    color: white !important;
    border: none !important;
    border-radius: 9px !important;
    font-weight: 700 !important;
    transition: 0.2s ease;
}

.stButton button:hover,
.stFormSubmitButton button:hover {
    background: #C92A36 !important;
    transform: translateY(-2px);
}

/* Cards */
[data-testid="stVerticalBlockBorderWrapper"] {
    background: #111827;
    border: 1px solid #293548;
    border-radius: 14px;
    padding: 12px;
}

/* Progress bars */
.stProgress > div > div > div {
    background-color: #E63946 !important;
}

/* Dividers */
hr {
    border-color: #293548;
}

/* Sidebar */
[data-testid="stSidebar"] {
    background: #111827;
}

</style>
""", unsafe_allow_html=True)



st.markdown("""
<div style="padding: 15px 0 30px 0;">
    <div style="font-size:42px; font-weight:900; color:white;">
        HEARD THAT<span style="color:#E63946;">.</span>
    </div>
    <div style="font-size:13px; color:#94A3B8;
                letter-spacing:3px; margin-top:5px;">
        SPORTS TALK. UNFILTERED.
    </div>
</div>
""", unsafe_allow_html=True)
URL = "https://api.gemini.com/v1/prediction-markets/events"
# Used AI for the skip words feature to ensue thaat the rumor is common despite filler words
SKIP_WORDS = {"the", "and", "that", "going", "will", "for", "with", "are", "was", "his", "her", "they", "have", "has", "from"}


# This next section fetches up to 50 active markets.
@st.cache_data(ttl = 300)
def get_events():
    response = requests.get(URL, params = {"status": "active", "limit": 50}, timeout = 15)
    response.raise_for_status()
    data = response.json()
    if isinstance(data, list):
        return data
    for value in data.values():
        if isinstance(value, list):
            return value
    return []


# This section turns each team's bid and ask prices into a percent chance.
def get_odds(event):
    odds = []
    for contract in event.get("contracts", []):
        prices = contract.get("prices", {})
        try:
            bid = float(prices["bestBid"])
            ask = float(prices["bestAsk"])
            odds.append((contract["label"], (bid + ask) / 2))
        except (KeyError, ValueError, TypeError):
            pass
    total = sum(value for _, value in odds)
    if total == 0:
        return []
    return [(label, round(100 * value / total)) for label, value in odds]

# This section sends the gossip line to ElevenLabs and gets back audio.
@st.cache_data(ttl = 3600)
def speak(text):
    api_key = os.getenv("ELEVENLABS_API_KEY")
    if not api_key:
        return None, "No ELEVENLABS_API_KEY found. Check your .env file."
    voices = requests.get(
        "https://api.elevenlabs.io/v1/voices",
        headers = {"xi-api-key": api_key},
        timeout = 15,
    )
    if voices.status_code != 200:
        return None, f"Could not list voices: error {voices.status_code}"
    premade = [v for v in voices.json().get("voices", []) if v.get("category") == "premade"]
    if not premade:
        return None, "No free premade voices found on this account."
    voice_id = premade[0]["voice_id"]
    response = requests.post(
        f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
        headers = {"xi-api-key": api_key},
        json = {"text": text, "model_id": "eleven_multilingual_v2"},
        timeout = 30,
    )
    if response.status_code != 200:
        return None, f"ElevenLabs error {response.status_code}: {response.text[:200]}"
    return response.content, None
# ask the user for a rumor and match it to the markets
# RUMOR SUBMISSION

st.markdown("""
<div style="background:#151E2D; padding:24px;
            border-radius:14px; border:1px solid #293548;">
    <h2 style="color:white; margin:0;">
        What's the word?
    </h2>
    <p style="color:#94A3B8;">
        Drop a rumor. Let's see what the crowd thinks.
    </p>
</div>
""", unsafe_allow_html=True)

rumor = st.text_input(
    "What did you hear?",
    placeholder="I heard Oregon State is making a big move...",
    label_visibility="collapsed"
)
# This if statement throws out filler words and matches the rumor to the markets. It also shows the first 3 matches and a developer view of the first match.
if rumor:
    events = get_events()
    words = [w.lower().strip("., !?") for w in rumor.split()]
    words = [w for w in words if len(w) > 2 and w not in SKIP_WORDS]

    matches = [e for e in events if any(w in e.get("title", "").lower() for w in words)]

    if matches:
        st.subheader("Ooh, there's a market for that:")
    else:
        st.subheader("No exact match, but here's something interesting:")
        matches = events[:3]
# #The else statemnt shows 3 live markets to at least get something
    top = matches[0]
    st.header(top.get("title", "untitled"))

   
    odds = get_odds(top)

   
    if odds:
        for label, pct in odds:
            st.write(f"**{label}**: {pct}%")
            st.progress(pct / 100)


        chosen = next(((name, p) for name, p in odds if name.lower() in rumor.lower()), odds[0])
        if chosen[1] < 35:
            spice = "Bold!"
        elif chosen [1] > 65:
            spice = "Everbody already knows!"
        else:
            spice = "50/50, not bad."
        gossip = f"Wow, the crowd gives {chosen[0]} a {chosen [1]} percent chance. {spice}"
        st.markdown(f"""
<div style="
    background:linear-gradient(135deg, #202B3B, #151E2D);
    border:1px solid #374151;
    border-left:5px solid #E63946;
    border-radius:12px;
    padding:22px;
    margin:20px 0;
">
    <div style="color:#E63946; font-size:11px;
                font-weight:800; letter-spacing:2px;">
        THE VERDICT
    </div>
    <div style="color:white; font-size:22px;
                font-weight:800; margin-top:10px;">
        {html.escape(gossip)}
    </div>
</div>
""", unsafe_allow_html=True)
        audio, error = speak(gossip)
        if audio:
            st.audio(audio, format = "audio/mp3")
        else:
            st.caption(error)
    else:
        st.write("No odds posted for this one yet.")
# The Chosen section means that the app talks about a given team
# The if/elif/else statements talk about probabiliy with "spice"
    
        

# This section is going to dedicted to making the website look goo!

st.markdown("""
<style>
/* Main application background */
.stApp {
    background-color: #0B0F19;
    color: #F9FAFB;
}

/* Main content spacing */
.block-container {
    padding-top: 2rem;
    padding-bottom: 3rem;
    max-width: 1200px;
}

/* Main headings */
h1, h2, h3 {
    color: #FFFFFF !important;
    font-weight: 800 !important;
}

/* Paragraph text */
p, label {
    color: #D1D5DB;
}

/* Buttons */
.stButton > button {
    background-color: #E63946;
    color: white;
    border: none;
    border-radius: 8px;
    padding: 0.6rem 1.2rem;
    font-weight: 700;
    transition: 0.2s ease;
}

.stButton > button:hover {
    background-color: #C92A36;
    color: white;
    border: none;
}

/* Text input fields */
.stTextInput input,
.stTextArea textarea {
    background-color: #1F2937;
    color: white;
    border: 1px solid #374151;
    border-radius: 8px;
}

/* Sidebar */
[data-testid="stSidebar"] {
    background-color: #111827;
}

/* Dividers */
hr {
    border-color: #374151;
}
</style>
""", unsafe_allow_html=True)
