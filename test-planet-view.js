// Test script to verify planet view data structure
const fs = require('fs');
const path = require('path');

// Read the simulated data
const dataPath = path.join(__dirname, '..', 'mcp_servers', 'cockpit_mcp', 'simulated_data.json');
const data = JSON.parse(fs.readFileSync(dataPath, 'utf8'));

console.log('=== Planet View Data Test ===\n');

// Check each galaxy and its planets
Object.keys(data).forEach(galaxyId => {
    const galaxy = data[galaxyId];
    console.log(`Galaxy: ${galaxy.name} (${galaxyId})`);
    
    if (galaxy.planets && galaxy.planets.length > 0) {
        galaxy.planets.forEach(planet => {
            console.log(`  Planet: ${planet.name} (${planet.id})`);
            console.log(`    Status: ${planet.status}`);
            console.log(`    Deployed Score: ${planet.deployedVersion?.evaluation?.score || 'N/A'}`);
            console.log(`    Trace History Count: ${planet.traceHistory?.length || 0}`);
            
            if (planet.traceHistory && planet.traceHistory.length > 0) {
                console.log(`    Top 3 Traces:`);
                const sortedTraces = [...planet.traceHistory]
                    .sort((a, b) => (b.evaluation?.score || 0) - (a.evaluation?.score || 0))
                    .slice(0, 3);
                
                sortedTraces.forEach((trace, index) => {
                    console.log(`      ${index + 1}. ${trace.id} - Score: ${trace.evaluation?.score} - ${trace.text.substring(0, 50)}...`);
                });
            }
            console.log('');
        });
    } else {
        console.log('  No planets found');
    }
    console.log('');
});

console.log('=== Test Complete ===');
console.log('If you see trace history data above, the Planet View should work correctly!'); 