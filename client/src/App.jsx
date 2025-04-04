import { useEffect, useRef, useState } from "react";

function App() {
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const socketRef = useRef(null);

  // Establish WebSocket connection
  useEffect(() => {
    const socket = new WebSocket("ws://localhost:4580/ws/chat");
    socketRef.current = socket;

    socket.onmessage = (event) => {
      if (event.data === "[[END]]") {
        setIsTyping(false);
        return;
      }

      setMessages((prev) => [...prev, { from: "bot", text: event.data }]);
    };

    socket.onopen = () => console.log("✅ WebSocket connected");
    socket.onclose = () => console.log("❌ WebSocket closed");

    return () => socket.close();
  }, []);

  const sendMessage = () => {
    if (!input.trim()) return;

    setMessages((prev) => [...prev, { from: "user", text: input }]);
    socketRef.current.send(input);
    setInput("");
    setIsTyping(true);
  };

  return (
    <div className="min-h-screen bg-gray-100 flex items-center justify-center px-4">
      <div className="w-full max-w-2xl bg-white rounded-lg shadow-lg p-6 flex flex-col space-y-4">
        <h1 className="text-xl font-bold">🧠 LangGraph Chatbot</h1>

        <div className="flex-1 overflow-y-auto max-h-[60vh] space-y-2">
          {messages.map((msg, i) => (
            <div
              key={i}
              className={`p-3 max-w-[80%] rounded-lg ${
                msg.from === "user"
                  ? "bg-blue-100 self-end ml-auto"
                  : "bg-green-100 self-start mr-auto"
              }`}
            >
              {msg.text}
            </div>
          ))}
          {isTyping && <div className="text-sm text-gray-500">Bot is typing...</div>}
        </div>

        <div className="flex space-x-2">
          <input
            className="flex-1 border border-gray-300 p-2 rounded"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && sendMessage()}
            placeholder="Say something..."
          />
          <button
            className="bg-blue-600 text-white px-4 py-2 rounded"
            onClick={sendMessage}
          >
            Send
          </button>
        </div>
      </div>
    </div>
  );
}

export default App;
