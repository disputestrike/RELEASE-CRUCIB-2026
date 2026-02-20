import { useEffect, useRef, useState } from 'react';

/**
 * VoiceWaveform — canvas-based waveform visualization for voice recording.
 * Per E2E doc Section 05: AnalyserNode + canvas + orange bars + timer + stop/confirm buttons.
 * Adapted to white theme: orange (#FF6B35) bars on white background.
 */
const VoiceWaveform = ({ stream, onStop, onConfirm, isRecording }) => {
  const canvasRef = useRef(null);
  const animFrameRef = useRef(null);
  const analyserRef = useRef(null);
  const [elapsed, setElapsed] = useState(0);
  const timerRef = useRef(null);

  // Timer
  useEffect(() => {
    if (isRecording) {
      setElapsed(0);
      timerRef.current = setInterval(() => {
        setElapsed(prev => prev + 1);
      }, 1000);
    }
    return () => {
      if (timerRef.current) clearInterval(timerRef.current);
    };
  }, [isRecording]);

  // Waveform
  useEffect(() => {
    if (!stream || !canvasRef.current) return;

    const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
    const analyser = audioCtx.createAnalyser();
    analyser.fftSize = 64;
    const source = audioCtx.createMediaStreamSource(stream);
    source.connect(analyser);
    analyserRef.current = analyser;

    const canvas = canvasRef.current;
    const ctx = canvas.getContext('2d');
    const bufferLength = analyser.frequencyBinCount;
    const dataArray = new Uint8Array(bufferLength);

    const draw = () => {
      animFrameRef.current = requestAnimationFrame(draw);
      analyser.getByteFrequencyData(dataArray);

      ctx.clearRect(0, 0, canvas.width, canvas.height);

      const barWidth = (canvas.width / bufferLength) * 0.8;
      const gap = (canvas.width / bufferLength) * 0.2;
      let x = 0;

      for (let i = 0; i < bufferLength; i++) {
        const barHeight = (dataArray[i] / 255) * canvas.height * 0.8;
        const y = (canvas.height - barHeight) / 2;

        ctx.fillStyle = '#FF6B35';
        ctx.beginPath();
        ctx.roundRect(x, y, barWidth, barHeight, 2);
        ctx.fill();

        x += barWidth + gap;
      }
    };

    draw();

    return () => {
      if (animFrameRef.current) cancelAnimationFrame(animFrameRef.current);
      audioCtx.close();
    };
  }, [stream]);

  const formatTime = (seconds) => {
    const m = Math.floor(seconds / 60).toString().padStart(2, '0');
    const s = (seconds % 60).toString().padStart(2, '0');
    return `${m}:${s}`;
  };

  return (
    <div className="voice-waveform-container">
      <div className="voice-waveform-inner">
        <div className="voice-timer">{formatTime(elapsed)}</div>
        <canvas
          ref={canvasRef}
          width={200}
          height={40}
          className="voice-canvas"
        />
        <div className="voice-controls">
          <button
            type="button"
            onClick={onStop}
            className="voice-btn voice-btn-stop"
            title="Cancel recording"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={onConfirm}
            className="voice-btn voice-btn-confirm"
            title="Send recording"
          >
            Send
          </button>
        </div>
      </div>
    </div>
  );
};

export default VoiceWaveform;
