import React, { useState, useEffect } from 'react';
import './MetricConfig.css';

const AVAILABLE_METRICS = [
    "", "score", "factuality", "hallucination", "speed", "toxicity", 
    "verbosity", "user_sentiment", "custom_metric_1"
];

const VISUAL_PROPERTIES = [
    { key: "planetSize", label: "Planet Size" },
    { key: "planetPosition", label: "Planet Position" },
    { key: "planetSpeed", label: "Planet Speed" }
];

function MetricConfig({ galaxy, onUpdateMapping }) {
    const [metricMapping, setMetricMapping] = useState({});
    const [isEditing, setIsEditing] = useState(false);

    useEffect(() => {
        if (galaxy?.config?.metricMapping) {
            setMetricMapping(galaxy.config.metricMapping);
        } else {
            // Default mapping
            setMetricMapping({
                planetSize: "score",
                planetPosition: "score"
            });
        }
    }, [galaxy]);

    const handleMetricChange = (property, metric) => {
        setMetricMapping(prev => {
            const newMapping = { ...prev };
            if (metric === "empty") {
                // Remove the property when empty is selected
                delete newMapping[property];
            } else {
                // Set the property when a metric is selected
                newMapping[property] = metric;
            }
            return newMapping;
        });
    };

    const handleSave = async () => {
        try {
            const response = await fetch(`http://localhost:8080/api/agent/${galaxy.id}/metric_mapping`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ metricMapping })
            });

            if (response.ok) {
                onUpdateMapping(metricMapping);
                setIsEditing(false);
            } else {
                const errorText = await response.text();
                alert(`Failed to update metric mapping: ${errorText}`);
            }
        } catch (error) {
            console.error("Metric mapping API error:", error);
            alert("Failed to update metric mapping due to a network or server error.");
        }
    };

    const handleCancel = () => {
        // Reset to original values
        if (galaxy?.config?.metricMapping) {
            setMetricMapping(galaxy.config.metricMapping);
        }
        setIsEditing(false);
    };

    if (!galaxy) return null;

    // Get planet status information for all planets in the galaxy
    const getPlanetStatuses = () => {
        if (!galaxy.planets || galaxy.planets.length === 0) {
            return [{ status: "No prompts", prompt: "N/A", health: "N/A" }];
        }
        
        return galaxy.planets.map((planet, index) => {
            const evaluation = planet.deployedVersion?.evaluation || {};
            const health = evaluation.score ? `${(evaluation.score * 100).toFixed(1)}%` : "N/A";
            
            return {
                id: planet.id || index,
                status: planet.status || "Unknown",
                prompt: planet.deployedVersion?.text || "N/A",
                health: health,
                lastUpdated: planet.deployedVersion?.timestamp || "N/A"
            };
        });
    };

    const planetStatuses = getPlanetStatuses();

    return (
        <div className="metric-config">
            <div className="metric-config-header">
                <h4>Metric Mapping</h4>
                {!isEditing ? (
                    <button onClick={() => setIsEditing(true)} className="edit-btn">Edit</button>
                ) : (
                    <div className="edit-actions">
                        <button onClick={handleSave} className="save-btn">Save</button>
                        <button onClick={handleCancel} className="cancel-btn">Cancel</button>
                    </div>
                )}
            </div>
            
            <div className="metric-mappings">
                {VISUAL_PROPERTIES.map(property => (
                    <div key={property.key} className="metric-mapping-item">
                        <label>{property.label}:</label>
                        {isEditing ? (
                            <select
                                value={metricMapping[property.key] || ""}
                                onChange={(e) => handleMetricChange(property.key, e.target.value)}
                                className="metric-select"
                            >
                                {AVAILABLE_METRICS.map(metric => (
                                    <option key={metric} value={metric}>
                                        {metric}
                                    </option>
                                ))}
                            </select>
                        ) : (
                            <span className="metric-value">
                                {metricMapping[property.key] || ""}
                            </span>
                        )}
                    </div>
                ))}
            </div>
            
            <div className="metric-info">
                <small>
                    <strong>Prompts ({planetStatuses.length}):</strong><br/>
                    {planetStatuses.map((status, index) => (
                        <div key={status.id} className="prompt-status">
                            <strong>Prompt {index + 1}:</strong><br/>
                            <strong>Health:</strong> {status.health}<br/>
                            <strong>Status:</strong> {status.status}<br/>
                            <strong>Updated:</strong> {new Date(status.lastUpdated).toLocaleString()}<br/>
                            {index < planetStatuses.length - 1 && <hr/>}
                        </div>
                    ))}
                </small>
            </div>
        </div>
    );
}

export default MetricConfig; 