// services/audioService.js

export async function startRecording(setRecorder, setAudioChunks) {
  const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
  const mediaRecorder = new MediaRecorder(stream);

  let chunks = [];

  mediaRecorder.ondataavailable = (e) => {
    chunks.push(e.data);
  };

  mediaRecorder.onstop = () => {
    setAudioChunks(chunks);
  };

  mediaRecorder.start();
  setRecorder(mediaRecorder);
}

export function stopRecording(recorder) {
  if (recorder && recorder.state === 'recording') {
    recorder.stop();
  }
}

export async function sendAudioToBackend(audioBlob) {
  const formData = new FormData();
  formData.append("file", audioBlob, "voice.wav");

  try {
    const response = await fetch("http://localhost:8000/upload_audio", {
      method: "POST",
      body: formData,
    });

    if (!response.ok) {
      throw new Error(`Backend error ${response.status}`);
    }

    const result = await response.json();

    if (!result.audio_url) {
      throw new Error("Missing audio_url in backend response.");
    }

    return result; // { transcription, extracted, reply_text, audio_url }

  } catch (error) {
    console.error("❌ Backend unavailable or failed:", error.message);
    return {
      error: true,
      message: "Backend unavailable. Please try again later.",
    };
  }
}

export async function playAudioFromUrl(audioUrl) {
  return new Promise((resolve, reject) => {
    const audio = new Audio(audioUrl);

    audio.onended = () => {
      console.log("✅ Audio playback finished.");
      resolve();
    };

    audio.onerror = (e) => {
      console.error("❌ Audio load error:", e);
      reject(new Error("Failed to load audio"));
    };

    audio.play().catch((err) => {
      console.error("❌ Playback failed:", err);
      reject(err);
    });
  });
}
