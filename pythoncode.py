import pyrebase
import firebase_admin
from firebase_admin import credentials, firestore

# Initialize Firebase Realtime Database
firebase_config = {
    "apiKey": "AIzaSyB_u-sbR-EiMaa_LMy0Dykaqc2l66fMNU0",
    "authDomain": "java-chip-435d2.firebaseapp.com",
    "databaseURL": "https://java-chip-435d2-default-rtdb.firebaseio.com",
    "projectId": "java-chip-435d2",
    "storageBucket": "java-chip-435d2.appspot.com",
    "messagingSenderId": "439056982183",
    "appId": "1:439056982183:web:a1c81cddd9180a0c42fb82"
}

firebase = pyrebase.initialize_app(firebase_config)
database = firebase.database()
patient_data = database.child('patient-data').get().val()

# Initialize Firebase Admin SDK for Firestore (only once)
if not firebase_admin._apps:
    cred = credentials.Certificate("/content/java-chip-435d2-firebase-adminsdk-trxln-4b845add19.json")  # Replace with your service account key file
    firebase_admin.initialize_app(cred)
db = firestore.client()

# Fetch data from Firebase Realtime Database and Firestore
doctors_data = db.collection("doctor-data").stream()

# Extract all doctor details
doctors = []
for doctor_info in doctors_data:
    doctor_data = doctor_info.to_dict()
    doctors.append(doctor_data)
    print(f"Doctor Data: {doctor_data}")

# Check if patient data is available
if patient_data is not None:
    print("\nPatient Details from Realtime Database:")
    patients = []
    for patient_id, patient_info in patient_data.items():
        if isinstance(patient_info, dict):  # Check if patient_info is a dictionary
            # Determine diagnosis based on symptoms
            symptoms = patient_info.get("symptoms", "").lower()
            age = int(patient_info.get("age", 0))

            # Split symptoms into words
            symptom_words = symptoms.split()

            if any(symptom in symptom_words for symptom in ["fever", "cold", "cough", "tiredness", "headache", "diarrhea"]) and age < 18:
                # Pediatrician
                patient_info["diagnosis"] = "Pediatrician"
            elif any(symptom in symptom_words for symptom in ["fever", "cold", "cough", "tiredness", "headache", "diarrhea"]):
                # General Physician
                patient_info["diagnosis"] = "General Physician"
            elif any(symptom in symptom_words for symptom in ["swelling", "fracture", "sprain", "limiting", "motion", "bleeding"]):
                # Orthopedic
                patient_info["diagnosis"] = "orthopedics"
            elif any(symptom in symptom_words for symptom in ["pimples", "burns", "rashes", "allergy", "scars", "infection"]):
                # Dermatologist
                patient_info["diagnosis"] = "Dermatologist"
            else:
                # No specific diagnosis found
                patient_info["diagnosis"] = "Unknown Diagnosis"

            # Include patientId, age, gender, and symptoms
            patient_info["patient_id"] = patient_id
            patient_info["age"] = age
            patient_info["gender"] = patient_info.get("gender", "Unknown")
            patient_info["symptoms"] = symptoms

            # Extract all patient details
            patients.append(patient_info)
            print(f"Patient Data: {patient_info}")
else:
    print("No patient data found in the Realtime Database.")

# Define a dictionary to store doctor-patient associations
doctor_patients = {}

# Assign patients to available doctors' queues based on matching specialization
for patient in patients:
    if "diagnosis" not in patient:
        print(f"No diagnosis for patient {patient.get('firstName', 'Unknown')}, skipping...")
        continue

    for doctor in doctors:
        if doctor["avail"] is True and doctor["specl"] == patient["diagnosis"]:
            # Initialize a list for the doctor's patients if it doesn't exist
            if doctor["docName"] not in doctor_patients:
                doctor_patients[doctor["docName"]] = []

            # Add the patient to the doctor's patients list
            # Include patientId, age, gender, and symptoms
            doctor_patients[doctor["docName"]].append({
                "patient_id": patient["patient_id"],
                "patient_name": patient["firstName"],
                "age": patient["age"],
                "gender": patient["gender"],
                "symptoms": patient["symptoms"],
                "severity": patient.get("severity", "low"),  # Default to "low" if "severity" is missing
                "arrival_time": patient.get("time", 0)  # Default to 0 if "time" is missing
            })
# Update patient status and remove completed patients
for doctor_name, patients_list in doctor_patients.items():
    for index, patient in enumerate(patients_list):
        if index == 0:
            patient["status"] = "inprogress"
        else:
            patient["status"] = "waiting"

# Sort patients within each doctor's queue based on severity (high, moderate, low) and arrival time
patients_list.sort(key=lambda x: (x["severity"].lower(), x["arrival_time"]))

# Define a custom order for severity levels
severity_order = {"high": 0, "moderate": 1, "low": 2}

# Sort patients within each doctor's queue based on the custom severity order
patients_list.sort(key=lambda x: (severity_order[x["severity"].lower()], x["arrival_time"]))

# Calculate and update the wait time for patients
# Define the time in minutes for each severity level
severity_time = {"high": 15, "moderate": 10, "low": 5}

# Iterate through each doctor's queue
for doctor_name, patients_list in doctor_patients.items():
    previous_patient_wait_time = 0  # Initialize the wait time for the first patient
    for patient in patients_list:
        # Calculate wait time based on severity
        severity = patient["severity"].lower()
        wait_time = severity_time.get(severity, 0)

        # Add the wait time to the previous patient's wait time
        patient["wait_time"] = previous_patient_wait_time

        # Print the wait time for the current patient
        print(f"Patient {patient['patient_name']} - Wait Time: {patient['wait_time']} mins")

        # Update the previous_patient_wait_time for the next iteration
        previous_patient_wait_time += wait_time

# Reference the "doctors" collection in Firestore
doctors_collection = db.collection("doctors")

# Update Firestore with doctor-patient associations and appointment details
for doctor_name, patients_list in doctor_patients.items():
    doctor_data = next((doc for doc in doctors if doc["docName"] == doctor_name), None)
    if doctor_data:
        doctor_data["patients"] = patients_list
        # Check if the doctor's document already exists in Firestore
        doctor_doc_ref = doctors_collection.document(doctor_name)
        if doctor_doc_ref.get().exists:
            # If the document exists, update it with the new data
            doctor_doc_ref.update(doctor_data)
            print(f"Updated doctor's data for {doctor_name}")
        else:
            # If the document does not exist, create it with the new data
            doctor_doc_ref.set(doctor_data)
            print(f"Created doctor's data for {doctor_name}")

# Remove patients with a "status" of "completed" from the queues
for doctor_name, patients_list in doctor_patients.items():
    doctor_patients[doctor_name] = [patient for patient in patients_list if patient.get("status") != "completed"]

print("Doctor-patient associations updated in Firestore successfully.")
