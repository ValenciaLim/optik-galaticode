# GalactiCode: The AI Agent Cockpit for Comet Opik

Welcome to GalactiCode, a dynamic 3D monitoring and management dashboard for your AI agents. This application provides a celestial-themed interface to visualize, test, and optimize your AI prompts in real-time. Each AI agent is represented as a galaxy, with its various prompt families orbiting as planets, allowing for intuitive navigation and control of your entire AI ecosystem.

## ✨ Features

*   **3-Tier View System:** Navigate from a high-level Universe View of all agents, down to a Galaxy View of a single agent's prompts, and finally to the Planet View to analyze individual prompt variants.
*   **Interactive 3D Visualization:** Navigate your AI agent ecosystem in a fluid, intuitive 3D space powered by React Three Fiber.
*   **Real-time Monitoring:** Live updates are pushed from the backend via WebSockets, ensuring the cockpit always reflects the current state of your agents.
*   **Prompt A/B Testing:** Initiate on-the-fly optimization tasks to test different prompt variants and automatically identify top performers.

## 🔭 Core Views

The GalactiCode experience is built around a three-tiered hierarchy of views, allowing you to seamlessly zoom from a high-level overview to the most granular details of a single prompt.

### 🌌 Universe View

The Universe View is your landing page and the highest-level dashboard. It provides a complete overview of all your onboarded AI agents.

*   **Representation:** Each star system in this view is a **Galaxy**, representing a distinct AI agent.
*   **Interaction:**
    *   Pan, zoom, rotate, re-position to explore your universe of agents.
    *   The central star of each system indicates the agent's overall status (e.g., green for stable, yellow for optimizing, red for critical).
    *   Use the **Control Panel** to search for specific agents or filter them by health status.
    *   Double-clicking a galaxy's central star takes you into the **Galaxy View**.
    *   **Try For Fun!** Change the planet to Pokemon-planets or Cat-planets using the **Control Panel**

👉 [**Universe View Demo**](https://www.loom.com/share/12e8af9f254e456bbbe49bca7ceed528?sid=0de88bd7-f394-498e-b4de-1cf8dbac941f)

### 🪐 Galaxy View

The Galaxy View focuses on a single AI agent, providing a detailed look at its constituent parts.

*   **Representation:** This view represents a single AI agent. The central star is the agent itself, and the orbiting bodies are its **Planets**. Each planet corresponds to a specific prompt family, task, or use case that the agent handles.
*   **Interaction:**
    *   The camera zooms in to focus on the selected agent.
    *   See all the agent's planets orbiting the central star. The orbital distance and size of each planet can be dynamically mapped to performance metrics.
    *   Clicking the central star allows you to configure the agent's **Metric Mapping** in the Stats Box.
    *   Double-clicking a planet takes you into the **Planet View**.

![Galaxy View](https://i.imgur.com/your-galaxy-view-image.png)

### 🛰️ Planet View

The Planet View is the most granular level, offering powerful tools to inspect and optimize a single prompt. This view is activated when you double-click a planet, causing the camera to focus on it and a detailed sidebar to appear.

*   **Representation:**
    *   The focused **Planet** represents the currently deployed prompt variant for that task.
    *   Smaller nodes orbiting the planet are **Trace Nodes**, which represent other prompt variants from the optimization history. The best-performing variants orbit closest to the planet.
*   **Interaction:**
    *   The **Planet Sidebar** is your command center for this prompt.
    *   **Deployed Version:** View the full text and performance metrics of the currently active prompt.
    *   **Auto-Optimization:** Start or stop an A/B testing session for this planet. The system will continuously generate and evaluate new variants.
    *   **Selected Variant:** Click on any orbiting trace node to see its metrics and full text. From here, you can click the **Deploy this Variant** button to make it the new active prompt for the planet.

![Planet View](https://i.imgur.com/your-planet-view-image.png)

## 🛠️ Technology Stack

*   **Frontend:** React, React Three Fiber (for 3D), Drei (helpers for R3F), Zustand (state management).
*   **Backend:** Python, aiohttp (for the web server and WebSocket communication).

## 🚀 Getting Started

Follow these steps to get the GalactiCode cockpit running on your local machine.

### Prerequisites

*   Node.js and npm
*   Python 3.7+ and pip

### Installation & Setup

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/your-username/GalactiCode.git
    cd GalactiCode
    ```

2.  **Install Backend Dependencies:**
    ```bash
    pip install -r mcp_servers/cockpit_mcp/requirements.txt
    ```

3.  **Install Frontend Dependencies:**
    ```bash
    cd dashboard/cockpit
    npm install
    ```

### Running the Application

1.  **Start the Backend Server:**
    Open a terminal in the project root and run:
    ```bash
    python mcp_servers/cockpit_mcp/server.py
    ```
    The backend server will start on `http://localhost:8080`.

2.  **Start the Frontend Application:**
    Open a second terminal in the `dashboard/cockpit` directory and run:
    ```bash
    npm start
    ```
    The React application will start and should open automatically in your browser at `http://localhost:3000`. 
