<script lang="ts">
	import type { NewsCluster } from '$lib/api';
	import FireBadge from './FireBadge.svelte';
	let { items = [] }: { items: NewsCluster[] } = $props();
</script>

{#if items.length > 0}
	<section class="mb-8">
		<h2 class="text-lg font-bold mb-4 text-gray-900 dark:text-gray-100">📰 News dnia</h2>
		<div class="grid grid-cols-1 md:grid-cols-3 gap-4">
			{#each items.slice(0, 3) as item}
				<a href="/news/{item.id}" class="block rounded-xl overflow-hidden border-2 border-blue-500/20 hover:border-blue-500/60 transition bg-white dark:bg-gray-800 p-4">
					<div class="flex items-center gap-2 mb-1"><FireBadge tier={item.fire_tier} /><span class="text-xs text-gray-500">{item.category.icon} {item.category.name}</span></div>
					<h3 class="font-bold text-gray-900 dark:text-gray-100 line-clamp-2">{item.canonical_title}</h3>
					<p class="text-sm text-gray-600 dark:text-gray-400 mt-1 line-clamp-2">{item.canonical_summary}</p>
				</a>
			{/each}
		</div>
	</section>
{/if}
