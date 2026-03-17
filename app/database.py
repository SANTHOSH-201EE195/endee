import os
import endee
from endee.schema import VectorItem
from sentence_transformers import SentenceTransformer

# --- Bug fix for Endee SDK (Pydantic model issue) ---
if not hasattr(VectorItem, 'get'):
    VectorItem.get = lambda self, key, default=None: self.model_dump().get(key, default)

# 15 Emergency Scenarios paired with relief resources
emergency_scenarios = [
    {
        "id": "event_01",
        "resource_name": "Heavy Water Rescue Boat + Flood Protocol",
        "detailed_response": "A Heavy Water Rescue Boat has been dispatched to your location. Please move to the highest possible floor or the roof immediately. Do not attempt to swim through moving water. Signal rescuers with a bright cloth or whistle. Our team is trained in flood extraction and will reach you shortly."
    },
    {
        "id": "event_02",
        "resource_name": "Insulin & Medical Kit + Diabetic Emergency",
        "detailed_response": "Emergency medical responders are en route with a focused Insulin & Medical Kit. If you are conscious, try to sit or lie down in a safe position. If you have any fast-acting sugar (like juice or soda) nearby and can safely swallow, consume it now. Keep your airway clear and stay on the line if possible."
    },
    {
        "id": "event_03",
        "resource_name": "Thermal Tents + Exposure Risk",
        "detailed_response": "Thermal Tents and cold-weather survival gear are being deployed to your coordinates. To prevent further exposure, stay out of the wind and keep off the cold ground. If you are with others, huddle together for warmth. Cover your head and neck. Our team will provide immediate insulation and heat sources upon arrival."
    },
    {
        "id": "event_04",
        "resource_name": "Aerial Fire Suppression + Wildfire Protocol",
        "detailed_response": "Aerial support and ground fire crews have been alerted. If an evacuation order is in effect, leave immediately via the designated route. Close all windows and doors before leaving. If trapped, stay low to the ground to avoid smoke inhalation and find a clearing away from dense vegetation."
    },
    {
        "id": "event_05",
        "resource_name": "Advanced Life Support (ALS) Unit + Cardiac Protocol",
        "detailed_response": "An ALS Ambulance is rushing to your location. If the patient is unresponsive and not breathing, begin chest compressions (hands-only CPR) immediately—push hard and fast in the center of the chest. We are 5 minutes away. Stay calm; expert help is coming."
    },
    {
        "id": "event_06",
        "resource_name": "Search and Rescue K9 Team + Missing Person Protocol",
        "detailed_response": "A specialized K9 Search and Rescue team is being deployed. Please stay exactly where you are to avoid crossing paths or confusing the scent trail. Blow a whistle or shout at regular intervals. If night is falling, try to build a signal fire or use a flashlight. We are combing the sector now."
    },
    {
        "id": "event_07",
        "resource_name": "Hydraulic Extraction Tool + Vehicle Entrapment",
        "detailed_response": "A Rescue Squad equipped with hydraulic 'Jaws of Life' is en route. If you are inside the vehicle, remain as still as possible to prevent further injury. Do not attempt to move unless there is an immediate threat of fire. We will stabilize the vehicle and extract you safely."
    },
    {
        "id": "event_08",
        "resource_name": "Hazmat Containment Unit + Chemical Spill",
        "detailed_response": "A Hazmat team is responding to the chemical leak. Stay upwind and uphill of the spill site. Seek high ground if the vapors are heavier than air. Cover your nose and mouth with a damp cloth if possible. Do not touch or walk through any spilled liquid. We are initiating containment procedures."
    },
    {
        "id": "event_09",
        "resource_name": "High-Angle Rope Rescue + Mountain Fall",
        "detailed_response": "A Technical Rope Rescue team is preparing for extraction. If you are on a ledge, move as little as possible. If you can, anchor yourself to a stable point. Stay vocal so our technicians can locate your exact position. We will use a litter/stretcher to bring you to safety."
    },
    {
        "id": "event_10",
        "resource_name": "Emergency Potable Water Truck + Drought/Contamination",
        "detailed_response": "A Potable Water Truck is being dispatched to the central relief point in your area. Please bring clean containers for collection. Do not drink from local taps until they have been cleared by health officials. We are also providing water purification tablets for immediate use."
    },
    {
        "id": "event_11",
        "resource_name": "Industrial Power Generator + Utility Failure",
        "detailed_response": "High-capacity Industrial Power Generators are being moved to critical infrastructure and community centers. If you rely on home medical equipment, please proceed to the nearest designated 'Warm Site' for power. Avoid using candles for light; use flashlights to prevent fire risk."
    },
    {
        "id": "event_12",
        "resource_name": "Trauma Surgical Team + Active Threat",
        "detailed_response": "A specialized Trauma Surgical Unit is on standby at the nearest secure perimeter. Follow all Law Enforcement instructions immediately: Run, Hide, or as a last resort, Fight. If you have injuries, apply firm pressure to bleeding sites. We will move in as soon as the area is secured."
    },
    {
        "id": "event_13",
        "resource_name": "Earthquake Structural Stabilizers + Collapse Risk",
        "detailed_response": "Structural Engineering teams with heavy-duty stabilizers are responding. If you are inside a damaged building, evacuate carefully if possible. If trapped, tap on a pipe or wall so rescuers can hear you. Avoid using elevators. We are arriving to shore up the structure and begin extraction."
    },
    {
        "id": "event_14",
        "resource_name": "Anti-Venom & Toxin Kit + Wildlife Encounter",
        "detailed_response": "A medical unit with a broad-spectrum Anti-Venom and Toxin Kit is on the way. Keep the affected limb immobilized and at or below heart level. Do not attempt to suck out the venom or apply a tourniquet. Describe the appearance of the creature to the responders upon arrival."
    },
    {
        "id": "event_15",
        "resource_name": "Field Kitchen & Ration Supply + Displacement",
        "detailed_response": "A Mobile Field Kitchen and emergency food ration supplies are being set up at the community shelter. Nutritious, ready-to-eat meals are available for all displaced individuals. Please bring any identification or ration cards if you have them, though no one will be turned away."
    }
]

# Endee Server Configuration
INDEX_NAME = "emergency_sos"

def setup_database():
    # Initialize client
    client = endee.Endee(token="test")
    client.set_base_url("http://localhost:8081/api/v1")
    
    print(f"Checking index: {INDEX_NAME}...")
    try:
        # Create index if it doesn't exist (dimension 384 for ‘all-MiniLM-L6-v2’)
        client.create_index(name=INDEX_NAME, dimension=384, space_type="cosine")
        print(f"Index '{INDEX_NAME}' created.")
    except Exception as e:
        print(f"Index check: {e} (might already exist)")

    print("Loading SentenceTransformer model 'all-MiniLM-L6-v2'...")
    model = SentenceTransformer('all-MiniLM-L6-v2')
    
    index = client.get_index(INDEX_NAME)
    payloads = []
    
    print("Vectorizing scenarios and preparing payloads...")
    for entry in emergency_scenarios:
        # Vectorize the detailed_response as requested
        embedding = model.encode(entry["detailed_response"]).tolist()
        
        payloads.append({
            "id": entry["id"],
            "vector": embedding,
            "meta": {
                "resource_name": entry["resource_name"],
                "detailed_response": entry["detailed_response"]
            }
        })
    
    print(f"Inserting {len(payloads)} records into Endee Index '{INDEX_NAME}'...")
    try:
        index.upsert(payloads)
        print("Knowledge base successfully seeded!")
    except Exception as e:
        print(f"ERROR: Could not insert data: {e}")
        print("\nLOCALIZATION TIP:")
        print("1. Ensure your containerized Endee server is running via Docker.")
        print("2. Run 'docker-compose up -d --build' in the root folder.")
        print("3. Then run this script again to seed the database.")

if __name__ == "__main__":
    setup_database()
