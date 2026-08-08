"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import type { AIClientControlMessage, AIServerEvent } from "@/lib/api/contracts";
import { parseAIServerEvent } from "@/lib/api/events";

export type SocketStatus = "idle" | "connecting" | "connected" | "reconnecting" | "error" | "closed";

interface SocketCallbacks {
  onEvent: (event: AIServerEvent) => void;
  onSessionReset?: () => void;
}

export function useCopilotSocket({ onEvent, onSessionReset }: SocketCallbacks) {
  const [status, setStatus] = useState<SocketStatus>("idle");
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const socketRef = useRef<WebSocket | null>(null);
  const manualClose = useRef(false);
  const retryCount = useRef(0);
  const reconnectTimer = useRef<ReturnType<typeof setTimeout> | null>(null);
  const heartbeatTimer = useRef<ReturnType<typeof setInterval> | null>(null);
  const lastPongAt = useRef(0);
  const startMessage = useRef<AIClientControlMessage | null>(null);
  const callbacks = useRef({ onEvent, onSessionReset });
  callbacks.current = { onEvent, onSessionReset };

  const openSocket = useCallback(() => {
    const message = startMessage.current;
    if (!message) return;
    const url = process.env.NEXT_PUBLIC_AI_WS_URL ? `${process.env.NEXT_PUBLIC_AI_WS_URL.replace(/\/$/, "")}/ws/copilot` : "ws://127.0.0.1:8000/ws/copilot";
    setStatus(retryCount.current ? "reconnecting" : "connecting");
    setError(null);
    const socket = new WebSocket(url);
    socket.binaryType = "arraybuffer";
    socketRef.current = socket;
    socket.onopen = () => socket.send(JSON.stringify(message));
    socket.onmessage = (messageEvent) => {
      if (typeof messageEvent.data !== "string") return;
      try {
        const event = parseAIServerEvent(messageEvent.data);
        if (event.type === "session_ready") {
          if (retryCount.current > 0) callbacks.current.onSessionReset?.();
          retryCount.current = 0;
          setSessionId(event.session_id);
          setStatus("connected");
          lastPongAt.current = Date.now();
          if (heartbeatTimer.current) clearInterval(heartbeatTimer.current);
          heartbeatTimer.current = setInterval(() => {
            const active = socketRef.current;
            if (!active || active.readyState !== WebSocket.OPEN) return;
            if (Date.now() - lastPongAt.current > 35_000) { active.close(4000, "Heartbeat timed out"); return; }
            active.send(JSON.stringify({ type: "ping", nonce: String(Date.now()) }));
          }, 15_000);
        } else if (event.type === "error") {
          setError(event.message);
        } else if (event.type === "pong") lastPongAt.current = Date.now();
        callbacks.current.onEvent(event);
      } catch (caught) {
        setError(caught instanceof Error ? caught.message : "A realtime event could not be read.");
      }
    };
    socket.onerror = () => { setError("The AI realtime service could not be reached."); setStatus("error"); };
    socket.onclose = () => {
      if (heartbeatTimer.current) { clearInterval(heartbeatTimer.current); heartbeatTimer.current = null; }
      socketRef.current = null;
      setSessionId(null);
      if (manualClose.current) { setStatus("closed"); return; }
      if (retryCount.current >= 4) { setStatus("error"); setError("Realtime reconnection stopped after several attempts."); return; }
      retryCount.current += 1;
      setStatus("reconnecting");
      reconnectTimer.current = setTimeout(openSocket, Math.min(1000 * 2 ** (retryCount.current - 1), 8000));
    };
  }, []);

  const connect = useCallback((input: { salesAgentId: string; leadId?: string; accessToken?: string }) => {
    manualClose.current = false;
    retryCount.current = 0;
    startMessage.current = { type: "session_start", sales_agent_id: input.salesAgentId, external_lead_id: input.leadId, access_token: input.accessToken, language: "en", audio_config: { encoding: "pcm_s16le", sample_rate_hz: 16_000, channels: 1, sample_width_bytes: 2 } };
    socketRef.current?.close();
    openSocket();
  }, [openSocket]);

  const sendControl = useCallback((message: AIClientControlMessage) => {
    if (socketRef.current?.readyState !== WebSocket.OPEN) return false;
    socketRef.current.send(JSON.stringify(message));
    return true;
  }, []);

  const sendAudio = useCallback((audio: ArrayBuffer) => {
    if (socketRef.current?.readyState !== WebSocket.OPEN) return false;
    socketRef.current.send(audio);
    return true;
  }, []);

  const disconnect = useCallback(() => {
    manualClose.current = true;
    if (reconnectTimer.current) clearTimeout(reconnectTimer.current);
    if (heartbeatTimer.current) { clearInterval(heartbeatTimer.current); heartbeatTimer.current = null; }
    socketRef.current?.close(1000, "Call workspace closed");
    socketRef.current = null;
    setSessionId(null);
    setStatus("closed");
  }, []);

  useEffect(() => () => disconnect(), [disconnect]);
  return { status, sessionId, error, connect, disconnect, sendControl, sendAudio };
}
