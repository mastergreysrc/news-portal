<script lang="ts">
	import { getNews, getCategories, type NewsCluster, type Category } from '$lib/api';
	import NewsCard from '$lib/components/NewsCard.svelte';
	import { page } from '$app/stores';

	let { data }: { data: { slug: string } } = $props();

	let items = $state<NewsCluster[]>([]);
	let categoryName = $state('');
	let currentPage = $state(1);
	let totalPages = $state(1);
	let loading = $state(true);

	async function load(slug: string, pg: number) {
		loading = true;
		try {
			const cats = await getCategories();
			const cat = cats.find(c => c.slug === slug);
			categoryName = cat ? `${cat.icon} ${cat.name}` : slug;
		} catch { categoryName = slug; }

		try {
			const data = await getNews({ category: slug, page: String(pg), per_page: '20', sort: 'popularity' });
			items = data.items;
			totalPages = data.pagination.pages;
			currentPage = data.pagination.page;
		} catch (e) { console.error(e); items = []; }
		loading = false;
	}

	$effect(() => {
		const slug = $page.params.slug;
		const p = parseInt($page.url.searchParams.get('page') || '1');
		if (slug) load(slug, p);
	});
</script>

<h1 class="text-2xl font-bold mb-6 text-gray-900 dark:text-gray-100">{categoryName || 'Kategoria'}</h1>

{#if loading}
	<div class="text-center py-12 text-gray-500">⏳ Ładowanie...</div>
{:else if items.length === 0}
	<div class="text-center py-12 text-gray-500">Brak newsów w tej kategorii.</div>
{:else}
	<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
		{#each items as item (item.id)}
			<NewsCard {item} />
		{/each}
	</div>
	{#if totalPages > 1}
		<div class="flex justify-center gap-2 mt-8">
			{#each Array(totalPages) as _, i}
				<a href="?page={i + 1}" class="px-3 py-1 rounded text-sm {currentPage === i + 1 ? 'bg-blue-600 text-white' : 'bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 dark:hover:bg-gray-600'}">{i + 1}</a>
			{/each}
		</div>
	{/if}
{/if}
