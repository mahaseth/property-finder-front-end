import React, { useState } from 'react';
import './VoiceChatScreen.css';
import {
  startRecording,
  stopRecording,
  sendAudioToBackend,
  playAudioFromUrl,
} from '../../services/audioService';
import { FaMicrophone, FaStop } from 'react-icons/fa';

function VoiceChatScreen({ onEndChat }) {
  const [recorder, setRecorder] = useState(null);
  const [audioChunks, setAudioChunks] = useState([]);
  const [isBotReplying, setIsBotReplying] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [propertyPrompt, setPropertyPrompt] = useState("Tap the mic and ask me about a property 🏡");
  const [errorMessage, setErrorMessage] = useState('');

  const handleStartRecording = async () => {
    await startRecording(setRecorder, setAudioChunks);
    setIsRecording(true);
    setErrorMessage('');
  };

  const handleStopRecording = () => {
    stopRecording(recorder);
    setIsRecording(false);
  };

  const handleMicClick = async () => {
    if (!isRecording) {
      handleStartRecording();
    } else {
      handleStopRecording();

      // Now send the audio chunks to backend
      setIsBotReplying(true);
      setPropertyPrompt("Processing your question... 🤖");

      const audioBlob = new Blob(audioChunks, { type: 'audio/wav' });
      const response = await sendAudioToBackend(audioBlob);

      if (response.error) {
        setErrorMessage("⚠️ " + response.message);
        setPropertyPrompt("⚠️ Backend unavailable. Try again later.");
        setIsBotReplying(false);
        return;
      }

      console.log("🎙️ Transcription:", response.transcription);
      console.log("📦 Extracted Info:", response.extracted);
      console.log("🗣️ Bot Reply:", response.reply_text);

      if (response.audio_url) {
        await playAudioFromUrl(`http://127.0.0.1:8000/${response.audio_url}`);
      }

      setIsBotReplying(false);
      setPropertyPrompt("Ask another question or explore more 🏘️");
      setAudioChunks([]);
    }
  };

  return (
    <div className={`voice-chat-screen ${isBotReplying ? 'blur-background' : ''}`}>
      <div className="chat-header">
        <h2>🏘️ Real Estate Voice Assistant</h2>
        <p className="chat-subtitle">Let’s find your dream property — just talk to me!</p>
      </div>

      <div className="chat-container">
        <p className="bot-response">
          {isBotReplying ? "🤖 Replying with the best property match..." : `🎧 ${propertyPrompt}`}
        </p>
      </div>

      <div className="mic-toggle">
        <button
          className={`mic-button ${isRecording ? "recording" : ""}`}
          onClick={handleMicClick}
        >
          {isRecording
            ? <FaStop size={22} color="white" />
            : <FaMicrophone size={22} color="#007bff" />
          }
        </button>
        <p className="mic-status">{isRecording ? "Recording..." : "Tap to speak"}</p>
        {errorMessage && (
          <p className="error-message">{errorMessage}</p>
        )}
      </div>

      <div className="footer-note">📍 Serving properties around your preferred suburb</div>

      <button
        className="end-chat-button"
        onClick={() => {
          handleStopRecording();
          onEndChat();
        }}
      >
        End Chat
      </button>
    </div>
  );
}

export default VoiceChatScreen;
