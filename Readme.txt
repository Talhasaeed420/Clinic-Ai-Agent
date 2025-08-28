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



   Steps for uvicorn (virtual env)

   1) make the environment
      python -m venv .venv
      
   2) active the environment
      .\.venv\Scripts\activate

   3) install the dependencies
      python -m pip install -r requirements.txt

   4) run the server
      uvicorn main:app --reload


   -----------------------Clinic Assistant Details---------------------------
1. 
Start with making model so our endpoint (/webhook) receive vapi data (transcriber , voice , transcipt , assistantid, caller everything)
-------Models  made for webhook----------
1. Artifacts.py 
2. Configs.py
3. info.py
4. metric.py
5. object_id.py
6. report.py
Finally all these are called in Model ----mainvapidata.py--- for a single model
----When call starts the vapi hits the /webhook endpoint and when call ended details saved in database ----calllogs---

---------------------------------------------------------------------------------------------------------
2. How vapi asstant is created??
-------Created a file name onetime_botconfig/assistantconfig.py just run it for one time to save data inside database this is for one time only 
-------Created a service/vapi_client.py file that actually make the assistant 
-------created a script/sync-vapi-assistant.py that use the services file to send the vapi configurations to vapi 
------- created a clinic_configuration/bot_tools.py file for all the tools used in vapi (scrript also use the file for tools)


Now in routers/bot_clinic.py a endpoint /sync_assistant when it hits the data sends to vapi.

--------------------------------------------------------------------------------------------------
3. How user will get options for voice and transcriber  selection?

------Created a file vapi-voice-trans/vapi_options.py file that actually sends data to the database 
------The client select the model , etc from there and use the post api inside router/bot_clinic.py so the bot-config data is updated 
------Then the sync-assitant should be trigger so vapi will be updated 


-------------------------------------------------------------------------------------------------
4. How Auto email with make.com is working?
----------Create a webhook scenario in make.com get the url and used in what 
you want to hit like in this code /booking is hit to send the data to make.com

----------then for email use your gmail inside make.com combine it with webhook scenario and
 when you send an email it auto sends the email you provide to destination

 ----------------------------------------------------------------------------

 5. How our client will change the voice and transcriber from ui?

-------In our ui there will be a dropdown or whatever you want to select 
lets say its a drop down the dropdown use a fastapi from routers/bot_clinic.py  get-vapi-options endpoint and 
He select the available options 

--------THen when he select from dropdown there will be a save button thats hits the fast api post for update bot 
inside routers/bot_clinic.py


---------when he hits the button the data in mongo db updated with collection bot-configs and save inside it '

--------THen ui will have a publish button that hits the api inisde routers/bot_clinic.py  the sync_assistant
one so the vapi will be updated with new voice and ready to go.



------------------------------------------------------------------