import React, { useState } from 'react';
import './OnboardingForm.css';

const opik_METRICS = [
    "factuality", "hallucination", "latency", "toxicity", 
    "verbosity", "user_sentiment", "custom_metric_1"
];

function OnboardingForm({ onOnboard, onClose }) {
    const [agentName, setAgentName] = useState('');
    const [apiUrl, setApiUrl] = useState('');
    const [authToken, setAuthToken] = useState('');
    const [selectedMetrics, setSelectedMetrics] = useState([]);

    const handleMetricChange = (metric) => {
        setSelectedMetrics(prev =>
            prev.includes(metric)
                ? prev.filter(m => m !== metric)
                : [...prev, metric]
        );
    };

    const handleSubmit = async (e) => {
        e.preventDefault();
        const agentId = agentName.toLowerCase().replace(/\s+/g, '-');
        
        const payload = {
            id: agentId,
            name: agentName,
            apiUrl,
            authToken,
            opikMetrics: selectedMetrics
        };

        try {
            const response = await fetch('http://localhost:8080/api/onboard', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(payload)
            });

            if (response.ok) {
                onOnboard(payload);
                onClose();
            } else {
                const errorText = await response.text();
                alert(`Onboarding failed: ${errorText}`);
            }
        } catch (error) {
            console.error("Onboarding API error:", error);
            alert("Onboarding failed due to a network or server error.");
        }
    };

    return (
        <div className="modal-overlay">
            <div className="modal-content">
                <form onSubmit={handleSubmit} className="onboarding-form">
                    <h3>Onboard New AI Agent</h3>
                    
                    <label htmlFor="agentName">Agent Name</label>
                    <input
                        id="agentName"
                        type="text"
                        value={agentName}
                        onChange={(e) => setAgentName(e.target.value)}
                        placeholder="e.g., Customer Support Bot"
                        required
                    />

                    <label htmlFor="apiUrl">Telemetry API Endpoint</label>
                    <input
                        id="apiUrl"
                        type="url"
                        value={apiUrl}
                        onChange={(e) => setApiUrl(e.target.value)}
                        placeholder="https://api.my-agent.com/telemetry"
                        required
                    />

                    <label htmlFor="authToken">Auth Token</label>
                    <input
                        id="authToken"
                        type="password"
                        value={authToken}
                        onChange={(e) => setAuthToken(e.target.value)}
                        placeholder="e.g., sk-xxxxxxxx"
                    />

                    <fieldset>
                        <legend>Select opik Evaluation Metrics</legend>
                        <div className="metrics-grid">
                            {opik_METRICS.map(metric => (
                                <div key={metric} className="metric-item">
                                    <input
                                        type="checkbox"
                                        id={`metric-${metric}`}
                                        checked={selectedMetrics.includes(metric)}
                                        onChange={() => handleMetricChange(metric)}
                                    />
                                    <label htmlFor={`metric-${metric}`}>{metric}</label>
                                </div>
                            ))}
                        </div>
                    </fieldset>

                    <div className="form-actions">
                        <button type="button" onClick={onClose} className="btn-cancel">Cancel</button>
                        <button type="submit" className="btn-submit">Onboard Agent</button>
                    </div>
                </form>
            </div>
        </div>
    );
}

export default OnboardingForm; 