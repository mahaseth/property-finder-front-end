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
  formData.append('file', audioBlob, 'userAudio.wav');

  // const response = await fetch('http://127.0.0.1:8000/process-audio', {
  //   method: 'POST',
  //   body: formData,
  // });

  const response = await fetch('http://127.0.0.1:8000', {
    method: 'GET'
  });


  if (!response.ok) {
    console.error("❌ Backend processing failed");
    throw new Error("Backend error");
  }

  const result = await response.json();
  console.log("✅ Backend response:", result);

  // Compose audio URL to play
  const audioFileUrl = `http://127.0.0.1:8000/audio/${result.audio_file}`;
  return audioFileUrl;
}





// Play audio from a given URL once and resolve only after playback completes
export async function playAudioFromUrl(audioUrl) {
  return new Promise((resolve, reject) => {
    const audio = new Audio(audioUrl);

    audio.onended = () => {
      console.log("✅ Audio playback finished.");
      resolve(); // Only then continue to next recording cycle
    };

    audio.onerror = (e) => {
      console.error("❌ Audio load error:", e);
      reject(new Error("Failed to load audio"));
    };

    // Attempt to play audio
    audio.play().catch((err) => {
      console.error("❌ Playback failed:", err);
      reject(err);
    });
  });
}

