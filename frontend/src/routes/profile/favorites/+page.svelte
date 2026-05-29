<script lang="ts">
	import { getFavorites, type NewsCluster } from '$lib/api';
	import NewsCard from '$lib/components/NewsCard.svelte';
	import { token } from '$lib/stores';
	import { goto } from '$app/navigation';
	import { browser } from '$app/environment';

	let items = $state<NewsCluster[]>([]);
	let loading = $state(true);

	$effect(() => {
		if (browser) {
			if (!$token) {
				goto('/login');
				return;
			}
			getFavorites()
				.then(f => items = f)
				.catch(() => {})
				.finally(() => loading = false);
		}
	});
</script>

<h1 class="text-2xl font-bold mb-6 text-gray-900 dark:text-gray-100">🔖 Ulubione</h1>

{#if loading}
	<div class="text-center py-12 text-gray-500">⏳ Ładowanie...</div>
{:else if items.length === 0}
	<div class="text-center py-12 text-gray-500">Nie masz jeszcze zapisanych newsów. Kliknij 🔖 na karcie newsa, aby zapisać.</div>
{:else}
	<div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
		{#each items as item (item.id)}
			<NewsCard {item} />
		{/each}
	</div>
{/if}
