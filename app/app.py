import streamlit as st
import endee
from endee.schema import VectorItem
from sentence_transformers import SentenceTransformer
from streamlit_geolocation import streamlit_geolocation

# --- Page Config ---
st.set_page_config(page_title="Emergency SOS Textline", page_icon="🚨", layout="centered")

# --- Bug fix for Endee SDK (Pydantic model issue) ---
if not hasattr(VectorItem, 'get'):
    VectorItem.get = lambda self, key, default=None: self.model_dump().get(key, default)

# --- Initialization ---
@st.cache_resource
def load_resources():
    model = SentenceTransformer('all-MiniLM-L6-v2')
    client = endee.Endee(token="test")
    client.set_base_url("http://localhost:8081/api/v1")
    index = client.get_index("emergency_sos")
    return model, index

model, index = load_resources()

# --- State Management ---
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "🛰️ **Emergency Response Mission Control Active.** Please describe your situation, specific hazards, and immediate needs for coordination."}
    ]

if "pending_dispatch" not in st.session_state:
    st.session_state.pending_dispatch = None
if "user_location" not in st.session_state:
    st.session_state.user_location = None
if "dispatched_resources" not in st.session_state:
    st.session_state.dispatched_resources = []

# --- Helper Functions ---
def format_protocol(protocol_text):
    """Converts a paragraph into a point-by-point checklist."""
    points = [p.strip() for p in protocol_text.split('.') if p.strip()]
    formatted = ""
    for point in points:
        formatted += f"✅ {point}.\n\n"
    return formatted

def build_aggregated_response(new_resource, protocol, location):
    """Builds an empathetic aggregated response."""
    if new_resource not in st.session_state.dispatched_resources:
        st.session_state.dispatched_resources.append(new_resource)
    
    all_resources = ", ".join(st.session_state.dispatched_resources)
    count = len(st.session_state.dispatched_resources)
    
    if count == 1:
        msg = f"**System Alert: {new_resource} is on the way to {location}.**\n\n"
    else:
        msg = f"**I have added {new_resource} to your dispatch.** I understand this is a critical situation. "
        msg += f"Currently, all resources (**{all_resources}**) are en route to your location at **{location}**.\n\n"
    
    msg += "### Immediate Safety Instructions:\n"
    msg += format_protocol(protocol)
    return msg

# --- UI Header ---
st.title("🚨 Emergency SOS Textline")
st.markdown("---")

# --- Display Chat History ---
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# --- Interaction Flow ---

# 1. Location Gathering Processing (Only if not already known)
if st.session_state.pending_dispatch and not st.session_state.user_location:
    with st.chat_message("assistant"):
        st.write("📍 **Location required to finalize dispatch.**")
        
        # Real Browser Geolocation
        st.write("Click below to provide your coordinates automatically:")
        location = streamlit_geolocation()
        
        location_captured = ""
        if location and location.get("latitude") and location.get("longitude"):
            location_captured = f"{location['latitude']}, {location['longitude']} (Browser GPS)"
            st.success(f"Detected: {location_captured}")

        # Manual Input
        location_input = st.text_input(
            "Or enter address/landmarks manually:", 
            value=location_captured,
            key="loc_input_manual"
        )

        if st.button("Confirm Location & Dispatch"):
            final_loc = location_input or location_captured
            if final_loc:
                st.session_state.user_location = final_loc
                st.session_state.messages.append({"role": "user", "content": f"My location is: {final_loc}"})
                
                dispatch = st.session_state.pending_dispatch
                final_response = build_aggregated_response(dispatch["resource"], dispatch["protocol"], final_loc)
                
                st.session_state.messages.append({"role": "assistant", "content": final_response})
                st.session_state.pending_dispatch = None
                st.rerun()
            else:
                st.warning("Please provide a location via GPS or manual input.")

# 2. Main Chat Input (Only if not waiting for location)
else:
    if prompt := st.chat_input("Describe your emergency..."):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        with st.spinner("Analyzing situation..."):
            try:
                query_vector = model.encode(prompt).tolist()
                results = index.query(vector=query_vector, top_k=1)
                
                if results and len(results) > 0:
                    match = results[0]
                    similarity = match.get('similarity', 0)
                    
                    # Threshold to filter out non-emergency/irrelevant queries
                    if similarity < 0.2:
                        msg = "I'm here to assist with emergencies and safety protocols. Please ask if you need help with a disaster or crisis situation."
                        st.session_state.messages.append({"role": "assistant", "content": msg})
                    else:
                        meta = match.get("meta", {})
                        resource = meta.get("resource_name", "Standard Emergency Response")
                        protocol = meta.get("detailed_response", "Please stay calm, help is being coordinated.")
                        
                        if st.session_state.user_location:
                            # Direct dispatch if location known
                            final_response = build_aggregated_response(resource, protocol, st.session_state.user_location)
                            st.session_state.messages.append({"role": "assistant", "content": final_response})
                        else:
                            # Need location
                            st.session_state.pending_dispatch = {"resource": resource, "protocol": protocol}
                            msg = f"I've identified your situation. I am ready to dispatch the **{resource}**. To ensure we reach you quickly, please provide your exact location."
                            st.session_state.messages.append({"role": "assistant", "content": msg})
                else:
                    msg = "I'm here to assist with emergencies. Please describe your situation if you need immediate help."
                    st.session_state.messages.append({"role": "assistant", "content": msg})

            except Exception as e:
                msg = f"An error occurred: {e}. Please call 911 directly if possible."
                st.session_state.messages.append({"role": "assistant", "content": msg})
        
        st.rerun()
