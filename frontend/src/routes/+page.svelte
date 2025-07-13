<!-- File: frontend/src/routes/+page.svelte (Final Version with Settings Button) -->
<script>
    import { onMount } from 'svelte';

    // --- State for the Interactive Calendar ---
    let daysInMonth = [];
    let selectedDay = null; // This will hold the data for the clicked day

    // Mock log entries for the demo
    const MOCK_LOGS = [
        "User Command: 'Turn on the living room lights.'",
        "Tool Used: `smart-home-service`",
        "Action: Set `light.living_room` to `ON`.",
        "Task Complete.",
        "User Command: 'What's the weather like?'",
        "Tool Used: `web-search`",
        "Action: Searched for 'weather in current location'.",
        "Verbal Response: 'It's currently 18 degrees and sunny.'",
        "User Command: 'Summarize the last email from John Doe.'",
        "Tool Used: `email-assistant`",
        "Tool Used: `rag-memory` to get context.",
        "Verbal Response: 'John Doe's last email was a project update...'",
        "Autonomous: Indexing new files from watched folder.",
    ];

    function openSettingsModal() {
        // In a real implementation, this would open a settings modal component.
        alert('AI Settings modal would open here. This is where you would configure the main system prompt, memory settings, etc.');
    }

    function generateCalendarData(year, month) {
        const date = new Date(year, month, 1);
        const firstDayOfMonth = date.getDay();
        const daysInMonthCount = new Date(year, month + 1, 0).getDate();

        let calendarDays = [];

        for (let i = 0; i < firstDayOfMonth; i++) {
            calendarDays.push({ date: null });
        }

        for (let i = 1; i <= daysInMonthCount; i++) {
            const activityLevel = Math.floor(Math.random() * 5);
            const logCount = activityLevel > 0 ? Math.floor(Math.random() * activityLevel * 3) + 1 : 0;
            let dayLogs = [];
            for (let j = 0; j < logCount; j++) {
                dayLogs.push(MOCK_LOGS[Math.floor(Math.random() * MOCK_LOGS.length)]);
            }

            calendarDays.push({
                date: i,
                activityLevel,
                logs: dayLogs.sort()
            });
        }
        return calendarDays;
    }

    function selectDay(day) {
        if (day && day.logs && day.logs.length > 0) {
            selectedDay = day;
        }
    }

    function closeLogView() {
        selectedDay = null;
    }

    onMount(() => {
        const today = new Date();
        daysInMonth = generateCalendarData(today.getFullYear(), today.getMonth());
    });
</script>

<!-- Log Viewer Modal -->
{#if selectedDay}
<div class="modal-overlay" on:click={closeLogView} role="button" tabindex="0" on:keydown={(e) => {if(e.key === 'Escape') closeLogView()}}>
    <div class="log-viewer-modal" on:click|stopPropagation>
        <header class="modal-header">
            <h3>Activity for: October {selectedDay.date}, 2023</h3>
            <button on:click={closeLogView} title="Close">×</button>
        </header>
        <ul class="log-list">
            {#each selectedDay.logs as log}
                <li>{log}</li>
            {:else}
                <li>No activity recorded for this day.</li>
            {/each}
        </ul>
    </div>
</div>
{/if}

<div class="dashboard-container">
    <header class="dashboard-header">
        <h1>AI Command Center</h1>
        <button class="settings-button" title="AI Settings" on:click={openSettingsModal}>
            <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="3"></circle><path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"></path></svg>
        </button>
    </header>

    <main class="dashboard-grid">
        <!-- Widget 1: Command & Live Activity -->
        <div class="widget command-widget">
            <h3>Command & Status</h3>
            <div class="command-actions">
                <button class="command-button voice"><span>Voice Command</span></button>
                <button class="command-button text"><span>Type Command</span></button>
            </div>
            <div class="live-activity-feed">
                <ul class="status-list">
                    <li class="status-item idle">Awaiting command...</li>
                </ul>
            </div>
        </div>

        <!-- Widget 2: Tool Usage Chart -->
        <div class="widget tool-usage-widget">
            <h3>Tool Usage (Last 7 Days)</h3>
            <div class="chart bar-chart">
                <ul>
                    <li style="--bar-value: 85%; --bar-color: #3b82f6;"><span>Smart Home</span></li>
                    <li style="--bar-value: 70%; --bar-color: #8b5cf6;"><span>Memory (RAG)</span></li>
                    <li style="--bar-value: 50%; --bar-color: #10b981;"><span>Communications</span></li>
                    <li style="--bar-value: 25%; --bar-color: #ec4899;"><span>Image Generation</span></li>
                </ul>
            </div>
        </div>

        <!-- Widget 3: Interactive Activity Calendar -->
        <div class="widget activity-widget">
            <div class="activity-header">
                <h3>Activity History</h3>
                <div class="calendar-nav">
                    <button>‹</button>
                    <span>October 2023</span>
                    <button>›</button>
                </div>
            </div>
            <div class="calendar-grid">
                <div class="day-name">Sun</div><div class="day-name">Mon</div><div class="day-name">Tue</div><div class="day-name">Wed</div><div class="day-name">Thu</div><div class="day-name">Fri</div><div class="day-name">Sat</div>

                {#each daysInMonth as day}
                    {#if day.date}
                        <button
                            class="day-cell"
                            style="--activity-level: {day.activityLevel};"
                            on:click={() => selectDay(day)}
                            disabled={day.activityLevel === 0}
                            title="{day.logs.length} activities"
                        >
                            {day.date}
                        </button>
                    {:else}
                        <div class="day-cell empty"></div>
                    {/if}
                {/each}
            </div>
        </div>

        <!-- Widget 4: Tool Palette -->
        <div class="widget tool-palette-widget">
            <h3>Key Tools</h3>
            <div class="tool-palette-grid">
                <div class="tool-item online"><span>💡</span>Smart Home</div>
                <div class="tool-item online"><span>🧠</span>Memory (RAG)</div>
                <div class="tool-item online"><span>📱</span>Comms</div>
                <div class="tool-item online"><span>🎨</span>Image Gen</div>
            </div>
            <button class="view-all-button">
                View All Tools →
            </button>
        </div>
    </main>
</div>

<style>
    /* Main container and layout */
    .dashboard-container {
        display: flex; flex-direction: column; height: 100%; width: 100%;
        background-color: #111827; color: #e5e7eb;
        padding: 1.5rem 2rem; gap: 1.5rem;
    }

    .dashboard-header { display: flex; justify-content: space-between; align-items: center; flex-shrink: 0; }
    .dashboard-header h1 { margin: 0; font-size: 1.75rem; font-weight: 600; }
    .settings-button { background: transparent; border: none; color: #9ca3af; cursor: pointer; padding: 0.5rem; border-radius: 50%; transition: all 0.2s ease; }
    .settings-button:hover { background: rgba(255, 255, 255, 0.1); color: #fff; }

    /* Grid Layout for Widgets */
    .dashboard-grid { flex-grow: 1; display: grid; grid-template-columns: repeat(2, 1fr); grid-template-rows: repeat(2, 1fr); gap: 1.5rem; }

    /* Glassmorphism Widget Styling */
    .widget {
        background: rgba(31, 41, 55, 0.5); backdrop-filter: blur(12px);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 16px; padding: 1.5rem;
        display: flex; flex-direction: column;
    }
    .widget h3 { margin: 0 0 1.5rem 0; font-size: 1rem; font-weight: 500; color: #d1d5db; }

    /* Command Widget */
    .command-widget { grid-area: 1 / 1 / 2 / 2; }
    .command-actions { display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; margin-bottom: 1.5rem; }
    .command-button {
        display: flex; align-items: center; justify-content: center; gap: 0.75rem;
        font-size: 1rem; font-weight: 500; padding: 1rem; border-radius: 10px;
        border: 1px solid rgba(255, 255, 255, 0.2); cursor: pointer;
        transition: all 0.2s ease; background: rgba(255, 255, 255, 0.05); color: #e5e7eb;
    }
    .command-button:hover { background: rgba(255, 255, 255, 0.1); border-color: rgba(255, 255, 255, 0.3); }
    .live-activity-feed { flex-grow: 1; background: rgba(0,0,0,0.2); border-radius: 8px; padding: 1rem; }
    .status-list { list-style: none; padding: 0; margin: 0; font-family: 'Menlo', monospace; font-size: 0.85rem; }
    .status-item.idle::before { content: '●'; color: #4ade80; margin-right: 0.5rem; animation: pulse 2s infinite; }

    /* Tool Usage Widget */
    .tool-usage-widget { grid-area: 1 / 2 / 2 / 3; }
    .bar-chart { flex-grow: 1; display: flex; flex-direction: column; justify-content: space-around; }
    .bar-chart ul { list-style: none; padding: 0; margin: 0; display: flex; flex-direction: column; gap: 1rem; }
    .bar-chart li { display: grid; grid-template-columns: 1fr 2fr; align-items: center; gap: 1rem; }
    .bar-chart li::after { content: ''; height: 1.5rem; width: var(--bar-value); background: var(--bar-color); border-radius: 4px; box-shadow: 0 0 12px 0 var(--bar-color); }
    .bar-chart span { font-size: 0.9rem; font-weight: 500; }

    /* INTERACTIVE Activity Calendar Widget */
    .activity-widget { grid-area: 2 / 1 / 3 / 2; gap: 1rem; }
    .activity-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 0 !important; }
    .activity-header h3 { margin-bottom: 0 !important; }
    .calendar-nav { display: flex; align-items: center; gap: 0.5rem; }
    .calendar-nav span { font-size: 0.9rem; font-weight: 500; }
    .calendar-nav button { background: none; border: none; color: #9ca3af; cursor: pointer; font-size: 1.5rem; }
    .calendar-grid { flex-grow: 1; display: grid; grid-template-columns: repeat(7, 1fr); grid-template-rows: auto repeat(6, 1fr); gap: 5px; }
    .day-name { font-size: 0.75rem; text-align: center; color: #9ca3af; }
    .day-cell {
        background: rgba(255, 255, 255, 0.05); border-radius: 4px;
        border: 1px solid transparent;
        color: #d1d5db; font-size: 0.8rem;
        display: flex; align-items: center; justify-content: center;
        transition: all 0.2s ease;
    }
    .day-cell:not([disabled]):not(.empty) { cursor: pointer; }
    .day-cell:not([disabled]):hover { border-color: rgba(59, 130, 246, 0.8); background: rgba(59, 130, 246, 0.2); }
    .day-cell[disabled] { opacity: 0.5; cursor: not-allowed; }
    .day-cell.empty { background: transparent; }
    .day-cell[style*="--activity-level: 1"] { background-color: rgba(59, 130, 246, 0.2); }
    .day-cell[style*="--activity-level: 2"] { background-color: rgba(59, 130, 246, 0.4); }
    .day-cell[style*="--activity-level: 3"] { background-color: rgba(59, 130, 246, 0.7); }
    .day-cell[style*="--activity-level: 4"] { background-color: rgba(59, 130, 246, 1.0); }

    /* Tool Palette Widget */
    .tool-palette-widget { grid-area: 2 / 2 / 3 / 3; }
    .tool-palette-grid { display: grid; grid-template-columns: 1fr 1fr; grid-template-rows: 1fr 1fr; gap: 1rem; flex-grow: 1; }
    .tool-item {
        background: rgba(255, 255, 255, 0.05); border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 10px; display: flex; flex-direction: column; align-items: center; justify-content: center;
        gap: 0.5rem; font-weight: 500; position: relative;
    }
    .tool-item.online::after {
        content: ''; position: absolute; top: 12px; right: 12px; width: 8px; height: 8px;
        border-radius: 50%; background-color: #4ade80; box-shadow: 0 0 8px 0 #4ade80;
    }
    .tool-item span:first-child { font-size: 1.75rem; }
    .view-all-button {
        margin-top: 1.5rem; padding: 0.75rem; width: 100%;
        background: rgba(255, 255, 255, 0.1); border: 1px solid rgba(255, 255, 255, 0.2);
        color: #e5e7eb; font-weight: 500; border-radius: 8px; cursor: pointer; transition: background 0.2s ease;
    }
    .view-all-button:hover { background: rgba(255, 255, 255, 0.15); }

    /* Log Viewer Modal Styling */
    .modal-overlay {
        position: fixed; top: 0; left: 0; width: 100%; height: 100%;
        background: rgba(0,0,0,0.6); backdrop-filter: blur(5px);
        z-index: 1000; display: grid; place-items: center;
    }
    .log-viewer-modal {
        width: 90%; max-width: 600px;
        background: #1f2937; border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 16px; padding: 1.5rem;
        max-height: 80vh; display: flex; flex-direction: column;
    }
    .modal-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 1rem; }
    .modal-header h3 { margin: 0; }
    .modal-header button { background: none; border: none; font-size: 2rem; color: #9ca3af; cursor: pointer; line-height: 1; }
    .log-list {
        list-style: none; padding: 1rem; margin: 0;
        background: rgba(0,0,0,0.2); border-radius: 8px;
        font-family: 'Menlo', monospace; font-size: 0.85rem;
        overflow-y: auto; display: flex; flex-direction: column; gap: 0.5rem;
    }

    @keyframes pulse {
        0% { box-shadow: 0 0 0 0 #4ade8077; }
        70% { box-shadow: 0 0 0 8px #4ade8000; }
        100% { box-shadow: 0 0 0 0 #4ade8000; }
    }
</style>