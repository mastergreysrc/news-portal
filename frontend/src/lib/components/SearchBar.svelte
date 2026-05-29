<script lang="ts">
	import { goto } from '$app/navigation';
	let query = $state('');

	function handleSubmit(e: SubmitEvent) {
		e.preventDefault();
		if (query.trim()) goto(`/search?q=${encodeURIComponent(query.trim())}`);
	}
</script>

<form onsubmit={handleSubmit} class="flex gap-2">
	<input type="search" bind:value={query} placeholder="Szukaj newsów..."
		class="flex-1 px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500" />
	<button type="submit" class="px-4 py-2 bg-blue-600 text-white rounded-lg text-sm hover:bg-blue-700 transition">Szukaj</button>
</form>
