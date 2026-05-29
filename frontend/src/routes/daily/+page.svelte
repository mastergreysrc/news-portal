<script lang="ts">
	import { getDailyNews, type NewsCluster } from '$lib/api';
	import NewsCard from '$lib/components/NewsCard.svelte';
	import { browser } from '$app/environment';

	let dailyData = $state<Record<string, NewsCluster[]>>({});
	let loading = $state(true);

	$effect(() => {
		if (browser) {
			const today = new Date().toISOString().split('T')[0];
			getDailyNews(today)
				.then(d => dailyData = d)
				.catch(() => {})
				.finally(() => loading = false);
		}
	});
</script>

<h1 class="text-2xl font-bold mb-6 text-gray-900 dark:text-gray-100">📰 News dnia</h1>

{#if loading}
	<div class="text-center py-12 text-gray-500">⏳ Ładowanie...</div>
{:else if Object.keys(dailyData).length === 0}
	<div class="text-center py-12 text-gray-500">Brak newsów na dziś.</div>
{:else}
	{#each Object.entries(dailyData) as [category, items]}
		<section class="mb-8">
			<h2 class="text-lg font-semibold mb-4 text-gray-900 dark:text-gray-100">{category}</h2>
			<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
				{#each items as item (item.id)}
					<NewsCard {item} />
				{/each}
			</div>
		</section>
	{/each}
{/if}
