"use client";

import { useCallback, useRef, useState } from "react";

export function useAudioPlayer() {
  const [isPlaying, setIsPlaying] = useState(false);
  const queueRef = useRef<{ url: string }[]>([]);
  const currentAudioRef = useRef<HTMLAudioElement | null>(null);

  const stop = useCallback(() => {
    queueRef.current.forEach((item) => {
      URL.revokeObjectURL(item.url);
    });
    queueRef.current = [];

    if (currentAudioRef.current) {
      currentAudioRef.current.pause();
      currentAudioRef.current.src = "";
      currentAudioRef.current = null;
    }
    setIsPlaying(false);
  }, []);

  const playNextInQueue = useCallback(() => {
    if (queueRef.current.length === 0) {
      setIsPlaying(false);
      currentAudioRef.current = null;
      return;
    }

    const nextItem = queueRef.current.shift();
    if (!nextItem) {
      setIsPlaying(false);
      return;
    }

    const audio = new Audio(nextItem.url);
    currentAudioRef.current = audio;
    setIsPlaying(true);

    audio.onended = () => {
      URL.revokeObjectURL(nextItem.url);
      playNextInQueue();
    };

    audio.onerror = () => {
      URL.revokeObjectURL(nextItem.url);
      playNextInQueue();
    };

    audio.play().catch(() => {
      URL.revokeObjectURL(nextItem.url);
      playNextInQueue();
    });
  }, []);

  const playAudioChunk = useCallback(
    (base64Audio: string, format = "audio/mpeg") => {
      if (!base64Audio) return;
      try {
        const binaryString = window.atob(base64Audio);
        const bytes = new Uint8Array(binaryString.length);
        for (let index = 0; index < binaryString.length; index += 1) {
          bytes[index] = binaryString.charCodeAt(index);
        }
        const blob = new Blob([bytes], { type: format });
        const url = URL.createObjectURL(blob);

        queueRef.current.push({ url });

        if (!currentAudioRef.current || currentAudioRef.current.ended || currentAudioRef.current.paused) {
          playNextInQueue();
        }
      } catch (caught) {
        console.error("Failed to decode and play audio chunk:", caught);
      }
    },
    [playNextInQueue]
  );

  return { isPlaying, playAudioChunk, stop };
}
