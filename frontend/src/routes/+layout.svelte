<script lang="ts">
	import './layout.css';
	import favicon from '$lib/assets/favicon.svg';
	import { getCategories, type Category } from '$lib/api';
	import CategoryNav from '$lib/components/CategoryNav.svelte';
	import SearchBar from '$lib/components/SearchBar.svelte';
	import RefreshButton from '$lib/components/RefreshButton.svelte';
	import { token, adminKey } from '$lib/stores';
	import { page } from '$app/stores';
	import { browser } from '$app/environment';
	import { goto } from '$app/navigation';

	let { children } = $props();
	let categories = $state<Category[]>([]);

	let activeSlug = $derived(
		$page.url.pathname.startsWith('/category/')
			? $page.url.pathname.split('/')[2]
			: ''
	);

	function handleLogout() {
		$token = null;
		goto('/');
	}

	$effect(() => {
		if (browser) {
			getCategories().then(c => categories = c).catch(() => {});
		}
	});
</script>

<svelte:head><link rel="icon" href={favicon} /></svelte:head>

<div class="min-h-screen bg-gray-50 dark:bg-gray-900">
	<header class="sticky top-0 z-50 bg-white/80 dark:bg-gray-900/80 backdrop-blur border-b border-gray-200 dark:border-gray-800">
		<div class="max-w-6xl mx-auto px-4 py-3">
			<div class="flex items-center gap-4 mb-3">
				<a href="/" class="text-xl font-bold text-gray-900 dark:text-gray-100">🎮 Gaming News PL</a>
				<div class="flex-1 max-w-md"><SearchBar /></div>
				<RefreshButton />
				<div class="flex gap-2 items-center">
					{#if $token}
						<a href="/profile/favorites" class="text-sm text-gray-600 dark:text-gray-400 hover:underline">🔖 Ulubione</a>
						<button onclick={handleLogout} class="text-sm text-gray-600 dark:text-gray-400 hover:underline">Wyloguj</button>
					{:else}
						<a href="/login" class="text-sm text-gray-600 dark:text-gray-400 hover:underline">Zaloguj</a>
					{/if}
					{#if !$adminKey}
						<input type="password" placeholder="Admin key" class="text-xs w-24 px-1 py-0.5 border rounded dark:bg-gray-800 dark:border-gray-600" bind:value={$adminKey} />
					{:else}
						<span class="text-xs text-green-600" title="Admin key set">🟢</span>
					{/if}
				</div>
			</div>
			<CategoryNav {categories} active={activeSlug} />
		</div>
	</header>
	<main class="max-w-6xl mx-auto px-4 py-6">
		{@render children()}
	</main>
	<footer class="border-t border-gray-200 dark:border-gray-800 py-6 text-center text-sm text-gray-500">
		Gaming News PL — agregator newsów gamingowych po polsku. Zasilany przez Reddit, X, YouTube, RSS i więcej.
	</footer>
</div>
