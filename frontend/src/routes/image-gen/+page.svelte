<!-- File: frontend/src/routes/image-gen/+page.svelte -->
<script>
    import { onMount } from 'svelte';

    // UI state for inputs
    let prompt = '';
    let negativePrompt = 'ugly, deformed, disfigured, poor quality, lowres, bad anatomy, extra limbs, blurry';
    let width = 512;
    let height = 512;
    let steps = 25;
    let cfgScale = 7.0;

    // Model management state
    let availableModels = []; // List of model filenames from the backend
    let selectedModel = '';   // The model currently selected in the dropdown
    let currentLoadedModel = 'None'; // The model actually loaded in the backend
    let deviceUsed = 'N/A'; // Device reported by backend

    // Loading/error states
    let isLoading = false;
    let isModelLoading = false; // New state for model load/unload operations
    let errorMessage = null;
    let imageUrl = null;

    onMount(async () => {
        await fetchModelList();
        await updateModelStatus();
        // If there are models, pre-select the first one in the dropdown
        if (availableModels.length > 0) {
            selectedModel = availableModels[0];
        }
    });

    async function fetchModelList() {
        try {
            const response = await fetch('/api/image/models');
            if (!response.ok) {
                throw new Error(`Failed to fetch model list: ${response.statusText}`);
            }
            const data = await response.json();
            availableModels = data.models;
        } catch (error) {
            console.error('Error fetching model list:', error);
            errorMessage = `Could not fetch model list: ${error.message}`;
        }
    }

    async function updateModelStatus() {
        try {
            const response = await fetch('/api/image/health');
            if (!response.ok) {
                throw new Error(`Failed to fetch model status: ${response.statusText}`);
            }
            const data = await response.json();
            currentLoadedModel = data.loaded_model_name || 'None';
            deviceUsed = data.device;
            // Also update available models in case they changed on disk
            await fetchModelList();
        } catch (error) {
            console.error('Error updating model status:', error);
            errorMessage = `Could not get model status: ${error.message}`;
        }
    }

    async function loadSelectedModel() {
        if (!selectedModel || isModelLoading) return;

        isModelLoading = true;
        errorMessage = null;
        try {
            const response = await fetch('/api/image/load', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ model_filename: selectedModel }),
            });

            const data = await response.json();
            if (!response.ok) {
                throw new Error(data.message || `Failed to load model: ${response.statusText}`);
            }
            // Update the loaded model status on success
            currentLoadedModel = data.loaded_model_name;
        } catch (error) {
            console.error('Error loading model:', error);
            errorMessage = `Failed to load model: ${error.message}`;
        } finally {
            isModelLoading = false;
        }
    }

    async function unloadCurrentModel() {
        if (currentLoadedModel === 'None' || isModelLoading) return;

        isModelLoading = true;
        errorMessage = null;
        try {
            const response = await fetch('/api/image/unload', {
                method: 'POST',
            });

            const data = await response.json();
            if (!response.ok) {
                throw new Error(data.message || `Failed to unload model: ${response.statusText}`);
            }
            // Update the loaded model status on success
            currentLoadedModel = 'None';
        } catch (error) {
            console.error('Error unloading model:', error);
            errorMessage = `Failed to unload model: ${error.message}`;
        } finally {
            isModelLoading = false;
        }
    }

    async function generateImage() {
        isLoading = true;
        errorMessage = null;
        if (imageUrl) {
            URL.revokeObjectURL(imageUrl);
            imageUrl = null;
        }

        if (currentLoadedModel === 'None') {
            errorMessage = "No model is loaded. Please load a model before generating an image.";
            isLoading = false;
            return;
        }

        const requestBody = {
            prompt: prompt,
            negative_prompt: negativePrompt,
            width: width,
            height: height,
            num_inference_steps: steps,
            guidance_scale: cfgScale,
        };

        try {
            const response = await fetch('/api/image/generate', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify(requestBody),
            });

            if (!response.ok) {
                const errorText = await response.text();
                throw new Error(`Server error: ${response.status} - ${errorText}`);
            }

            const imageBlob = await response.blob();
            imageUrl = URL.createObjectURL(imageBlob);

        } catch (error) {
            console.error('Generation failed:', error);
            errorMessage = error.message;
        } finally {
            isLoading = false;
        }
    }
</script>

<div class="image-gen-container">
    <div class="controls-panel">
        <header class="panel-header">
            <h2>Image Generation</h2>
            <p>Select your model and craft your visual masterpiece.</p>
        </header>

        <!-- Model Selection and Management -->
        <div class="model-management-section">
            <h3>Model Management</h3>
            <p class="model-status">Loaded: <span>{currentLoadedModel}</span> on <span>{deviceUsed}</span></p>

            <div class="control-group">
                <label for="model-select">Select Model</label>
                <select id="model-select" bind:value={selectedModel} disabled={isModelLoading || availableModels.length === 0}>
                    {#each availableModels as model}
                        <option value={model}>{model}</option>
                    {:else}
                        <option value="" disabled>No models found</option>
                    {/each}
                </select>
            </div>

            <div class="model-buttons">
                <button on:click={loadSelectedModel} disabled={isModelLoading || !selectedModel || selectedModel === currentLoadedModel}>
                    {#if isModelLoading && selectedModel === currentLoadedModel}
                        Loading...
                    {:else}
                        Load Selected
                    {/if}
                </button>
                <button on:click={unloadCurrentModel} disabled={isModelLoading || currentLoadedModel === 'None'}>
                    {#if isModelLoading && currentLoadedModel !== 'None'}
                        Unloading...
                    {:else}
                        Unload Current
                    {/if}
                </button>
            </div>
        </div>

        <!-- Generation Controls -->
        <h3>Generation Controls</h3>
        <div class="control-group">
            <label for="prompt">Prompt</label>
            <textarea id="prompt" bind:value={prompt} rows="6" placeholder="A stunning portrait of a character..."></textarea>
        </div>

        <div class="control-group">
            <label for="negative-prompt">Negative Prompt</label>
            <textarea id="negative-prompt" bind:value={negativePrompt} rows="3"></textarea>
        </div>

        <div class="control-grid">
            <div class="control-group">
                <label for="width">Width</label>
                <input id="width" type="number" bind:value={width} step="64" />
            </div>
            <div class="control-group">
                <label for="height">Height</label>
                <input id="height" type="number" bind:value={height} step="64" />
            </div>
            <div class="control-group">
                <label for="steps">Steps</label>
                <input id="steps" type="number" bind:value={steps} step="1" />
            </div>
            <div class="control-group">
                <label for="cfg">CFG Scale</label>
                <input id="cfg" type="number" bind:value={cfgScale} step="0.5" />
            </div>
        </div>

        <button class="generate-btn" on:click={generateImage} disabled={isLoading || currentLoadedModel === 'None'}>
            {#if isLoading}
                <div class="spinner"></div>
                <span>Generating...</span>
            {:else}
                <span>Generate Image</span>
            {/if}
        </button>
    </div>

    <div class="display-panel">
        {#if isModelLoading}
            <div class="placeholder">
                <div class="spinner large"></div>
                <p>Loading model, please wait...</p>
            </div>
        {:else if isLoading}
            <div class="placeholder">
                <div class="spinner large"></div>
                <p>Conjuring pixels...</p>
            </div>
        {:else if errorMessage}
            <div class="placeholder error">
                <h3>Operation Failed</h3>
                <p>{errorMessage}</p>
                <button on:click={() => errorMessage = null}>Clear Error</button>
            </div>
        {:else if imageUrl}
            <img src={imageUrl} alt="Generated art" class="generated-image" />
        {:else}
            <div class="placeholder">
                <svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="18" height="18" rx="2" ry="2"></rect><circle cx="8.5" cy="8.5" r="1.5"></circle><polyline points="21 15 16 10 5 21"></polyline></svg>
                <p>Your generated image will appear here.</p>
                <p>Ensure a model is loaded in the control panel.</p>
            </div>
        {/if}
    </div>
</div>


<style>
    .image-gen-container {
        display: flex;
        height: 100%;
        width: 100%;
        background-color: var(--bg-color);
        color: var(--text-color);
    }

    .controls-panel {
        width: 380px; /* Slightly wider for new controls */
        flex-shrink: 0;
        padding: 2rem;
        background-color: var(--sidebar-bg);
        border-right: 1px solid var(--border-color);
        display: flex;
        flex-direction: column;
        gap: 1.5rem;
        overflow-y: auto;
    }

    .panel-header h2 {
        margin: 0 0 0.25rem 0;
        font-size: 1.5rem;
    }

    .panel-header p {
        margin: 0;
        font-size: 0.9rem;
        color: #888;
    }
    :global(body.dark-mode) .panel-header p {
        color: #aaa;
    }

    .model-management-section {
        border: 1px solid var(--border-color);
        border-radius: 8px;
        padding: 1rem;
        display: flex;
        flex-direction: column;
        gap: 1rem;
    }
    .model-management-section h3 {
        margin: 0 0 0.5rem 0;
        font-size: 1.1rem;
        color: var(--text-color);
    }
    .model-status {
        font-size: 0.9rem;
        color: #666;
    }
    .model-status span {
        font-weight: bold;
        color: var(--text-color);
    }
    :global(body.dark-mode) .model-status {
        color: #bbb;
    }
    :global(body.dark-mode) .model-status span {
        color: #fff;
    }

    .control-group {
        display: flex;
        flex-direction: column;
    }

    .control-group label {
        margin-bottom: 0.5rem;
        font-weight: 500;
        font-size: 0.9rem;
    }

    .control-group input,
    .control-group textarea,
    .control-group select {
        width: 100%;
        box-sizing: border-box;
        padding: 0.75rem;
        background-color: var(--input-bg);
        color: var(--text-color);
        border: 1px solid var(--input-border);
        border-radius: 6px;
        font-size: 1rem;
        font-family: inherit;
    }
    .control-group textarea {
        resize: vertical;
    }

    .model-buttons {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 0.75rem;
    }
    .model-buttons button {
        padding: 0.75rem;
        font-size: 0.9rem;
        font-weight: 600;
        border: none;
        border-radius: 6px;
        cursor: pointer;
        transition: background-color 0.2s;
        background-color: #6c757d; /* Grey button */
        color: white;
    }
    .model-buttons button:hover:not(:disabled) {
        background-color: #5a6268;
    }
    .model-buttons button:disabled {
        opacity: 0.7;
        cursor: not-allowed;
    }
    :global(body.dark-mode) .model-buttons button {
        background-color: #495057;
    }
    :global(body.dark-mode) .model-buttons button:hover:not(:disabled) {
        background-color: #6c757d;
    }

    .control-grid {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 1rem;
    }

    .generate-btn {
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 0.75rem;
        width: 100%;
        padding: 1rem;
        font-size: 1rem;
        font-weight: 600;
        background-color: var(--button-bg);
        color: var(--button-text);
        border: none;
        border-radius: 6px;
        cursor: pointer;
        transition: background-color 0.2s;
        margin-top: auto; /* Push to bottom */
    }
    .generate-btn:hover:not(:disabled) {
        background-color: var(--button-hover-bg);
    }
    .generate-btn:disabled {
        opacity: 0.7;
        cursor: not-allowed;
    }

    .display-panel {
        flex-grow: 1;
        display: flex;
        align-items: center;
        justify-content: center;
        padding: 2rem;
        background-color: var(--bg-color);
    }

    .generated-image {
        max-width: 100%;
        max-height: 100%;
        object-fit: contain;
        border-radius: 8px;
        box-shadow: 0 10px 25px rgba(0,0,0,0.1);
    }
    :global(body.dark-mode) .generated-image {
         box-shadow: 0 10px 25px rgba(0,0,0,0.4);
    }

    .placeholder {
        display: flex;
        flex-direction: column;
        align-items: center;
        justify-content: center;
        text-align: center;
        color: #999;
        border: 2px dashed var(--border-color);
        border-radius: 12px;
        width: 100%;
        height: 100%;
    }
    :global(body.dark-mode) .placeholder {
        color: #777;
    }
    .placeholder svg {
        margin-bottom: 1rem;
    }
    .placeholder.error {
        color: var(--danger-button-bg);
        border-color: var(--danger-button-bg);
        padding: 1rem;
    }
    .placeholder.error button {
        background: var(--danger-button-bg);
        color: white;
        border: none;
        padding: 0.5rem 1rem;
        border-radius: 5px;
        margin-top: 1rem;
        cursor: pointer;
    }

    .spinner {
        border: 2px solid #f3f3f3;
        border-top: 2px solid var(--button-text);
        border-radius: 50%;
        width: 16px;
        height: 16px;
        animation: spin 1s linear infinite;
    }
    .generate-btn .spinner, .model-buttons button .spinner {
        border-top-color: var(--button-text);
    }
    .display-panel .spinner {
        border-top-color: var(--text-color);
    }
    .spinner.large {
        width: 48px;
        height: 48px;
        border-width: 4px;
    }

    @keyframes spin {
        0% { transform: rotate(0deg); }
        100% { transform: rotate(360deg); }
    }

    @media (max-width: 900px) {
        .image-gen-container {
            flex-direction: column;
        }
        .controls-panel {
            width: 100%;
            height: auto;
            max-height: 50vh;
            border-right: none;
            border-bottom: 1px solid var(--border-color);
            padding: 1rem;
        }
        .generate-btn {
            margin-top: 1rem;
        }
    }
</style>