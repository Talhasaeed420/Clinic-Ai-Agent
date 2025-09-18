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
Call ending-----------
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

How encryption and decryption is added?
--------------No one can see the data in mongo db 
--------------Dont lose the encryption key inside .env file if lose all data will be lost and noone can recover it 
--------------WHo can decrypt? And how 
--------------Files used   ----dependencies/auth.py for hardcode the authorize user for now we can change later.
------------------------------- encrypt/encryption.py  (Two functions 1 for encrypt and 1 for decrypt)
-------------------------------  Used in webhook_service , utils/vapi_chatbot 

---Use the password  ---admin--- to decrypt the data for now 


---------------------------------------------------------------------------------
---------------------------------------------------------------------------------

What  utils files doing?? (Functions used in other files)
------------------Files--------------------
utils/daterparse.py ---> used in webhook to change the natural language date to 10/09/2025 type date
utils/formatter.py ----> to set the phonenumber format used in webhook so make.com receive the correct phonenumber
utils/querybuilder.py ---> Success messages , json sent like this ( Vapi sent you a data this file make the json format, vapi sents appointment_id it queries so mongo receive it correctly)
utils/responses.py -------> the response in success and error ways (json success used in clinic.py file when vapi sends the data)
utils/vapi_chatbot.py -----> needed for making vapi chat bot so he will remember us by our user id 
utils/vapi_cost.py  ------> needed to get the cost like total cost , avg_cost the metrics of vapi 

---------------------------------------------------------------------------------

What services files doing? 
-----------------Files-----------------------

services/admin_service.py ---> that is decrypting the data only for authorized always remember dont use it for anyone(sensitive)
services/appointment_service -----> creating, updating , deleting appointments functions used by vapi 
services/webhook_service.py ---->  handling end of tool, handling end of call report and saving in database , saving data in make.com
service/user-service ------> For admin Authentication

----------------------------------------------------------------
What vapi-voice-trans doin?
------Files------
vapi_options.py is needed to sets the data for voice , transcriber and models it is important so the client who wants to sets
can change see what options are available 

----------------------------------------------------------------
*****************Routers***************************************

init.py  ----> empty file for python (optional but a good thing to use so python accurately use the files)
admin.py -----> api for admin_service so he can see the decrypted data after login without login he also cant see the data 
bot_clinic.py ----->  Used by admin to change voice , transcriber and  by sync_assistant api vapi will receive the data
bot_tool.py ------> used by the developer(only credential) so he can add delete or update tool that we made on vapi copy the tool id from vapi and put it there and then use sync_assistant api so vapi receive it 
clinic.py ------> main file for creating , updating , deleting , webhook and booking api
doctor_data.py ---->  add,update, delete doctor data 
vapi_chat.py ------> if someone wants to make a ui of chat bot use this endpoint to talk to vapi
vapi_metrics.py ----> use this api to get the cost of vapi 
user.py ---> FOr user Authentication





-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
********************************************** Workflow of all the code ****************************************************

Example 1 related to call: 

Im the patient and i want to  book an appointment i call on the number vapi gave me. He asked me details
1.Name 2.Time 3. email (spell for him for better assistance) 4.reason 5. speciality means a cardiologist or wtever my need is 

He books the appointment. Data will be saved in mongo db . 
Email is sensitive info so it will be encrypted u see text like gaadasdsadas not readable. For anyone. 
Now i call again and want to delete or update time he will ask appointment_id you will receive that on your email or sms
Everything done? No 

Now if data is encrypted who can see it the admin can decrypt the data by the functions i made 
Only admin can see the callslog and receptionist can only read the name,time,doctor_name no email get_ac_purchase_details

How admin will see the data??----
Admin have access like his own id and pass we make he can see by our functions inside files (encrypt/encryption , admin_service ,admin.py(api))



*****************


Example  2:

THis time i chat with vapi same he ask details 
And the data is saved the chat conversation will be saved in chats collection.
Chat is encrypted again bcz sometime client can tell sensitive info by mistake so it is encrypted 
Admin can see by decrypt it. 



*****************************************8

Why admin wants to see the data? And What things are encrypted?

Callslog, chats , email, phonenumber all sensitive info 


Sometimes there is an issue like i dont say that to your agent. So admin should have access to what our agent said and what client said 


