## Technologies Used

- **FastAPI** – Backend framework
- **Vapi AI** – Voice assistant platform
- **MongoDB** – Database for storing appointments
- **Ngrok** – Tunneling tool to make local server public
- **Pydantic** – Data validation
- **httpx** – Async HTTP client for Vapi call trigger

Project Structure

project/
│
├── main.py # FastAPI app & routes
├── models.py # Pydantic models for validation
├── database.py # MongoDB connection & lifespan setup
├── .env # API keys and DB URIs

## How to Run

1. Extract zip file.
2. Add your `.env` file with Vapi API key, Assistant ID, Mongo URI
3. Run the FastAPI app
uvicorn main:app --reload
4. Start ngrok:
ngrok http 8000
5. Paste the ngrok link in Vapi assistant’s tool call URL