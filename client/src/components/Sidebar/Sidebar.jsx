import React, { useState } from "react";
import './Sidebar.css';

export default function Sidebar({ loadedKeys, setLoadedKeys, socketRef }) {
    const [uploadedFiles, setUploadedFiles] = useState([]);
    const [fileMap, setFileMap] = useState({});
    // const [loadDisabled, setLoadDisabled] = useState(true);

    const handleFileUpload = async (event) => {
        const files = Array.from(event.target.files);
        if (files.length === 0) return;

        const formData = new FormData();
        files.forEach(file => formData.append("files", file));

        try {
            const response = await fetch("http://localhost:4580/upload", {
                method: "POST",
                body: formData
            });

            if (response.ok) {
                const data = await response.json();
                const keyMap = data.file_map;

                setUploadedFiles(prev => [...prev, ...files]);

                const updatedMap = { ...fileMap };
                for (const [key, name] of Object.entries(keyMap)) {
                    updatedMap[key] = name;
                }

                setFileMap(updatedMap);
                // setLoadDisabled(false);
            } else {
                alert("Failed to upload files");
            }
        } catch (error) {
            console.error("Upload error:", error);
        }
    };

    const handleAddToContext = () => {
        console.log("SocketRef in Sidebar: ", socketRef?.current);
        if (socketRef?.current) {
            socketRef.current.send("__CONTEXT__");
        }
    };

    const handleDeleteFile = async (key, index) => {
        const formData = new FormData();
        formData.append("file_key", key);

        const response = await fetch("http://localhost:4580/delete-file", {
            method: "POST",
            body: formData
        });

        if (response.ok) {
            const updatedFiles = [...uploadedFiles];
            updatedFiles.splice(index, 1);
            setUploadedFiles(updatedFiles);

            const updatedMap = { ...fileMap };
            delete updatedMap[key];
            setFileMap(updatedMap);
        }
    };

    return (
        <aside className="sidebar">
            <h2 className="sidebar-title">🧠 Chat SkiBiDi</h2>

            <nav className="sidebar-nav">
                <a href="#">Chat</a>
                <a href="#">Modes</a>
                <a href="#">Settings</a>
            </nav>

            <div className="file-upload-box">
                <h4>📁 Files</h4>

                <div className="file-list">
                    {uploadedFiles.map((file, idx) => {
                        // Match against original file name for grey-out
                        const isLoaded = loadedKeys.has(file.name);
                        const key = Object.keys(fileMap).find(k => fileMap[k] === file.name);

                        return (
                            <div key={idx} className="file-entry" style={{ opacity: isLoaded ? 0.5 : 1 }}>
                                <span role="img" aria-label="file">📄</span>
                                <div className="file-name">
                                    {file.name.length > 15
                                        ? `${file.name.slice(0, 10)}...${file.name.slice(-5)}`
                                        : file.name}
                                </div>
                                {!isLoaded && (
                                    <button
                                        className="delete-btn"
                                        onClick={() => handleDeleteFile(key, idx)}
                                    >✖</button>
                                )}
                            </div>
                        );
                    })}
                </div>

                <input
                    id="file-upload"
                    type="file"
                    multiple
                    accept=".txt,.pdf,.doc,.docx"
                    style={{ display: 'none' }}
                    onChange={handleFileUpload}
                />
                <div className="button-row">
                    <label htmlFor="file-upload" className="file-button">
                        Add Files
                    </label>
                    <button
                        className="load-button"
                        disabled={
                            // true
                            uploadedFiles.length === 0 || uploadedFiles.every(file => loadedKeys.has(file.name))
                        }
                        onClick={handleAddToContext}
                    >
                        Load to Context
                    </button>
                </div>
            </div>
        </aside>
    );
}