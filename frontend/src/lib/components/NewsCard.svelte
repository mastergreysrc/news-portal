<script lang="ts">
	import type { NewsCluster } from '$lib/api';
	import FireBadge from './FireBadge.svelte';
	import SourceList from './SourceList.svelte';
	import { token } from '$lib/stores';
	import { toggleFavorite } from '$lib/api';

	let { item }: { item: NewsCluster } = $props();
	let favorited = $state(false);
	let favLoading = $state(false);

	// Sync favorited from item prop
	$effect(() => {
		favorited = item.is_favorited;
	});

	async function handleFav(e: MouseEvent) {
		e.preventDefault();
		if (!$token || favLoading) return;
		favLoading = true;
		try {
			const res = await toggleFavorite(item.id);
			favorited = res.favorited;
		} catch { /* ignore */ }
		favLoading = false;
	}

	function timeAgo(dateStr: string | null): string {
		if (!dateStr) return '';
		const then = new Date(dateStr).getTime();
		const now = Date.now();
		const diff = Math.floor((now - then) / 1000);
		if (diff < 3600) return `${Math.floor(diff / 60)}m`;
		if (diff < 86400) return `${Math.floor(diff / 3600)}h`;
		return `${Math.floor(diff / 86400)}d`;
	}
</script>

<a href="/news/{item.id}" class="block group">
	<div class="border border-gray-200 dark:border-gray-700 rounded-xl p-4 hover:border-gray-400 dark:hover:border-gray-500 transition bg-white dark:bg-gray-800">
		<div class="flex items-start gap-2 mb-2">
			<FireBadge tier={item.fire_tier} />
			<span class="text-sm text-gray-500 dark:text-gray-400">{item.category.icon} {item.category.name}</span>
			<span class="ml-auto text-xs text-gray-400">{timeAgo(item.published_at)}</span>
		</div>
		<h3 class="font-semibold text-gray-900 dark:text-gray-100 group-hover:text-blue-600 dark:group-hover:text-blue-400 line-clamp-2">
			{item.canonical_title}
		</h3>
		{#if item.canonical_summary}
			<p class="text-sm text-gray-600 dark:text-gray-400 mt-1 line-clamp-2">{item.canonical_summary}</p>
		{/if}
		<SourceList sources={item.sources} />
		{#if $token}
			<button onclick={handleFav} class="mt-2 text-xs {favorited ? 'text-yellow-500' : 'text-gray-400'} hover:text-yellow-600">
				{favorited ? '🔖 Zapisane' : '🔖 Zapisz'}
			</button>
		{/if}
	</div>
</a>
