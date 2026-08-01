<script>
    import { onMount } from 'svelte';
    let result = "Loading...";

    onMount(async () => {
        const url = '/main.mjs';
		const createModule = (await import(/* @vite-ignore */ url)).default;
		await createModule();
    });
</script>

<canvas id="webgl"></canvas>

<style>
    :global(html), :global(body) {
        padding: 0;
        margin: 0;
        width: 100%;
        height: 100%;
        overflow: hidden; /* prevent scrollbars from canvas edge rounding */
    }
    #webgl {
        display: block; /* kills the inline-element bottom gutter gap */
        width: 100vw;
        height: 100vh;
    }
</style>