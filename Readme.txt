Voice Assistant Project – Clinic Appointments + Call Center
(Using Vapi AI + FastAPI + MongoDB)

Overview:
This project is a dual-purpose voice assistant that allows users to interact via phone calls for two types of services:
1. Clinic Appointment Booking
2. AC Support and Service

Tech Stack:
- Vapi AI (Voice AI tool)
- FastAPI (Python backend framework)
- MongoDB (for storing customer & appointment data)
- Ngrok (for exposing localhost to Vapi)

Use Case Flow:

1️⃣ Start Call:
Vapi prompts:
“Welcome! Are you calling for a doctor appointment or AC support today?”

2️⃣ If user says "Doctor Appointment":
   - Assistant asks for name, date, and time.
   - Data is sent to `/book_appointment` FastAPI endpoint.
   - Response confirms: “Your appointment has been booked.”

3️⃣ If user says "AC Support":
   - Assistant asks what kind of help is needed:
     - Purchase details
     - Warranty info
     - Schedule service
     - Troubleshooting
   - For purchase details:
     - Assistant asks for customer ID
     - Data sent to `/get_ac_purchase_details?customer_id=XYZ`
     - Response: purchase info or "no result found"

