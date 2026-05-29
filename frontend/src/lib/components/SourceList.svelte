<script lang="ts">
	import type { SourceRef } from '$lib/api';
	let { sources = [] }: { sources: SourceRef[] } = $props();
	const typeLabels: Record<string, string> = { reddit: 'Reddit', twitter: 'X', youtube: 'YT', rss: 'RSS', scrape: 'Web' };
</script>

<div class="flex flex-wrap gap-1.5 mt-2">
	{#each sources as src}
		<a href={src.url} target="_blank" rel="noopener"
			class="text-xs px-2 py-0.5 rounded-full bg-gray-100 dark:bg-gray-700 text-gray-600 dark:text-gray-300 hover:underline">
			{typeLabels[src.type] || src.type}: {src.name}
		</a>
	{/each}
</div>
