<script lang="ts">
	import { searchNews, type NewsCluster } from '$lib/api';
	import NewsCard from '$lib/components/NewsCard.svelte';
	import { page } from '$app/stores';

	let items = $state<NewsCluster[]>([]);
	let currentPage = $state(1);
	let totalPages = $state(1);
	let loading = $state(true);
	let query = $state('');

	async function search(q: string, pg: number) {
		if (!q.trim()) { items = []; loading = false; return; }
		loading = true;
		try {
			const data = await searchNews(q, pg);
			items = data.items;
			totalPages = data.pagination.pages;
			currentPage = data.pagination.page;
		} catch (e) { console.error(e); items = []; }
		loading = false;
	}

	$effect(() => {
		const q = $page.url.searchParams.get('q') || '';
		const p = parseInt($page.url.searchParams.get('page') || '1');
		query = q;
		search(q, p);
	});
</script>

<h1 class="text-2xl font-bold mb-6 text-gray-900 dark:text-gray-100">
	{#if query}
		Wyniki wyszukiwania: "{query}"
	{:else}
		Wyszukiwanie
	{/if}
</h1>

{#if loading}
	<div class="text-center py-12 text-gray-500">⏳ Szukanie...</div>
{:else if items.length === 0}
	<div class="text-center py-12 text-gray-500">
		{#if query}
			Brak wyników dla "{query}".
		{:else}
			Wpisz frazę w polu wyszukiwania.
		{/if}
	</div>
{:else}
	<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
		{#each items as item (item.id)}
			<NewsCard {item} />
		{/each}
	</div>
	{#if totalPages > 1}
		<div class="flex justify-center gap-2 mt-8">
			{#each Array(totalPages) as _, i}
				<a href="?q={encodeURIComponent(query)}&page={i + 1}" class="px-3 py-1 rounded text-sm {currentPage === i + 1 ? 'bg-blue-600 text-white' : 'bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 dark:hover:bg-gray-600'}">{i + 1}</a>
			{/each}
		</div>
	{/if}
{/if}
