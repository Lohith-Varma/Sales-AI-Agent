"use client";

import { useCallback, useRef, useState } from "react";

type MicrophoneStatus = "idle" | "requesting" | "active" | "error";

function downsampleToPCM16(input: Float32Array, inputRate: number, outputRate = 16_000) {
  if (outputRate > inputRate) throw new Error("The audio input sample rate is below 16 kHz.");
  const ratio = inputRate / outputRate;
  const outputLength = Math.max(1, Math.floor(input.length / ratio));
  const output = new Int16Array(outputLength);
  for (let index = 0; index < outputLength; index += 1) {
    const start = Math.floor(index * ratio);
    const end = Math.min(input.length, Math.floor((index + 1) * ratio));
    let total = 0;
    for (let cursor = start; cursor < end; cursor += 1) total += input[cursor] ?? 0;
    const sample = Math.max(-1, Math.min(1, total / Math.max(1, end - start)));
    output[index] = sample < 0 ? sample * 0x8000 : sample * 0x7fff;
  }
  return output.buffer;
}

export function useMicrophoneStream() {
  const [status, setStatus] = useState<MicrophoneStatus>("idle");
  const [error, setError] = useState<string | null>(null);
  const contextRef = useRef<AudioContext | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const nodeRef = useRef<AudioWorkletNode | null>(null);

  const stop = useCallback(async () => {
    nodeRef.current?.disconnect();
    nodeRef.current = null;
    streamRef.current?.getTracks().forEach((track) => track.stop());
    streamRef.current = null;
    if (contextRef.current && contextRef.current.state !== "closed") await contextRef.current.close();
    contextRef.current = null;
    setStatus("idle");
  }, []);

  const start = useCallback(async (onChunk: (chunk: ArrayBuffer) => void) => {
    if (!navigator.mediaDevices?.getUserMedia) { setError("This browser does not support microphone capture."); setStatus("error"); return; }
    setStatus("requesting");
    setError(null);
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: { channelCount: 1, echoCancellation: true, noiseSuppression: true, autoGainControl: true } });
      const context = new AudioContext({ latencyHint: "interactive" });
      await context.audioWorklet.addModule("/pcm-capture-worklet.js");
      const source = context.createMediaStreamSource(stream);
      const node = new AudioWorkletNode(context, "pcm-capture-processor");
      const mute = context.createGain();
      mute.gain.value = 0;
      node.port.onmessage = (event: MessageEvent<ArrayBuffer>) => onChunk(downsampleToPCM16(new Float32Array(event.data), context.sampleRate));
      source.connect(node).connect(mute).connect(context.destination);
      streamRef.current = stream;
      contextRef.current = context;
      nodeRef.current = node;
      setStatus("active");
    } catch (caught) {
      const message = caught instanceof DOMException && caught.name === "NotAllowedError" ? "Microphone permission was denied." : caught instanceof Error ? caught.message : "The microphone could not be started.";
      setError(message);
      setStatus("error");
      await stop();
      setStatus("error");
    }
  }, [stop]);

  return { status, error, start, stop };
}
