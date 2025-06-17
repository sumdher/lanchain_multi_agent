// App.jsx
import { useRef, useState } from "react";
import Sidebar from "./components/Sidebar/Sidebar";
import Header from "./components/Header/Header";
import ChatArea from "./components/ChatArea/ChatArea";
import InputArea from "./components/InputArea/InputArea";
import './index.css';

export default function App() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const [isConnected, setIsConnected] = useState(false);
  const [isConnecting, setIsConnecting] = useState(false);
  const socketRef = useRef(null);
  const [loadedKeys, setLoadedKeys] = useState(new Set());
  const [isLoadingContext, setIsLoadingContext] = useState(false);

  const connectToLangGraph = () => {
    setIsConnecting(true);
    const socket = new WebSocket("ws://127.0.0.1:4580/ws/chat");
    socketRef.current = socket;

    socket.onmessage = (event) => {
      const chunk = event.data;

      if (chunk === "[[END]]") {
        setIsTyping(false);
        setIsLoadingContext(false);
        return;
      }

      if (chunk.startsWith("[[LOADED::")) {
        const loadedList = chunk.replace("[[LOADED::", "").replace("]]", "").split(",");
        setLoadedKeys(prev => new Set([...prev, ...loadedList]));
        setIsLoadingContext(true);
        return;
      }

      // Normal bot message logic
      setMessages((prev) => {
        const last = prev[prev.length - 1];
        if (last?.from === "bot") {
          const updated = [...prev];
          updated[updated.length - 1] = { ...last, text: last.text + chunk };
          return updated;
        }
        return [...prev, { from: "bot", text: chunk }];
      });

      setIsTyping(true);
    };

    socket.onopen = () => {
      console.log("✅ WebSocket connected");
      setIsConnected(true);
      setIsConnecting(false);
    };

    socket.onclose = () => {
      console.log("❌ WebSocket closed");
      setIsConnected(false);
      setIsConnecting(false);
    };

    socket.onerror = () => {
      setIsConnecting(false);
    };
  };

  const stopAI = () => {
    if (socketRef.current?.readyState === 1) {
      socketRef.current.send("__STOP__");
      setIsTyping(false);
    }
  };

  const sendMessage = () => {
    if (!input.trim() || isTyping || socketRef.current.readyState !== 1) return;
    setMessages((prev) => [...prev, { from: "user", text: input }]);
    socketRef.current.send(input);
    setInput("");
    setIsTyping(true);
  };

  return (
    <div className="app-container">
      <Sidebar
        loadedKeys={loadedKeys}
        setLoadedKeys={setLoadedKeys}
        socketRef={socketRef}
        isLoadingContext={isLoadingContext}
        setIsLoadingContext={setIsLoadingContext}
      />
      <div className="main">
        <Header />
        {!isConnected ? (
          <div className="connect-screen">
            <button
              className={`connect-button ${isConnecting ? 'connecting' : ''}`}
              onClick={connectToLangGraph}
              disabled={isConnecting}
            >
              {isConnecting ? 'Connecting...' : 'Connect to DeepSeek-V3'}
            </button>
          </div>
        ) : (
          <>
            <ChatArea
              messages={messages}
              isTyping={isTyping}
              isLoadingContext={isLoadingContext}
            />
            <InputArea
              input={input}
              setInput={setInput}
              sendMessage={sendMessage}
              stopAI={stopAI}
              isTyping={isTyping}
            />
          </>
        )}
      </div>
    </div>
  );
}
