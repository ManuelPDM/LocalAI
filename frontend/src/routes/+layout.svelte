<!-- File: frontend/src/routes/+layout.svelte (Updated with modern nav rail) -->
<script>
    import { page } from '$app/stores';

    function toggleDarkMode() {
        if (typeof document !== 'undefined') {
            document.body.classList.toggle('dark-mode');
            localStorage.setItem('theme', document.body.classList.contains('dark-mode') ? 'dark' : 'light');
        }
    }
</script>

<div class="app-container">
    <nav class="main-nav-rail">
        <a href="/" class="logo-link" title="Home">
            <!-- App Logo Icon -->
            <svg xmlns="http://www.w3.org/2000/svg" width="28" height="28" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 8V4H8"></path><rect x="4" y="4" width="16" height="16" rx="2"></rect><path d="M2 14h2"></path><path d="M20 14h2"></path><path d="M15 2v2"></path><path d="M9 2v2"></path></svg>
        </a>

        <ul class="nav-list">
            <li class="nav-item">
                <a href="/" class="nav-link" class:active={$page.url.pathname === '/'} title="Home AI">
                    <!-- Home AI Icon -->
                    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m3 9 9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"></path><polyline points="9 22 9 12 15 12 15 22"></polyline></svg>
                </a>
            </li>
            <li class="nav-item">
                <a href="/playground" class="nav-link" class:active={$page.url.pathname.startsWith('/playground')} title="Chat Playground">
                    <!-- Playground Icon -->
                    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 22c5.523 0 10-4.477 10-10S17.523 2 12 2 2 6.477 2 12s4.477 10 10 10z"></path><path d="m7 12 5 5 5-5"></path><path d="m7 7 5 5 5-5"></path></svg>
                </a>
            </li>
             <li class="nav-item">
                <a href="/image-gen" class="nav-link" class:active={$page.url.pathname.startsWith('/image-gen')} title="Image Generation">
                    <!-- Image Gen Icon -->
                    <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect><circle cx="8.5" cy="8.5" r="1.5"></circle><polyline points="21 15 16 10 5 21"></polyline></svg>
                </a>
            </li>
        </ul>

        <div class="nav-footer">
            <button class="nav-link" on:click={toggleDarkMode} title="Toggle Dark Mode">
                <!-- Dark Mode Icon -->
                <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"></path></svg>
            </button>
             <!-- Global Settings can go here in the future -->
        </div>
    </nav>

    <main class="content-area">
        <slot />
    </main>
</div>

<style>
    /* Import your existing color variables */
    :root {
        --bg-color: #ffffff; --text-color: #212529; --border-color: #dee2e6;
        --sidebar-bg: #f8f9fa; --sidebar-hover-bg: #e9ecef; --sidebar-active-bg: #dde4eb;
        --nav-rail-bg: #f1f3f5;
    }
    :global(body.dark-mode) {
        --bg-color: #212529; --text-color: #f8f9fa; --border-color: #495057;
        --sidebar-bg: #343a40; --sidebar-hover-bg: #495057; --sidebar-active-bg: #0d6efd; /* Use a highlight color for active */
        --nav-rail-bg: #212529;
    }
    :global(body) {
        margin: 0;
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
        background-color: var(--bg-color);
        color: var(--text-color);
    }

    .app-container {
        display: flex;
        height: 100vh;
        width: 100vw;
        overflow: hidden;
    }

    .main-nav-rail {
        width: 64px; /* Crisp, narrow width */
        background-color: var(--nav-rail-bg);
        border-right: 1px solid var(--border-color);
        display: flex;
        flex-direction: column;
        align-items: center;
        padding: 1rem 0;
        flex-shrink: 0;
        z-index: 10;
    }

    .logo-link {
        color: var(--text-color);
        margin-bottom: 1.5rem;
    }

    .nav-list {
        list-style: none;
        padding: 0;
        margin: 0;
        display: flex;
        flex-direction: column;
        gap: 0.5rem;
    }

    .nav-link {
        display: flex;
        align-items: center;
        justify-content: center;
        width: 44px;
        height: 44px;
        border-radius: 8px;
        color: var(--text-color);
        text-decoration: none;
        transition: background-color 0.2s, color 0.2s;
        border: none;
        background: transparent;
        cursor: pointer;
    }

    .nav-link:hover {
        background-color: var(--sidebar-hover-bg);
    }

    .nav-link.active {
        background-color: var(--sidebar-active-bg);
        color: #fff; /* White icon color for active state */
    }
    :global(body.dark-mode) .nav-link.active {
        color: #fff;
    }


    .nav-footer {
        margin-top: auto; /* Pushes the footer to the bottom */
    }

    .content-area {
        flex-grow: 1;
        overflow: hidden;
        display: flex;
        flex-direction: column;
    }
</style>