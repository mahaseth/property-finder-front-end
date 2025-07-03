from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from faster_whisper import WhisperModel
import openai
import json
import pyodbc
from gtts import gTTS
import os
import logging
from typing import Dict, Any
import tempfile

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Real Estate Voice Robot API", description="Complete voice interaction system")

# Connect to the frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Whisper model instance
whisper_model = WhisperModel("base")

# Azure OpenAI configuration
openai.api_type = "azure"
openai.api_key = "mSSedelOpALeOCyKP4ssEipRpAkgAZz3v1kTIHBSGnrJqprIo349JQQJ99BGACL93NaXJ3w3AAABACOGf4ui"
openai.api_base = "https://aivoicetest.openai.azure.com/"
openai.api_version = "2024-02-15-preview"

# Azure SQL configuration
AZURE_SQL_CONFIG = {
    "driver": "ODBC Driver 18 for SQL Server",
    "server": "voiceai-sql-server.database.windows.net",
    "database": "RealEstateConvoAI",
    "username": "lorraine",
    "password": "Test123!Temp"
}

def save_uploaded_audio(file: UploadFile) -> str:
    try:
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".wav")
        temp_path = temp_file.name
        temp_file.close()
        with open(temp_path, "wb") as f:
            f.write(file.file.read())
        logger.info(f"Audio saved: {temp_path}")
        return temp_path
    except Exception as e:
        logger.error(f"Audio save failed: {e}")
        raise HTTPException(status_code=500, detail="Audio save failed")

def speech_to_text(audio_path: str) -> str:
    try:
        segments, _ = whisper_model.transcribe(audio_path, beam_size=5)
        text = " ".join([segment.text for segment in segments]).strip()
        logger.info(f"Speech recognition result: {text}")
        return text
    except Exception as e:
        logger.error(f"Audio to text failed: {e}")
        raise HTTPException(status_code=500, detail="Audio to text failed")

def extract_info(text: str) -> Dict[str, Any]:
    try:
        prompt = (
            "Extract the client's name, phone number, and property address from the text below. "
            "Return ONLY a JSON object (no extra text, no explanations, no code block).\n"
            f"Text: {text}\n"
            "Example output: {\"name\": \"Kevin Su\", \"phone\": \"0402662860\", \"address\": \"101/25-33 Wills Street Melbourne VIC 3000\"}"
        )
        response = openai.ChatCompletion.create(
            engine="gpt4o_voicebot",
            messages=[{"role": "user", "content": prompt}],
            temperature=0
        )
        content = response.choices[0].message['content']
        return json.loads(content)
    except Exception as e:
        logger.error(f"Information extraction failed: {e}")
        return {}

def query_property_azure(address: str) -> Any:
    try:
        conn = pyodbc.connect(
            f"DRIVER={{{AZURE_SQL_CONFIG['driver']}}};SERVER={AZURE_SQL_CONFIG['server']};"
            f"DATABASE={AZURE_SQL_CONFIG['database']};UID={AZURE_SQL_CONFIG['username']};"
            f"PWD={AZURE_SQL_CONFIG['password']};Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;"
        )
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM [House_Data] WHERE [name] LIKE ?", ('%' + address + '%',))
        result = cursor.fetchone()
        conn.close()
        return result if result else "Not found"
    except Exception as e:
        logger.error(f"Database query failed: {e}")
        return "Database error"

def property_summary(row: Any) -> str:
    if row == "Not found":
        return "Sorry, no matching property found."
    elif row == "Database error":
        return "Database access issue. Try again later."
    return (
        f"Matched property:\nAddress: {row[0]}\nType: {row[1]}\nYear: {row[2]}, Region: {row[18]}\n"
        f"Rooms: {row[7]} bed(s), {row[8]} bath(s), {row[9]} car space(s)\nRent: ${row[16]}\n"
        f"Nearby: {row[6]}, Postcode: {row[4]}"
    )

def text_to_speech(text: str, output_path: str = "result.mp3") -> str:
    try:
        gTTS(text, lang="en").save(output_path)
        return output_path
    except Exception as e:
        logger.error(f"TTS failed: {e}")
        raise HTTPException(status_code=500, detail="Text to speech failed")

def upload_to_azure_sql(data: Dict[str, Any]) -> bool:
    try:
        conn = pyodbc.connect(
            f"DRIVER={{{AZURE_SQL_CONFIG['driver']}}};SERVER={AZURE_SQL_CONFIG['server']};"
            f"DATABASE={AZURE_SQL_CONFIG['database']};UID={AZURE_SQL_CONFIG['username']};"
            f"PWD={AZURE_SQL_CONFIG['password']};Encrypt=yes;TrustServerCertificate=no;Connection Timeout=30;"
        )
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO Customer_Table (name, phone, address) VALUES (?, ?, ?)",
            data.get("name", ""), data.get("phone", ""), data.get("address", "")
        )
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Upload failed: {e}")
        return False

@app.post("/process-audio")
async def process_audio(file: UploadFile = File(...)):
    try:
        logger.info("Processing audio...")
        audio_path = save_uploaded_audio(file)
        text = speech_to_text(audio_path)
        client_info = extract_info(text)
        property_info = ""
        if client_info.get('address'):
            result = query_property_azure(client_info['address'])
            property_info = property_summary(result)
        audio_response_path = text_to_speech(property_info)
        if client_info:
            upload_to_azure_sql(client_info)
        if os.path.exists(audio_path):
            os.remove(audio_path)
        return {
            "success": True,
            "recognized_text": text,
            "client_info": client_info,
            "property_info": property_info,
            "audio_file": os.path.basename(audio_response_path)
        }
    except Exception as e:
        logger.error(f"Processing failed: {e}")
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")

@app.get("/audio/{filename}")
async def get_audio(filename: str):
    file_path = f"./{filename}"
    if os.path.exists(file_path):
        return FileResponse(file_path, media_type="audio/mpeg")
    raise HTTPException(status_code=404, detail="Audio file not found")

@app.get("/health")
async def health_check():
    return {"status": "healthy", "message": "API running"}

@app.get("/")
async def root():
    return {
        "message": "Real Estate Voice Robot API", 
        "docs": "/docs",
        "endpoints": {
            "process_audio": "POST /process-audio",
            "get_audio": "GET /audio/{filename}",
            "health": "GET /health"
        }
    }

if __name__ == "__main__":
    import uvicorn
    print("Start the Real Estate Voice Robot Backend API...")
    print("API address: http://localhost:3000")
    print("API documentation: http://localhost:3000/docs")
    print("Front end address: http://localhost:3000")
    print("=" * 50)
    uvicorn.run(app, host="0.0.0.0", port=3000, reload=True)