// App.jsx

import { useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import './index.css';
import CodeBlock from './CodeBlock';


export default function App() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const [isConnected, setIsConnected] = useState(false);
  const [isConnecting, setIsConnecting] = useState(false);
  const socketRef = useRef(null);
  const messagesEndRef = useRef(null);

  const connectToLangGraph = () => {
    setIsConnecting(true);
    const socket = new WebSocket("ws://127.0.0.1:4580/ws/chat");
    socketRef.current = socket;

    let botBuffer = "";

    socket.onmessage = (event) => {
      const chunk = event.data;

      if (chunk === "[[END]]") {
        setIsTyping(false);
        return;
      }

      botBuffer += chunk;

      setMessages((prev) => {
        const last = prev[prev.length - 1];

        if (last?.from === "bot") {
          // Append new chunk to existing bot message
          const updated = [...prev];
          updated[updated.length - 1] = {
            ...last,
            text: last.text + chunk,
          };
          return updated;
        } else {
          // New bot message starts here
          return [...prev, { from: "bot", text: chunk }];
        }
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
  
  function sanitizeMarkdown(markdown) {
    return markdown
      .replace(/```(\w*)[ \t]*([^\n])/g, '```$1\n$2')
      .replace(/([^\n])```/g, '$1\n```');
  }
  const stopAI = () => {
    if (socketRef.current && socketRef.current.readyState === 1) {
      socketRef.current.send("__STOP__");
      setIsTyping(false);
    }
  };

  // useEffect(() => {
  //   messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  // }, [messages]);

  useEffect(() => {
    const textarea = document.querySelector(".input-field");
    if (textarea) {
      textarea.style.height = "auto";
      textarea.style.height = Math.min(textarea.scrollHeight, 8 * 24) + "px";
    }
  }, [input]);

  const sendMessage = () => {
    if (!input.trim() || isTyping || socketRef.current.readyState !== 1) return;
    setMessages((prev) => [...prev, { from: "user", text: input }]);
    socketRef.current.send(input);
    setInput("");
    setIsTyping(true);
  };


  return (
    <div className="app-container">
      <aside className="sidebar">
        <h2 className="sidebar-title">🧠 Chat SkiBiDi</h2>
        <nav className="sidebar-nav">
          <a href="#">Chat</a>
          <a href="#">Modes</a>
          <a href="#">Settings</a>
        </nav>
      </aside>

      <div className="main">
        <header className="header">
          <h1 className="header-title">DeepSeek-V3 LLM</h1>
        </header>

        <main className="chat-area">
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
              <div className="messages-wrapper">
                <div className="messages">
                  {/* Welcome message */}
                  {messages.length === 0 && (
                    <div className="message-row bot">
                      <div className="message-bubble bot welcome-message">
                        <ReactMarkdown>{"**What can I help with today?**\n\nAsk me anything, and I'll do my best to assist you!"}</ReactMarkdown>
                      </div>
                    </div>
                  )}

                  {messages.map((msg, i) => (
                    <div key={i} className={`message-row ${msg.from}`}>
                      <div className={`message-bubble ${msg.from}`}>
                        {msg.from === "bot" ? (
                          <ReactMarkdown
                            components={{
                              code({ inline, className, children }) {
                                const match = /language-(\w+)/.exec(className || "");
                                const codeString = String(children).trim();

                                if (!inline && match) {
                                  return <CodeBlock language={match[1]} value={codeString} />;
                                }

                                return <code className={className}>{codeString}</code>;
                              },
                            }}
                          >
                            {msg.text}
                          </ReactMarkdown>
                        ) : (
                          msg.text
                        )}
                      </div>
                    </div>
                  ))}
                  {isTyping && <div className="typing">thinking...</div>}
                  <div ref={messagesEndRef} />
                </div>
              </div>
              <div className="input-area">
                <textarea
                  className="input-field"
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter" && !e.shiftKey) {
                      e.preventDefault(); // Prevents newline
                      sendMessage();      // Sends message only if Shift is NOT pressed
                    }
                  }}
                  placeholder="Type your message..."
                  rows={1}
                />
                <button
                  className="send-button"
                  onClick={isTyping ? stopAI : sendMessage}
                  disabled={!input.trim() && !isTyping}
                >
                  {isTyping ? "Stop" : "Send"}
                </button>

              </div>
            </>
          )}
        </main>
      </div>
    </div>
  );
}