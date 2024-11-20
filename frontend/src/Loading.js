// // src/Loading.js

import React, { useState, useEffect } from 'react';
import socket from './socket';
import './Loading.css';

const Loading = () => {
    const [players, setPlayers] = useState([]);

    useEffect(() => {
        // Mock function to simulate fetching players
        const fetchPlayers = () => {
            // This should be replaced with actual logic to fetch players
            setPlayers(['Player 1', 'Player 2', 'Player 3']);
        };

        fetchPlayers();

        // Optionally, set up a socket listener or polling to update players
        socket.on('playersUpdated', (newPlayers) => {
            setPlayers(newPlayers);
        });

        // Clean up the event listener on unmount
        return () => {
            socket.off('playersUpdated');
        };
    }, []);

    return (
        <div className="loading-container">
            <p className="loading-message">Waiting for Admin to Start the Game...</p>
            <span className="loading-emoji">😄</span>
            <div className="lobby-players">
                <h3>Players in Lobby:</h3>
                <ul className="player-list">
                    {players.map((player, index) => (
                        <li key={index} className="player-item">{player}</li>
                    ))}
                </ul>
            </div>
        </div>
    );
};

export default Loading;
