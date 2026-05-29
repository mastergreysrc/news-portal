<script lang="ts">
	import { refreshNews } from '$lib/api';
	import { adminKey } from '$lib/stores';

	let { category = 'gaming' }: { category: string } = $props();
	let loading = $state(false);
	let message = $state('');

	async function handleRefresh() {
		if (!$adminKey) { message = '✗ Brak klucza admina'; return; }
		loading = true; message = '⏳ Odświeżanie...';
		try {
			await refreshNews(category, $adminKey);
			message = '✓ Odświeżono!';
			setTimeout(() => message = '', 3000);
			window.location.reload();
		} catch { message = '✗ Błąd'; }
		loading = false;
	}
</script>

<button onclick={handleRefresh} disabled={loading}
	class="px-3 py-1.5 text-sm rounded-lg border border-gray-300 dark:border-gray-600 hover:bg-gray-100 dark:hover:bg-gray-700 disabled:opacity-50 transition">
	{loading ? '⏳' : '🔄'} {message || 'Odśwież'}
</button>
