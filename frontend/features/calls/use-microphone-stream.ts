"use client";

import { useCallback, useRef, useState } from "react";

type MicrophoneStatus = "idle" | "requesting" | "active" | "error";

const OUTPUT_SAMPLE_RATE = 16_000;
const FRAME_DURATION_MS = 100;
const SILENCE_DURATION_MS = 700;
const MIN_SPEECH_DURATION_MS = 250;
const SILENCE_RMS_THRESHOLD = 0.012;

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
  const pendingSamplesRef = useRef<Int16Array[]>([]);
  const pendingSampleCountRef = useRef(0);
  const speechSamplesRef = useRef(0);
  const silenceSamplesRef = useRef(0);
  const onChunkRef = useRef<((chunk: ArrayBuffer) => void) | null>(null);
  const onUtteranceEndRef = useRef<(() => void) | null>(null);

  const finishUtterance = useCallback(() => {
    if (speechSamplesRef.current >= OUTPUT_SAMPLE_RATE * MIN_SPEECH_DURATION_MS / 1_000) {
      onUtteranceEndRef.current?.();
    }
    speechSamplesRef.current = 0;
    silenceSamplesRef.current = 0;
  }, []);

  const flushFrames = useCallback(() => {
    const frameSamples = OUTPUT_SAMPLE_RATE * FRAME_DURATION_MS / 1_000;
    if (pendingSampleCountRef.current < frameSamples) return;
    const merged = new Int16Array(pendingSampleCountRef.current);
    let offset = 0;
    for (const samples of pendingSamplesRef.current) {
      merged.set(samples, offset);
      offset += samples.length;
    }
    let consumed = 0;
    while (merged.length - consumed >= frameSamples) {
      const frame = merged.slice(consumed, consumed + frameSamples);
      onChunkRef.current?.(frame.buffer);
      let energy = 0;
      for (const sample of frame) energy += (sample / 32768) ** 2;
      const isSpeech = Math.sqrt(energy / frame.length) >= SILENCE_RMS_THRESHOLD;
      if (isSpeech) {
        speechSamplesRef.current += frame.length;
        silenceSamplesRef.current = 0;
      } else if (speechSamplesRef.current > 0) {
        silenceSamplesRef.current += frame.length;
        if (silenceSamplesRef.current >= OUTPUT_SAMPLE_RATE * SILENCE_DURATION_MS / 1_000) finishUtterance();
      }
      consumed += frameSamples;
    }
    const remainder = merged.slice(consumed);
    pendingSamplesRef.current = remainder.length ? [remainder] : [];
    pendingSampleCountRef.current = remainder.length;
  }, [finishUtterance]);

  const stop = useCallback(async () => {
    flushFrames();
    finishUtterance();
    nodeRef.current?.disconnect();
    nodeRef.current = null;
    streamRef.current?.getTracks().forEach((track) => track.stop());
    streamRef.current = null;
    if (contextRef.current && contextRef.current.state !== "closed") await contextRef.current.close();
    contextRef.current = null;
    pendingSamplesRef.current = [];
    pendingSampleCountRef.current = 0;
    onChunkRef.current = null;
    onUtteranceEndRef.current = null;
    setStatus("idle");
  }, [finishUtterance, flushFrames]);

  const start = useCallback(async (onChunk: (chunk: ArrayBuffer) => void, onUtteranceEnd?: () => void) => {
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
      onChunkRef.current = onChunk;
      onUtteranceEndRef.current = onUtteranceEnd ?? null;
      node.port.onmessage = (event: MessageEvent<ArrayBuffer>) => {
        const samples = new Int16Array(downsampleToPCM16(new Float32Array(event.data), context.sampleRate));
        pendingSamplesRef.current.push(samples);
        pendingSampleCountRef.current += samples.length;
        flushFrames();
      };
      source.connect(node).connect(mute).connect(context.destination);
      streamRef.current = stream;
      contextRef.current = context;
      nodeRef.current = node;
      setStatus("active");
    } catch (caught) {
      let message = "The microphone could not be started.";
      if (caught instanceof DOMException) {
        if (caught.name === "NotAllowedError" || caught.name === "PermissionDeniedError") {
          message = "Microphone permission denied. Please allow microphone access in your browser settings.";
        } else if (caught.name === "NotFoundError" || caught.name === "DevicesNotFoundError") {
          message = "No microphone device detected.";
        } else {
          message = caught.message;
        }
      } else if (caught instanceof Error) {
        message = caught.message;
      }
      setError(message);
      setStatus("error");
      await stop();
      setStatus("error");
    }
  }, [flushFrames, stop]);

  return { status, error, start, stop };
}
