// InputArea.jsx
import React from "react";
import './InputArea.css';

export default function InputArea({ input, setInput, sendMessage, stopAI, isTyping }) {
    return (
        <div className="input-area">
            <textarea
                className="input-field"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={(e) => {
                    if (e.key === "Enter" && !e.shiftKey) {
                        e.preventDefault();
                        sendMessage();
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
    );
}
