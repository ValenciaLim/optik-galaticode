# Planet View - GalactiCode Extension

## Overview

The Planet View is a new feature that extends the existing GalactiCode dashboard to provide detailed visualization and analysis of individual prompts (planets) and their trace history. When users double-click on a planet in Galaxy View, they are transported to a focused 3D scene centered on that specific planet.

## Features

### 3D Planet Scene
- **Central Planet**: The selected prompt is displayed as a large, glowing green sphere at the center
- **Trace Nodes**: Top 10 performing prompt variants are rendered as orbiting satellites around the planet
- **Dynamic Orbits**: Each trace node orbits at a different radius based on its rank (closer = better performance)
- **Rank Labels**: Each trace node displays its rank (#1, #2, etc.) above the sphere

### Real-time Animations
- **New Entry Highlight**: When a new trace enters the top 10, it briefly glows green for 1 second
- **Top Position Highlight**: When a trace takes the #1 spot, it briefly glows gold for 1 second
- **Smooth Transitions**: Camera smoothly transitions between Universe → Galaxy → Planet views

### Interactive Trace Selection
- **Click to Select**: Click any trace node to view its details in the sidebar
- **Hover Effects**: Trace nodes grow slightly when hovered over
- **Dynamic Rankings**: Trace nodes automatically reorder based on performance scores

### Comprehensive Sidebar
- **Deployed Version**: Shows current deployed prompt with full metrics
  - Score, Hallucination %, Latency, Factuality
  - Complete prompt text in scrollable format
- **Selected Variant**: When a trace is clicked, shows detailed comparison
  - Side-by-side metrics comparison
  - Full variant text display
  - Rank information

### Navigation
- **Breadcrumb Navigation**: Universe > Galaxy > Planet hierarchy
- **Back Button**: Easy return to Galaxy view
- **Smooth Camera Transitions**: Automatic camera positioning for optimal viewing

## Technical Implementation

### Components Added
1. **PlanetView**: Main 3D scene for planet-focused view
2. **PlanetSidebar**: UI panel for displaying prompt details and metrics
3. **Enhanced TraceNode**: Improved with animations and rank labels
4. **Updated CameraController**: Handles planet view camera positioning

### State Management
- **View State**: Tracks current view type (universe/galaxy/planet)
- **Selected Trace**: Manages which trace variant is currently selected
- **Animation States**: Tracks new entries and top position changes

### Data Flow
1. **Planet Selection**: Double-click planet → Navigate to planet view
2. **Trace Updates**: WebSocket updates → Recalculate top 10 → Trigger animations
3. **Trace Selection**: Click trace node → Update sidebar with variant details
4. **Navigation**: Back button → Return to galaxy view

## Usage

### Entering Planet View
1. Navigate to a galaxy (double-click space station)
2. Double-click any planet to enter planet view
3. Camera automatically focuses on the planet with trace nodes

### Interacting with Traces
1. Click any orbiting trace node to select it
2. View detailed metrics and text in the sidebar
3. Watch for green/gold highlights when new traces enter top 10

### Navigation
1. Use breadcrumb links to navigate between views
2. Click "Back to Galaxy" button to return to galaxy view
3. Use breadcrumb to jump directly to Universe view

## Styling

The Planet View maintains the existing D3.js visual style with:
- Dark space theme with glowing elements
- Consistent color scheme (green for deployed, blue for UI elements)
- Smooth animations and transitions
- Responsive design for different screen sizes

## Future Enhancements

Potential improvements could include:
- Real-time metric updates with live charts
- Trace comparison tools
- Performance trend visualization
- A/B testing interface for prompt variants
- Export functionality for trace data 