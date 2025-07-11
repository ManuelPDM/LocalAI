import adapter from '@sveltejs/adapter-static'; // Import the adapter
import { vitePreprocess } from '@sveltejs/vite-plugin-svelte';

/** @type {import('@sveltejs/kit').Config} */
const config = {
	// Consult https://kit.svelte.dev/docs/integrations#preprocessors
	// for more information about preprocessors
	preprocess: vitePreprocess(),

	kit: {
		// adapter-auto only supports some environments, see https://kit.svelte.dev/docs/adapter-auto for a list.
		// If your environment is not supported or you settled on a specific environment, switch out the adapter.
		// See https://kit.svelte.dev/docs/adapters for more information about adapters.
		adapter: adapter({
			// default options are fine for our use case.
			// The output will be in the `build` directory.
			pages: 'build',
			assets: 'build',
			fallback: 'index.html', // Important for single-page applications
			precompress: false,
			strict: true
		})
	}
};

export default config;