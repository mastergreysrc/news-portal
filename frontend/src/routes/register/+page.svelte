<script lang="ts">
	import { register } from '$lib/api';
	import { token } from '$lib/stores';
	import { goto } from '$app/navigation';

	let username = $state('');
	let password = $state('');
	let error = $state('');
	let loading = $state(false);

	async function handleSubmit(e: SubmitEvent) {
		e.preventDefault();
		error = '';
		loading = true;
		try {
			const res = await register(username, password);
			$token = res.access_token;
			goto('/');
		} catch (err) {
			error = err instanceof Error ? err.message : 'Błąd rejestracji';
		}
		loading = false;
	}
</script>

<div class="max-w-sm mx-auto">
	<h1 class="text-2xl font-bold mb-6 text-gray-900 dark:text-gray-100">📝 Rejestracja</h1>

	<form onsubmit={handleSubmit} class="space-y-4">
		<div>
			<label for="reg-username" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Nazwa użytkownika</label>
			<input id="reg-username" type="text" bind:value={username} required minlength="3"
				class="w-full px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 focus:outline-none focus:ring-2 focus:ring-blue-500" />
		</div>
		<div>
			<label for="reg-password" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Hasło</label>
			<input id="reg-password" type="password" bind:value={password} required minlength="6"
				class="w-full px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 focus:outline-none focus:ring-2 focus:ring-blue-500" />
		</div>

		{#if error}
			<div class="text-red-500 text-sm">{error}</div>
		{/if}

		<button type="submit" disabled={loading}
			class="w-full px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition disabled:opacity-50">
			{loading ? '⏳ Rejestracja...' : 'Zarejestruj'}
		</button>
	</form>

	<p class="mt-4 text-sm text-center text-gray-600 dark:text-gray-400">
		Masz już konto? <a href="/login" class="text-blue-600 hover:underline">Zaloguj się</a>
	</p>
</div>
