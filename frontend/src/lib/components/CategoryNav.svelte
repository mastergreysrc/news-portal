<script lang="ts">
	import type { Category } from '$lib/api';
	let { categories = [], active = '' }: { categories: Category[], active: string } = $props();
</script>

<nav class="flex overflow-x-auto gap-2 pb-2 scrollbar-hide">
	<a href="/" class="px-4 py-2 rounded-full text-sm whitespace-nowrap transition {!active ? 'bg-blue-600 text-white' : 'bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700'}">
		Wszystkie
	</a>
	{#each categories as cat}
		<a href="/category/{cat.slug}" class="px-4 py-2 rounded-full text-sm whitespace-nowrap transition {active === cat.slug ? 'bg-blue-600 text-white' : 'bg-gray-100 dark:bg-gray-800 hover:bg-gray-200 dark:hover:bg-gray-700'}">
			{cat.icon} {cat.name}
		</a>
	{/each}
</nav>
