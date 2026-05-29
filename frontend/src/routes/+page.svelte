<script lang="ts">
	import { getNews, getDailyNews, type NewsCluster } from '$lib/api';
	import NewsCard from '$lib/components/NewsCard.svelte';
	import DailyDigest from '$lib/components/DailyDigest.svelte';
	import { page } from '$app/stores';
	import { browser } from '$app/environment';

	let items = $state<NewsCluster[]>([]);
	let dailyItems = $state<NewsCluster[]>([]);
	let currentPage = $state(1);
	let totalPages = $state(1);
	let loading = $state(true);
	let activeCategory = $state('');

	async function load(cat: string, pg: number) {
		loading = true;
		const params: Record<string, string> = { page: String(pg), per_page: '20', sort: 'popularity' };
		if (cat) params.category = cat;
		try {
			const data = await getNews(params);
			items = data.items;
			totalPages = data.pagination.pages;
			currentPage = data.pagination.page;
		} catch (e) { console.error(e); items = []; }
		loading = false;
	}

	$effect(() => {
		const c = $page.url.searchParams.get('category') || '';
		const p = parseInt($page.url.searchParams.get('page') || '1');
		activeCategory = c;
		load(c, p);
	});

	$effect(() => {
		if (browser) {
			const today = new Date().toISOString().split('T')[0];
			getDailyNews(today)
				.then(d => dailyItems = Object.values(d).flat().sort((a, b) => b.popularity_score - a.popularity_score))
				.catch(() => {});
		}
	});
</script>

{#if loading}
	<div class="text-center py-12 text-gray-500">⏳ Ładowanie...</div>
{:else}
	<DailyDigest items={dailyItems} />
	{#if items.length === 0}
		<div class="text-center py-12 text-gray-500">Brak newsów. Kliknij "Odśwież" aby pobrać.</div>
	{:else}
		<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
			{#each items as item (item.id)}
				<NewsCard {item} />
			{/each}
		</div>
		{#if totalPages > 1}
			<div class="flex justify-center gap-2 mt-8">
				{#each Array(totalPages) as _, i}
					<a href="?category={activeCategory}&page={i + 1}" class="px-3 py-1 rounded text-sm {currentPage === i + 1 ? 'bg-blue-600 text-white' : 'bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 dark:hover:bg-gray-600'}">{i + 1}</a>
				{/each}
			</div>
		{/if}
	{/if}
{/if}
