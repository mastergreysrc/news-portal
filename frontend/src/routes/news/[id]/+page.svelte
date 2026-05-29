<script lang="ts">
	import { getCluster, toggleFavorite, type NewsCluster } from '$lib/api';
	import FireBadge from '$lib/components/FireBadge.svelte';
	import SourceList from '$lib/components/SourceList.svelte';
	import { token } from '$lib/stores';
	import { page } from '$app/stores';

	let cluster = $state<(NewsCluster & { source_items?: { source: string; title: string; url: string; snippet: string }[] }) | null>(null);
	let loading = $state(true);
	let favorited = $state(false);
	let favLoading = $state(false);

	async function load(id: number) {
		loading = true;
		try {
			const data = await getCluster(id);
			cluster = data;
			favorited = data.is_favorited;
		} catch (e) { console.error(e); }
		loading = false;
	}

	async function handleFav() {
		if (!$token || favLoading || !cluster) return;
		favLoading = true;
		try {
			const res = await toggleFavorite(cluster.id);
			favorited = res.favorited;
		} catch { /* ignore */ }
		favLoading = false;
	}

	function formatDate(dateStr: string | null): string {
		if (!dateStr) return '';
		return new Date(dateStr).toLocaleDateString('pl-PL', {
			year: 'numeric', month: 'long', day: 'numeric', hour: '2-digit', minute: '2-digit'
		});
	}

	$effect(() => {
		const id = parseInt($page.params.id);
		if (id) load(id);
	});
</script>

{#if loading}
	<div class="text-center py-12 text-gray-500">⏳ Ładowanie...</div>
{:else if cluster}
	<article class="max-w-3xl mx-auto">
		<a href="/" class="text-sm text-blue-600 hover:underline mb-4 inline-block">← Powrót</a>

		<div class="bg-white dark:bg-gray-800 rounded-xl p-6 border border-gray-200 dark:border-gray-700">
			<div class="flex items-start gap-3 mb-4">
				<FireBadge tier={cluster.fire_tier} />
				<div>
					<span class="text-sm text-gray-500 dark:text-gray-400">{cluster.category.icon} {cluster.category.name}</span>
					<span class="text-sm text-gray-400 ml-4">Popularność: {cluster.popularity_score.toFixed(0)}</span>
				</div>
			</div>

			<h1 class="text-2xl font-bold text-gray-900 dark:text-gray-100 mb-3">{cluster.canonical_title}</h1>

			{#if cluster.canonical_summary}
				<p class="text-gray-700 dark:text-gray-300 mb-4 leading-relaxed">{cluster.canonical_summary}</p>
			{/if}

			{#if cluster.published_at}
				<p class="text-sm text-gray-500 mb-4">📅 {formatDate(cluster.published_at)}</p>
			{/if}

			<div class="mb-4">
				<span class="text-sm text-gray-500">Źródła ({cluster.source_count}):</span>
				<SourceList sources={cluster.sources} />
			</div>

			{#if $token}
				<button onclick={handleFav} disabled={favLoading}
					class="px-4 py-2 rounded-lg text-sm transition {favorited ? 'bg-yellow-100 text-yellow-700 hover:bg-yellow-200' : 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600'}">
					{favLoading ? '⏳' : favorited ? '🔖 Zapisane' : '🔖 Zapisz'}
				</button>
			{/if}

			{#if cluster.source_items && cluster.source_items.length > 0}
				<div class="mt-6 pt-6 border-t border-gray-200 dark:border-gray-700">
					<h2 class="text-lg font-semibold mb-3 text-gray-900 dark:text-gray-100">Wszystkie źródła ({cluster.source_items.length})</h2>
					<div class="space-y-3">
						{#each cluster.source_items as src}
							<a href={src.url} target="_blank" rel="noopener" class="block p-3 rounded-lg border border-gray-200 dark:border-gray-700 hover:border-blue-400 dark:hover:border-blue-500 transition">
								<div class="text-xs text-gray-500 mb-1">{src.source}</div>
								<div class="font-medium text-gray-900 dark:text-gray-100">{src.title}</div>
								{#if src.snippet}
									<p class="text-sm text-gray-600 dark:text-gray-400 mt-1 line-clamp-2">{src.snippet}</p>
								{/if}
							</a>
						{/each}
					</div>
				</div>
			{/if}
		</div>
	</article>
{:else}
	<div class="text-center py-12 text-gray-500">Nie znaleziono newsa.</div>
{/if}
