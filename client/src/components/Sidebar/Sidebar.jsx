import React, { useState } from "react";
import './Sidebar.css';

export default function Sidebar() {
    const [uploadedFiles, setUploadedFiles] = useState([]);
    const [fileMap, setFileMap] = useState({});
    const [loadDisabled, setLoadDisabled] = useState(true);

    const handleFileUpload = async (event) => {
        const files = Array.from(event.target.files);
        if (files.length === 0) return;

        const formData = new FormData();
        const newMap = { ...fileMap };

        files.forEach((file, index) => {
            const key = `${Date.now()}_${file.name}`;
            formData.append("files", file);
            newMap[key] = file.name;
        });

        try {
            const response = await fetch("http://localhost:4580/upload", {
                method: "POST",
                body: formData
            });

            if (response.ok) {
                setUploadedFiles(prev => [...prev, ...files]);
                setFileMap(newMap);
                setLoadDisabled(false);
            } else {
                alert("Failed to upload files");
            }
        } catch (error) {
            console.error("Upload error:", error);
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
            <h4>📁 Uploaded Files</h4>

            <div className="file-list">
                {uploadedFiles.map((file, idx) => (
                    <div key={idx} className="file-entry">
                        <span role="img" aria-label="file">📄</span>
                        <div className="file-name">
                            {file.name.length > 15
                                ? `${file.name.slice(0, 10)}...${file.name.slice(-5)}`
                                : file.name}
                        </div>
                    </div>
                ))}
            </div>

            {/* Hidden input and external label for better control */}
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
                    disabled={loadDisabled}
                    className="load-button"
                >
                    Load to Context
                </button>
            </div>
        </div>
    </aside>
);


}
