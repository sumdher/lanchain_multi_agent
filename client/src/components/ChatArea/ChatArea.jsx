import React from "react";
import ReactMarkdown from "react-markdown";
import CodeBlock from './CodeBlock';
import './ChatArea.css';

export default function ChatArea({ messages, isTyping, isLoadingContext }) {
    return (
        <div className="chat-area">
            <div className="messages-wrapper">
                <div className="messages">
                    {messages.length === 0 && (
                        <div className="message-row bot">
                            <div className="message-bubble bot welcome-message">
                                <ReactMarkdown>
                                    {"**What can I help with today?**\n\nAsk me anything, and I'll do my best to assist you!"}
                                </ReactMarkdown>
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
                                                return !inline && match ? (
                                                    <CodeBlock language={match[1]} value={codeString} />
                                                ) : (
                                                    <code className={className}>{codeString}</code>
                                                );
                                            }
                                        }}
                                    >
                                        {msg.text}
                                    </ReactMarkdown>
                                ) : msg.text}
                            </div>
                        </div>
                    ))}

                    {isLoadingContext && (
                        <div className="message-row bot">
                            <div className="message-bubble bot">
                                loading files to context...
                            </div>
                        </div>
                    )}

                    {isTyping && <div className="typing">thinking...</div>}
                </div>
            </div>
        </div>
    );
}
