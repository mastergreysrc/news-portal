<script lang="ts">
	let { tier = 0 }: { tier: number } = $props();
	const icons = ['🔥', '🔥', '🔥', '🔥🔥', '🔥🔥🔥'];
	const colors = ['text-gray-400', 'text-orange-500', 'text-red-500', 'text-rose-600', 'text-purple-600'];
</script>

<span class="{colors[tier] || colors[0]} font-bold text-lg">{icons[tier] || icons[0]}</span>
