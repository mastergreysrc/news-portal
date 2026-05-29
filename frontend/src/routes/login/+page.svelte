<script lang="ts">
	import { login } from '$lib/api';
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
			const res = await login(username, password);
			$token = res.access_token;
			goto('/');
		} catch (err) {
			error = err instanceof Error ? err.message : 'Błąd logowania';
		}
		loading = false;
	}
</script>

<div class="max-w-sm mx-auto">
	<h1 class="text-2xl font-bold mb-6 text-gray-900 dark:text-gray-100">🔐 Zaloguj się</h1>

	<form onsubmit={handleSubmit} class="space-y-4">
		<div>
			<label for="login-username" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Nazwa użytkownika</label>
			<input id="login-username" type="text" bind:value={username} required
				class="w-full px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 focus:outline-none focus:ring-2 focus:ring-blue-500" />
		</div>
		<div>
			<label for="login-password" class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Hasło</label>
			<input id="login-password" type="password" bind:value={password} required
				class="w-full px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-800 focus:outline-none focus:ring-2 focus:ring-blue-500" />
		</div>

		{#if error}
			<div class="text-red-500 text-sm">{error}</div>
		{/if}

		<button type="submit" disabled={loading}
			class="w-full px-4 py-2 bg-blue-600 text-white rounded-lg hover:bg-blue-700 transition disabled:opacity-50">
			{loading ? '⏳ Logowanie...' : 'Zaloguj'}
		</button>
	</form>

	<p class="mt-4 text-sm text-center text-gray-600 dark:text-gray-400">
		Nie masz konta? <a href="/register" class="text-blue-600 hover:underline">Zarejestruj się</a>
	</p>
</div>
