// Sidebar.jsx
import React from "react";
import './Sidebar.css';

export default function Sidebar() {
    return (
        <aside className="sidebar">
            <h2 className="sidebar-title">🧠 Chat SkiBiDi</h2>
            <nav className="sidebar-nav">
                <a href="#">Chat</a>
                <a href="#">Modes</a>
                <a href="#">Settings</a>
            </nav>
        </aside>
    );
}
