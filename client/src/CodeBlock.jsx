import { useState } from "react";
import { Prism as SyntaxHighlighter } from "react-syntax-highlighter";
import { dracula } from "react-syntax-highlighter/dist/esm/styles/prism";
import { monokai } from 'react-syntax-highlighter/dist/esm/styles/hljs';

export default function CodeBlock({ language = "text", value = "" }) {
    const [copied, setCopied] = useState(false);

    const handleCopy = () => {
        navigator.clipboard.writeText(value);
        setCopied(true);
        setTimeout(() => setCopied(false), 2000);
    };

    return (
        <div style={{
            margin: "1.5em 0",
            borderRadius: "20px",
            overflow: "hidden",
            border: "1px solid #30363d",
            background: "#0d1117"
        }}>
            {/* Header */}
            <div style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                padding: "8px 12px",
                backgroundColor: "#161b22",
                borderBottom: "1px solid #30363d",
                color: "#c9d1d9",
                fontSize: "1rem",
                fontFamily: "monospace",
                paddingLeft: "20px"
            }}>
                <span>{language}</span>
                <button
                    onClick={handleCopy}
                    style={{
                        background: "transparent",
                        color: "#d9d9d9",
                        border: "none",
                        fontSize: "0.8rem",
                        cursor: "pointer",
                        padding: "2px 6px",
                    }}
                >
                    {copied ? "Copied!" : "Copy"}
                </button>
            </div>

            {/* Code area */}
            <SyntaxHighlighter
                language={language}
                style={dracula}
                customStyle={{
                    margin: 0,
                    padding: "1rem",
                    fontSize: "01.2rem",
                    lineHeight: "1.5",
                    background: "transparent",
                }}
                codeTagProps={{
                    style: {
                        display: "block",
                        paddingLeft: 0,
                        marginLeft: 0,
                        textIndent: 0,
                        whiteSpace: "pre",
                        background: "transparent",
                    }
                }}
                showLineNumbers={false}
            >
                {value}
            </SyntaxHighlighter>
        </div>
    );
}
