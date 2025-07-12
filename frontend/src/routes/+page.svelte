<script>
    import { onMount } from 'svelte';
    import { marked } from 'marked';
    import hljs from 'highlight.js';
    import 'highlight.js/styles/atom-one-dark.css';

    // --- DOM Element Bindings ---
    let chatBox;
    let inputMessage;
    let settingsModal;
    let settingsOverlay;
    let promptListEditor;

    // --- Svelte Reactive State ---
    const AUTO_PLAY_KEY = 'autoPlayResponses';
    let currentSessionId = null;
    let currentAbortController = null;
    let currentSettings = {};
    let currentSessionInfo = { icon: 'bot.svg', ai_name: null };
    let isFullVoiceModeActive = false;
    let availableIcons = [];
    let audioUnlocked = false;
    let isNewChatMode = false;
    let sessionList = [];
    let isGenerating = false;
    let showMobileMenu = false;
    let autoPlayEnabled = false;

    // --- Speech Recognition ---
    const SpeechRecognition = typeof window !== 'undefined' ? window.SpeechRecognition || window.webkitSpeechRecognition : null;
    let recognition = null;
    let isSttSupported = !!SpeechRecognition;

    // --- TTS Streaming State ---
    let audioQueue = [];
    let isAudioPlaying = false;
    let currentAudio = null;
    const SENTENCE_BREAK_REGEX = /(?<=[.?!])\s|(?<=\n)|(?=\n\s*\*)/;

    onMount(async () => {
        if (SpeechRecognition) {
            recognition = new SpeechRecognition();
            recognition.continuous = false;
            recognition.interimResults = false;
            recognition.onresult = handleVoiceResult;
            recognition.onend = () => {
                if (isFullVoiceModeActive && !currentAbortController) {
                    startVoiceLoop();
                }
            };
        }

        if (localStorage.getItem('theme') === 'dark') {
            document.body.classList.add('dark-mode');
        }

        autoPlayEnabled = localStorage.getItem(AUTO_PLAY_KEY) === 'true';

        try {
            const response = await fetch('/api/settings');
            currentSettings = await response.json();
            applyIconSize(currentSettings.icon_size);
            await loadSessions();
        } catch (error) {
            console.error("Failed to load initial settings:", error);
        }

        // Add body-level click listener to unlock audio context
        document.body.addEventListener('click', unlockAudioContext, { once: true });
        document.body.addEventListener('touchend', unlockAudioContext, { once: true });
    });

    function unlockAudioContext() {
        if (audioUnlocked) return;
        const silentWav = "data:audio/wav;base64,UklGRigAAABXQVZFZm10IBIAAAABAAEARKwAAIhYAQACABAAAABkYXRhAgAAAAEA";
        const sound = new Audio(silentWav);
        sound.play().then(() => {
            audioUnlocked = true;
            console.log("Audio context unlocked by user gesture.");
        }).catch(e => {
            console.warn("Audio context unlock failed. Will try again on next interaction.", e);
        });
    }

    const stopAllAudio = () => {
        if (currentAudio) {
            currentAudio.onended = null;
            currentAudio.pause();
            currentAudio.src = '';
            currentAudio = null;
        }
        audioQueue = [];
        isAudioPlaying = false;
        const playingBtns = document.querySelectorAll('.tts-msg-btn.playing');
        playingBtns.forEach(btn => {
            btn.classList.remove('playing');
            btn.innerHTML = '🔊';
            btn.disabled = false;
        });
    };

    const playTextAsSpeech = async (text, buttonElement) => {
        unlockAudioContext();
        if (buttonElement.classList.contains('playing')) {
            stopAllAudio();
            return;
        }
        stopAllAudio();

        if (!text || !text.trim()) return;
        const textToSynthesize = text;
        const originalButtonContent = '🔊';

        buttonElement.innerHTML = '...';
        buttonElement.disabled = true;

        const controller = new AbortController();
        const timeoutId = setTimeout(() => {
            controller.abort();
            console.error("TTS request timed out.");
        }, 10000);

        try {
            buttonElement.classList.add('playing');
            const ttsUrl = `/api/tts`;
            const response = await fetch(ttsUrl, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    text: textToSynthesize.trim(),
                    length_scale: currentSettings.length_scale || 1.0
                }),
                signal: controller.signal
            });
            clearTimeout(timeoutId);

            if (!response.ok) throw new Error(`TTS server error: ${response.statusText}`);

            const blob = await response.blob();
            currentAudio = new Audio(URL.createObjectURL(blob));
            isAudioPlaying = true;
            currentAudio.play();
            currentAudio.onended = () => {
                isAudioPlaying = false;
                currentAudio = null;
                if (document.body.contains(buttonElement)) {
                    buttonElement.classList.remove('playing');
                    buttonElement.innerHTML = originalButtonContent;
                    buttonElement.disabled = false;
                }
            };
        } catch (error) {
            clearTimeout(timeoutId);
            console.error("Single TTS Error:", error);
            isAudioPlaying = false;
            if (document.body.contains(buttonElement)) {
                buttonElement.innerHTML = '⚠️';
                setTimeout(() => {
                    if (document.body.contains(buttonElement)) {
                        buttonElement.innerHTML = originalButtonContent;
                    }
                }, 2000);
            }
        } finally {
            if (document.body.contains(buttonElement) && !isAudioPlaying) {
                buttonElement.classList.remove('playing');
                buttonElement.disabled = false;
            }
        }
    };

    const processAudioQueue = async () => {
        if (isAudioPlaying || audioQueue.length === 0) return;

        isAudioPlaying = true;
        const voiceStatusText = document.getElementById('voice-status-text');
        if (isFullVoiceModeActive && voiceStatusText) voiceStatusText.textContent = 'Speaking...';
        const sentence = audioQueue.shift();

        if (!sentence || !sentence.trim()) {
            isAudioPlaying = false;
            processAudioQueue();
            return;
        }

        const textToSynthesize = sentence;

        try {
            const ttsUrl = `/api/tts`;
            const response = await fetch(ttsUrl, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    text: textToSynthesize.trim(),
                    length_scale: currentSettings.length_scale || 1.0
                })
            });
            if (!response.ok) throw new Error(`TTS server error: ${response.statusText}`);

            const blob = await response.blob();
            currentAudio = new Audio(URL.createObjectURL(blob));
            currentAudio.play();
            currentAudio.onended = () => {
                isAudioPlaying = false;
                if (audioQueue.length > 0) {
                    processAudioQueue();
                } else if (isFullVoiceModeActive) {
                    startVoiceLoop();
                }
            };
        } catch (error) {
            console.error("TTS Error:", error);
            isAudioPlaying = false;
            if (isFullVoiceModeActive) {
                startVoiceLoop();
            }
        }
    };

    let messages = [];

    function addMessage(role, text, isStreaming = false) {
        const lastMessage = messages[messages.length - 1];
        if (isStreaming && lastMessage && lastMessage.role === role) {
            lastMessage.text += text;
            messages = messages;
        } else {
            const newMessage = {
                id: Date.now() + Math.random(),
                role,
                text,
                sender: role === 'assistant' ? (currentSessionInfo.ai_name || 'Assistant') : 'User',
                avatar: role === 'assistant' ? `/icons/${currentSessionInfo.icon || 'bot.svg'}` : '/icons/user.svg'
            };
            messages = [...messages, newMessage];
        }
        setTimeout(() => { if (chatBox) chatBox.scrollTop = chatBox.scrollHeight; }, 0);
    }

    function finalizeMessage(messageId) {
        const messageDiv = document.querySelector(`.message[data-id="${messageId}"] .message-content`);
        if (!messageDiv) return;

        const message = messages.find(m => m.id == messageId);
        if (!message) return;

        messageDiv.innerHTML = marked.parse(message.text || '');
        messageDiv.querySelectorAll('pre code').forEach(hljs.highlightElement);

        messageDiv.querySelectorAll('pre').forEach(pre => {
            if (pre.querySelector('.copy-btn')) return;
            const copyBtn = document.createElement('button');
            copyBtn.className = 'copy-btn';
            copyBtn.innerText = 'Copy';
            copyBtn.onclick = () => {
                navigator.clipboard.writeText(pre.querySelector('code').innerText).then(() => {
                    copyBtn.innerText = 'Copied!';
                    setTimeout(() => copyBtn.innerText = 'Copy', 2000);
                });
            };
            pre.appendChild(copyBtn);
        });
    }

    const updateActionButtons = (messageId) => {
        setTimeout(() => {
            const messageEl = document.querySelector(`.message[data-id="${messageId}"]`);
            if (messageEl) {
                const buttons = messageEl.querySelectorAll('.message-actions button');
                buttons.forEach(btn => btn.classList.remove('hidden'));
            }
        }, 10);
    };

    const handleStream = async (response, onFinally) => {
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        const useVoice = autoPlayEnabled || isFullVoiceModeActive;

        const newMessage = {
            id: Date.now() + Math.random(),
            role: 'assistant',
            text: '',
            sender: currentSessionInfo.ai_name || 'Assistant',
            avatar: `/icons/${currentSessionInfo.icon || 'bot.svg'}`
        };
        messages = [...messages, newMessage];

        let sentenceBuffer = "";

        while (true) {
            if (currentAbortController && currentAbortController.signal.aborted) break;
            const { done, value } = await reader.read();
            if (done) break;

            const chunk = decoder.decode(value, { stream: true });
            newMessage.text += chunk;
            messages = messages;

            if (useVoice) {
                sentenceBuffer += chunk;
                const sentences = sentenceBuffer.split(SENTENCE_BREAK_REGEX);
                if (sentences.length > 1) {
                    sentenceBuffer = sentences.pop();
                    for (const sentence of sentences) {
                        if (sentence.trim()) {
                            audioQueue.push(sentence);
                            if (!isAudioPlaying) processAudioQueue();
                        }
                    }
                }
            }
        }
        if (currentAbortController && !currentAbortController.signal.aborted && useVoice && sentenceBuffer.trim()) {
            audioQueue.push(sentenceBuffer);
            if (!isAudioPlaying) processAudioQueue();
        }
        finalizeMessage(newMessage.id);
        onFinally(newMessage.id);
    };

    const loadSessions = async () => {
        try {
            const response = await fetch('/api/sessions');
            sessionList = await response.json();

            if (sessionList.length > 0 && !currentSessionId) {
                await loadSession(sessionList[0].id);
            } else if (sessionList.length === 0) {
                await enterNewChatMode();
            }
        } catch (error) {
            console.error("Failed to load sessions:", error);
        }
    };

    const loadSession = async (sessionId) => {
        if (currentAbortController) currentAbortController.abort();
        stopAllAudio();
        isNewChatMode = false;

        try {
            const response = await fetch(`/api/sessions/${sessionId}`);
            if (!response.ok) { currentSessionId = null; await loadSessions(); return; }
            const sessionData = await response.json();

            currentSessionInfo = { icon: sessionData.icon, ai_name: sessionData.ai_name };
            messages = sessionData.messages
                .filter(msg => msg.role !== 'system')
                .map(msg => ({
                    id: Math.random(),
                    ...msg,
                    text: msg.content,
                    sender: msg.role === 'assistant' ? (sessionData.ai_name || 'Assistant') : 'User',
                    avatar: msg.role === 'assistant' ? `/icons/${sessionData.icon || 'bot.svg'}` : '/icons/user.svg'
                }));

            currentSessionId = sessionId;
            setTimeout(() => {
                messages.forEach(msg => finalizeMessage(msg.id));
                updateActionButtons(messages[messages.length - 1]?.id);
            }, 50);

        } catch (error) {
            console.error(`Failed to load session ${sessionId}:`, error);
        }
    };

    const enterNewChatMode = async () => {
        if (currentAbortController) currentAbortController.abort();
        stopAllAudio();
        messages = [];
        currentSessionId = null;
        isNewChatMode = true;

        const defaultPrompt = currentSettings.prompts ? currentSettings.prompts[0] : {};
        currentSessionInfo = {
            icon: defaultPrompt?.icon || 'bot.svg',
            ai_name: defaultPrompt?.ai_name || null
        };
        if (inputMessage) inputMessage.focus();
    };

    async function sendMessageToServer(messageText, isNew) {
        currentAbortController = new AbortController();
        isGenerating = true;
        try {
            const voiceStatusText = document.getElementById('voice-status-text');
            if (isFullVoiceModeActive && voiceStatusText) voiceStatusText.textContent = 'Thinking...';

            const response = await fetch(`/api/chat/${currentSessionId}`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ message: messageText }),
                signal: currentAbortController.signal
            });

            if (!response.ok) throw new Error("Failed to get response from server.");

            await handleStream(response, (newMessageId) => {
                updateActionButtons(newMessageId);
                if (isNew) loadSessions();
            });
        } catch (error) {
            if (error.name !== 'AbortError') {
                console.error('Fetch error:', error);
                addMessage('assistant', `Error: ${error.message}`);
            } else {
                console.log("Stream aborted by user.");
            }
        } finally {
            currentAbortController = null;
            isGenerating = false;
        }
    }

    const sendMessage = async () => {
        unlockAudioContext();
        const messageText = inputMessage.value.trim();
        if (!messageText || isGenerating) return;

        stopAllAudio();

        let isNew = !currentSessionId;
        if (isNew) {
            isNewChatMode = false;
            try {
                const promptDropdown = document.getElementById('prompt-select-dropdown');
                const selectedPrompt = promptDropdown ? promptDropdown.value : (currentSettings.prompts[0]?.prompt || '');
                const response = await fetch('/api/sessions', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ prompt: selectedPrompt })
                });
                const newSessionData = await response.json();
                currentSessionId = newSessionData.id;

                const promptInfo = (currentSettings.prompts || []).find(p => p.prompt === selectedPrompt);
                if (promptInfo) {
                    currentSessionInfo = { icon: promptInfo.icon, ai_name: promptInfo.ai_name };
                }
            } catch (error) {
                console.error("Failed to create new session:", error);
                addMessage('assistant', 'Error: Could not create a new session.');
                return;
            }
        }

        addMessage('user', messageText);
        inputMessage.value = '';
        inputMessage.style.height = 'auto';

        await sendMessageToServer(messageText, isNew);
    };

    const regenerateMessage = async (messageDiv) => {
        if (!currentSessionId || isGenerating) return;
        stopAllAudio();

        const messageId = messageDiv.dataset.id;
        messages = messages.filter(m => m.id != messageId);

        isGenerating = true;
        currentAbortController = new AbortController();

        try {
            const response = await fetch(`/api/chat/${currentSessionId}/regenerate`, {
                method: 'POST',
                signal: currentAbortController.signal
            });
            if (!response.ok) {
                const errorText = await response.text();
                throw new Error(`Failed to regenerate: ${errorText}`);
            }
            await handleStream(response, (newMessageId) => updateActionButtons(newMessageId));
        } catch (error) {
            if (error.name !== 'AbortError') {
                addMessage('assistant', `<p style="color:red;">Error: ${error.message}</p>`);
            }
        } finally {
            currentAbortController = null;
            isGenerating = false;
        }
    };

    function applyIconSize(size) {
        document.body.classList.remove('icon-size-small', 'icon-size-medium', 'icon-size-large', 'icon-size-xl');
        document.body.classList.add(`icon-size-${size || 'medium'}`);
    }

    const openSettingsModal = async () => {
        try {
            const settingsResp = await fetch('/api/settings');
            currentSettings = await settingsResp.json();
            availableIcons = ['bot.svg', 'python.svg', 'story.svg', 'user.svg'];
            settingsOverlay.classList.remove('hidden');
            settingsModal.classList.remove('hidden');
            // Dynamically create the prompt entries after modal is open
            setTimeout(rebuildPromptEditor, 0);
        } catch (error) {
            console.error("Failed to open settings:", error);
        }
    };

    const rebuildPromptEditor = () => {
        if (!promptListEditor) return;
        promptListEditor.innerHTML = ''; // Clear existing
        (currentSettings.prompts || []).forEach(p => createPromptEditorEntry(p));
    }

    const createPromptEditorEntry = (p = {}) => {
        if (!promptListEditor) return;

        const div = document.createElement('div');
        div.className = 'prompt-editor-entry';
        const iconOptions = availableIcons.map(icon => `<option value="${icon}" ${p.icon === icon ? 'selected' : ''}>${icon}</option>`).join('');
        div.innerHTML = `
            <div class="prompt-title-wrapper">
                <label>Persona Title</label>
                <input type="text" value="${p.title || ''}" class="prompt-title" placeholder="e.g., Python Expert">
            </div>
            <div class="prompt-name-wrapper">
                <label>AI Name (Optional)</label>
                <input type="text" value="${p.ai_name || ''}" class="prompt-ai-name" placeholder="e.g., CoderBot">
            </div>
            <button type="button" class="remove-prompt-btn" title="Remove Persona">X</button>
            <div class="prompt-icon-wrapper">
                 <label>Icon</label>
                 <select class="prompt-icon">${iconOptions}</select>
            </div>
            <textarea class="prompt-text" placeholder="System prompt content...">${p.prompt || ''}</textarea>
        `;
        promptListEditor.appendChild(div);
        div.querySelector('.remove-prompt-btn').addEventListener('click', () => div.remove());
    }

    const closeSettingsModal = () => {
        settingsOverlay.classList.add('hidden');
        settingsModal.classList.add('hidden');
    };

    const saveSettings = async (event) => {
        const newSettings = {
            lm_studio_url: document.getElementById('setting-url').value,
            icon_size: document.getElementById('setting-icon-size').value,
            length_scale: parseFloat(document.getElementById('setting-speed').value),
            context_limit: parseInt(document.getElementById('setting-context').value),
            prompts: []
        };

        promptListEditor.querySelectorAll('.prompt-editor-entry').forEach(div => {
            const title = div.querySelector('.prompt-title').value.trim();
            const prompt = div.querySelector('.prompt-text').value.trim();
            if (title && prompt) {
                newSettings.prompts.push({
                    title,
                    prompt,
                    icon: div.querySelector('.prompt-icon').value,
                    ai_name: div.querySelector('.prompt-ai-name').value.trim() || null
                });
            }
        });

        await fetch('/api/settings', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(newSettings)
        });
        currentSettings = newSettings;
        applyIconSize(currentSettings.icon_size);
        closeSettingsModal();
    };

    function startVoiceLoop() {
        if (!isFullVoiceModeActive) return;
        const voiceStatusText = document.getElementById('voice-status-text');
        if (voiceStatusText) voiceStatusText.textContent = 'Listening...';
        try { recognition.start(); } catch (e) { console.log("STT could not be started."); }
    }

    function stopVoiceLoop() {
        if (!isFullVoiceModeActive) return;
        isFullVoiceModeActive = false;
        stopAllAudio();
        try { recognition.stop(); } catch (e) { /* ignore */ }
        if (currentAbortController) {
            currentAbortController.abort();
            currentAbortController = null;
        }
    }

    function handleVoiceResult(event) {
        const transcript = event.results[event.results.length - 1][0].transcript.trim();
        if (transcript) {
            sendMessage(transcript);
        }
    }

    function handleSessionClick(sessionId) {
        if (sessionId !== currentSessionId) {
            loadSession(sessionId);
        }
        if (window.innerWidth <= 768) {
            showMobileMenu = false;
        }
    }

    function handleRenameSession(e, sessionId) {
        e.stopPropagation();
        const currentTitle = sessionList.find(s => s.id === sessionId)?.title || '';
        const newTitle = prompt('Enter new title:', currentTitle);
        if (newTitle && newTitle.trim()) {
            fetch(`/api/sessions/${sessionId}/rename`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ title: newTitle })
            }).then(() => {
                sessionList = sessionList.map(s => s.id === sessionId ? { ...s, title: newTitle } : s);
            });
        }
    }

    function handleDeleteSession(e, sessionId) {
        e.stopPropagation();
        if (confirm('Are you sure you want to delete this session?')) {
            fetch(`/api/sessions/${sessionId}`, { method: 'DELETE' })
                .then(() => {
                    sessionList = sessionList.filter(s => s.id !== sessionId);
                    if (currentSessionId === sessionId) {
                        currentSessionId = null;
                        enterNewChatMode();
                    }
                });
        }
    }

    function handleNewChatClick() {
        enterNewChatMode();
        if (window.innerWidth <= 768) {
            showMobileMenu = false;
        }
    }

    function toggleDarkMode() {
        document.body.classList.toggle('dark-mode');
        localStorage.setItem('theme', document.body.classList.contains('dark-mode') ? 'dark' : 'light');
    }

</script>

<button id="menu-toggle-btn" on:click={() => showMobileMenu = !showMobileMenu}>☰</button>

<div id="mobile-overlay" class:active={showMobileMenu} on:click={() => showMobileMenu = false} role="button" tabindex="0" on:keydown={(e) => {if(e.key==='Enter') showMobileMenu = false}}></div>

<div class="sidebar" class:open={showMobileMenu}>
    <div class="sidebar-header"><button id="new-chat-btn" on:click={handleNewChatClick}>➕ New Chat</button></div>
    <ul id="session-list">
        {#each sessionList as session (session.id)}
            <li>
                <button class="session-button" on:click={() => handleSessionClick(session.id)} class:active={session.id === currentSessionId}>
                    <img src={`/icons/${session.icon || 'bot.svg'}`} alt="session icon" class="session-icon">
                    <span class="session-title">{session.title}</span>
                </button>
                <div class="session-buttons">
                    <button class="rename-session-btn" title="Rename" on:click={(e) => handleRenameSession(e, session.id)}>✏️</button>
                    <button class="delete-session-btn" title="Delete" on:click={(e) => handleDeleteSession(e, session.id)}>🗑️</button>
                </div>
            </li>
        {/each}
    </ul>
    <div class="sidebar-footer">
        <div class="footer-action">
            <button id="full-voice-mode-btn" style="width:100%;" on:click={() => isFullVoiceModeActive = !isFullVoiceModeActive} disabled={!isSttSupported}>
                {#if isFullVoiceModeActive}⏹️ Stop Voice Chat{:else if !isSttSupported}⛔ Voice Not Supported{:else}🎙️ Start Voice Chat{/if}
            </button>
        </div>
        <div class="footer-action">
            <label for="voice-chat-toggle">🔊 Auto-Play Responses</label>
            <input type="checkbox" id="voice-chat-toggle" title="Toggle automatic voice playback for new messages" bind:checked={autoPlayEnabled} on:change={() => localStorage.setItem(AUTO_PLAY_KEY, autoPlayEnabled)}>
        </div>
        <div class="footer-action">
            <label for="settings-btn">⚙️ Settings</label>
            <button id="settings-btn" on:click={openSettingsModal}>Open</button>
        </div>
        <div class="footer-action">
            <label for="dark-mode-btn">🌙 Dark Mode</label>
            <button id="dark-mode-btn" on:click={toggleDarkMode}>Toggle</button>
        </div>
    </div>
</div>

<div class="chat-container">
    <div id="new-chat-prompt-selector" class:hidden={!isNewChatMode}>
        <label for="prompt-select-dropdown">Choose a Persona:</label>
        <select id="prompt-select-dropdown">
            {#if currentSettings.prompts}
                {#each currentSettings.prompts as p}
                    <option value={p.prompt}>{p.title}</option>
                {/each}
            {/if}
        </select>
    </div>

    <div id="chat-box" bind:this={chatBox}>
        {#each messages as msg (msg.id)}
            <div class="message {msg.role}" data-id={msg.id}>
                {#if msg.role === 'user' || msg.role === 'assistant'}
                    <img src={msg.avatar} alt="{msg.role} avatar" class="avatar" />
                    <div class="message-container">
                        {#if msg.role === 'assistant' && currentSessionInfo.ai_name}
                            <div class="message-sender">{currentSessionInfo.ai_name}</div>
                        {/if}
                        <div class="message-content">{@html msg.text ? marked.parse(msg.text) : ''}</div>
                        {#if msg.role === 'assistant'}
                            <div class="message-actions">
                                <button class="tts-msg-btn hidden" title="Read Aloud" on:click={(e) => playTextAsSpeech(msg.text, e.currentTarget)}>🔊</button>
                                <button class="regenerate-btn hidden" title="Regenerate" on:click={(e) => regenerateMessage(e.currentTarget.closest('.message'))}>🔄</button>
                            </div>
                        {/if}
                    </div>
                {/if}
            </div>
        {/each}
    </div>

    <div class="input-area">
        <button id="mic-btn" title="Start Speech to Text" on:click={() => recognition?.start()} disabled={!isSttSupported}>🎤</button>
        <textarea id="input-message" placeholder="Type your message here..." rows="1" bind:this={inputMessage} on:keypress={(e) => {if(e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendMessage(); }}}></textarea>
        {#if isGenerating}
            <button id="cancel-btn" title="Cancel Generation" on:click={() => currentAbortController?.abort()}>⏹️</button>
        {:else}
            <button id="send-btn" title="Send Message" on:click={sendMessage}>➤</button>
        {/if}
    </div>
</div>

<div id="full-voice-overlay" class:hidden={!isFullVoiceModeActive} on:click={stopVoiceLoop} role="button" tabindex="0" on:keydown={(e) => {if(e.key==='Enter') stopVoiceLoop()}}>
    <div id="pulsing-circle"></div>
    <p id="voice-status-text">Starting...</p>
</div>

<div id="settings-overlay" class:hidden={true} on:click={(e) => {if(e.target === settingsOverlay) closeSettingsModal()}} bind:this={settingsOverlay} role="button" tabindex="0" on:keydown={(e) => {if(e.key==='Enter') closeSettingsModal()}}></div>

<div id="settings-modal" class:hidden={true} bind:this={settingsModal}>
    <form id="settings-form" on:submit|preventDefault={saveSettings}>
        <h2>Settings</h2>
        <fieldset>
            <legend>API Configuration</legend>
            <label for="setting-url">LM Studio URL</label>
            <input type="text" id="setting-url" name="lm_studio_url" required placeholder="e.g., http://localhost:1234/v1/chat/completions" value={currentSettings.lm_studio_url || ''}>
        </fieldset>
        <fieldset>
            <legend>Appearance</legend>
            <label for="setting-icon-size">Icon Size</label>
            <select id="setting-icon-size" name="icon_size" bind:value={currentSettings.icon_size}>
                <option value="small">Small</option>
                <option value="medium">Medium</option>
                <option value="large">Large</option>
                <option value="xl">XL</option>
            </select>
        </fieldset>
        <fieldset>
            <legend>TTS Configuration</legend>
            <label for="setting-speed">Speech Speed (0.5=fast, 1=normal, 1.5=slow)</label>
            <input type="number" id="setting-speed" name="length_scale" step="0.1" min="0.5" max="2.0" required bind:value={currentSettings.length_scale}>
        </fieldset>
        <fieldset>
            <legend>Context Management</legend>
            <label for="setting-context">Context Limit (Tokens)</label>
            <input type="number" id="setting-context" name="context_limit" step="1" required bind:value={currentSettings.context_limit}>
        </fieldset>
        <fieldset>
            <legend>System Prompts / Personas</legend>
            <div id="prompt-list-editor" bind:this={promptListEditor}></div>
            <button type="button" id="add-prompt-btn" on:click={() => createPromptEditorEntry()}>Add New Persona</button>
        </fieldset>
        <div class="modal-buttons">
            <button type="button" id="settings-cancel-btn" on:click={closeSettingsModal}>Cancel</button>
            <button type="submit" id="settings-save-btn">Save All Settings</button>
        </div>
    </form>
</div>


<style>
    /* Paste your ENTIRE <style> block from index.html here */
    :root {
        --bg-color: #ffffff; --text-color: #212529; --border-color: #dee2e6;
        --sidebar-bg: #f8f9fa; --sidebar-hover-bg: #e9ecef; --sidebar-active-bg: #dde4eb;
        --input-bg: #ffffff; --input-border: #ced4da;
        --user-msg-bg: #e6f3ff; --ai-msg-bg: #f1f3f5; --system-msg-bg: #fffbe6;
        --button-bg: #007bff; --button-text: #ffffff; --button-hover-bg: #0056b3;
        --danger-button-bg: #dc3545; --danger-button-hover-bg: #c82333;
    }
    :global(body.dark-mode) {
        --bg-color: #212529; --text-color: #f8f9fa; --border-color: #495057;
        --sidebar-bg: #343a40; --sidebar-hover-bg: #495057; --sidebar-active-bg: #5a6268;
        --input-bg: #495057; --input-border: #6c757d;
        --user-msg-bg: #004a99; --ai-msg-bg: #343a40; --system-msg-bg: #533519;
        --button-bg: #0d6efd; --button-text: #ffffff; --button-hover-bg: #0b5ed7;
    }
    :global(html) {
        height: 100%;
    }
    :global(body) {
        font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
        margin: 0;
        background-color: var(--bg-color);
        color: var(--text-color);
        display: flex;
        height: 100%;
        overflow: hidden;
    }
    .sidebar { width: 260px; background-color: var(--sidebar-bg); border-right: 1px solid var(--border-color); display: flex; flex-direction: column; transition: background-color 0.3s, border-color 0.3s; }
    .sidebar-header { padding: 1rem; border-bottom: 1px solid var(--border-color); }
    #new-chat-btn { width: 100%; padding: 0.75rem; font-size: 1rem; background-color: var(--button-bg); color: var(--button-text); border: none; border-radius: 5px; cursor: pointer; transition: background-color 0.2s; }
    #session-list { list-style: none; padding: 0.5rem; margin: 0; overflow-y: auto; flex-grow: 1; }
    #session-list li { padding: 0; margin-bottom: 0.25rem; display: flex; justify-content: space-between; align-items: center; border-radius: 5px; }
    button.session-button { background: transparent; border: none; width: 100%; padding: 0.75rem 1rem; border-radius: 5px; cursor: pointer; display: flex; align-items: center; gap: 0.5rem; text-align: left; color: var(--text-color); }
    .session-icon { flex-shrink: 0; }
    .session-title { flex-grow: 1; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
    #session-list li:hover { background-color: var(--sidebar-hover-bg); }
    button.session-button.active { background-color: var(--sidebar-active-bg); font-weight: bold; }
    .session-buttons { display: flex; align-items: center; padding-right: 0.5rem; }
    .session-buttons button { background: none; border: none; color: var(--text-color); cursor: pointer; opacity: 0; padding: 2px 4px; font-size: 0.9rem; transition: opacity 0.2s;}
    #session-list li:hover .session-buttons button { opacity: 1; }
    .sidebar-footer { padding: 1rem; border-top: 1px solid var(--border-color); font-size: 0.9rem; }
    .footer-action { display: flex; justify-content: space-between; align-items: center; width: 100%; padding: 0.5rem 0.25rem; }
    #voice-chat-toggle { transform: scale(0.8); }
    .chat-container { flex-grow: 1; display: flex; flex-direction: column; }
    #chat-box { flex-grow: 1; padding: 1rem; overflow-y: auto; }
    #new-chat-prompt-selector { padding: 0.5rem 1rem; border-bottom: 1px solid var(--border-color); background-color: var(--sidebar-bg); }
    #prompt-select-dropdown { padding: 0.25rem; border-radius: 4px; border: 1px solid var(--input-border); background-color: var(--input-bg); color: var(--text-color); }
    .message { margin-bottom: 1rem; max-width: 100%; display: flex; align-items: flex-start; gap: 10px; }
    .message .avatar { border-radius: 50%; background-color: var(--sidebar-bg); flex-shrink: 0; object-fit: cover; }
    .message.system { justify-content: center; max-width: 100%; }
    .message.system .message-content { background-color: var(--system-msg-bg); color: var(--text-color); border: 1px solid var(--border-color); font-style: italic; text-align: center; font-size: 0.9em;}
    .message-container { display: flex; flex-direction: column; max-width: 90%; }
    .message-sender { font-weight: bold; margin-bottom: 4px; font-size: 0.9em; }
    .message-content { padding: 0.75rem 1rem; border-radius: 10px; word-wrap: break-word; }
    .message.user { flex-direction: row-reverse; }
    .message.user .message-container { align-items: flex-end; }
    .message.user .avatar { background-color: var(--user-msg-bg); padding: 5px; box-sizing: border-box; border-radius: 50%; }
    .message.assistant .message-container { align-items: flex-start; }
    .message.user .message-content { background-color: var(--user-msg-bg); border-top-right-radius: 0; }
    .message.assistant .message-content { background-color: var(--ai-msg-bg); border-top-left-radius: 0; }
    :global(.message-content pre) { background-color: #282c34; color: #abb2bf; padding: 1rem; border-radius: 5px; overflow-x: auto; position: relative; }
    :global(.copy-btn) { position: absolute; top: 5px; right: 5px; background: #555; color: white; border: none; padding: 3px 6px; border-radius: 3px; cursor: pointer; opacity: 0.7; }
    :global(.copy-btn:hover) { opacity: 1; }
    .message-actions { margin-top: 8px; display: flex; gap: 8px; align-items: center; }
    .message-actions button { background: transparent; border: 1px solid var(--border-color); border-radius: 5px; padding: 4px 8px; cursor: pointer; color: var(--text-color); font-size: 1rem; }
    .message-actions button.hidden { display: none; }
    .message-actions button.playing { color: var(--button-bg); border-color: var(--button-bg); }
    .input-area { border-top: 1px solid var(--border-color); padding: 1rem; display: flex; align-items: center; }
    #input-message { flex-grow: 1; padding: 0.75rem; border: 1px solid var(--input-border); border-radius: 5px; font-size: 1rem; resize: none; background-color: var(--input-bg); color: var(--text-color); }
    .hidden { display: none !important; }
    #settings-overlay, #full-voice-overlay { position: fixed; top: 0; left: 0; width: 100%; height: 100%; background-color: rgba(0, 0, 0, 0.7); z-index: 1000; display: flex; flex-direction: column; justify-content: center; align-items: center; }
    #full-voice-overlay { cursor: pointer; }
    #settings-modal { position: fixed; top: 50%; left: 50%; transform: translate(-50%, -50%); background-color: var(--bg-color); color: var(--text-color); padding: 2rem; border-radius: 8px; box-shadow: 0 5px 15px rgba(0,0,0,0.3); z-index: 1001; width: 90%; max-width: 700px; max-height: 90vh; overflow-y: auto; }
    :global(#settings-form fieldset) { border: 1px solid var(--border-color); border-radius: 4px; padding: 1rem; margin-bottom: 1.5rem; }
    :global(#settings-form legend) { padding: 0 0.5rem; font-weight: bold; }
    :global(#settings-form label) { display: block; margin-bottom: 0.5rem; }
    :global(#settings-form input[type="text"]), :global(#settings-form input[type="number"]), :global(#settings-form textarea), :global(#settings-form select) { width: 100%; box-sizing: border-box; padding: 0.5rem; margin-bottom: 1rem; background-color: var(--input-bg); color: var(--text-color); border: 1px solid var(--input-border); border-radius: 4px; }
    :global(.prompt-editor-entry) { display: grid; grid-template-columns: 1fr 1fr auto; gap: 0.5rem 1rem; margin-bottom: 1rem; padding-bottom: 1rem; border-bottom: 1px solid var(--border-color); }
    :global(.prompt-editor-entry:last-child) { border-bottom: none; }
    :global(.prompt-editor-entry .prompt-title-wrapper) { grid-column: 1 / 2; }
    :global(.prompt-editor-entry .prompt-name-wrapper) { grid-column: 2 / 3; }
    :global(.prompt-editor-entry .remove-prompt-btn) { grid-column: 3 / 4; grid-row: 2 / 3; background-color: var(--danger-button-bg); color: var(--button-text); border: none; padding: 0.5rem; border-radius: 4px; cursor: pointer; }
    :global(.prompt-editor-entry .prompt-icon-wrapper) { grid-column: 1 / 2; grid-row: 2 / 3; }
    :global(.prompt-editor-entry textarea) { grid-column: 1 / 4; min-height: 80px; }
    :global(.modal-buttons) { display: flex; justify-content: flex-end; gap: 1rem; }
    :global(#add-prompt-btn) { justify-self: start; margin-bottom: 1rem; }
    #pulsing-circle { width: 150px; height: 150px; border: 5px solid var(--button-bg); border-radius: 50%; animation: pulse 2s infinite ease-in-out; }
    @keyframes pulse { 0% { transform: scale(0.95); opacity: 0.7; } 70% { transform: scale(1.1); opacity: 1; } 100% { transform: scale(0.95); opacity: 0.7; } }
    #voice-status-text { margin-top: 2rem; color: #ffffff; font-size: 1.5rem; text-shadow: 1px 1px 2px black; }
    #menu-toggle-btn, #mobile-overlay { display: none; }

    /* Icon Sizing CSS - Updated values for a wider range */
    :global(.icon-size-small) .session-icon { width: 20px; height: 20px; }
    :global(.icon-size-small) .message .avatar { width: 28px; height: 28px; }
    :global(.icon-size-medium) .session-icon { width: 24px; height: 24px; }
    :global(.icon-size-medium) .message .avatar { width: 32px; height: 32px; }
    :global(.icon-size-large) .session-icon { width: 32px; height: 32px; }
    :global(.icon-size-large) .message .avatar { width: 48px; height: 48px; }
    :global(.icon-size-xl) .session-icon { width: 40px; height: 40px; }
    :global(.icon-size-xl) .message .avatar { width: 96px; height: 96px; }

    /* --- Responsive Design for Mobile --- */
    @media (max-width: 768px) {
        #menu-toggle-btn {
            display: block;
            position: fixed;
            top: 10px;
            left: 10px;
            z-index: 1200;
            background-color: var(--sidebar-bg);
            color: var(--text-color);
            border: 1px solid var(--border-color);
            border-radius: 5px;
            width: 44px;
            height: 44px;
            font-size: 24px;
            line-height: 44px;
            text-align: center;
            cursor: pointer;
            padding: 0;
        }

        .sidebar {
            position: fixed;
            top: 0;
            left: 0;
            height: 100%;
            z-index: 1100;
            transform: translateX(-100%);
            transition: transform 0.3s ease-in-out;
            width: 280px; /* Slightly wider for better touch targets */
            box-shadow: 3px 0 15px rgba(0,0,0,0.2);
        }

        .sidebar.open {
            transform: translateX(0);
        }

        #mobile-overlay {
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            background: rgba(0,0,0,0.5);
            z-index: 1050; /* Below sidebar */
        }

        #mobile-overlay.active {
            display: block;
        }

        .chat-container {
            width: 100vw;
        }

        .input-area {
            padding-bottom: calc(1rem + env(safe-area-inset-bottom));
        }

        :global(#settings-modal) {
            width: 100%;
            height: 100%;
            max-width: none;
            max-height: none;
            border-radius: 0;
            top: 0;
            left: 0;
            transform: none;
            padding: 1rem;
            box-sizing: border-box;
            overflow-y: auto;
        }

        :global(.prompt-editor-entry) {
            grid-template-columns: 1fr; /* Stack all elements */
            gap: 0.5rem;
        }

        :global(.prompt-editor-entry > div),
        :global(.prompt-editor-entry > textarea),
        :global(.prompt-editor-entry > button) {
            grid-column: 1 / -1; /* Make all items span the full width */
            grid-row: auto; /* Let them stack naturally */
        }

        :global(.prompt-editor-entry .remove-prompt-btn) {
            width: auto;
            padding: 0.5rem 1rem;
            justify-self: end; /* Align remove button to the right */
            margin-top: 0.5rem;
        }
    }
</style>