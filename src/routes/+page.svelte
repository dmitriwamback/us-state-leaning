<script>
    import { onMount } from 'svelte';
    let moduleInstance;

    let setViewportSize

    onMount(async () => {
        const canvas = document.getElementById("webgl");

        const resize = () => {
            const dpr = window.devicePixelRatio || 1;

            canvas.width = window.innerWidth * dpr;
            canvas.height = window.innerHeight * dpr;

            console.log(window.innerWidth);
            console.log(window.innerHeight);
            if (setViewportSize) {
                setViewportSize(canvas.width, canvas.height);
            }
        };

        resize();
        window.addEventListener("resize", resize);

        const url = '/main.mjs';
        const createModule = (await import(/* @vite-ignore */ url)).default;

        moduleInstance = await createModule();
        const setState = moduleInstance.cwrap('setState', null, ['string', 'string', 'number']);
        
        setViewportSize = moduleInstance.cwrap('setViewportSize', null, ['number', 'number']);
        setViewportSize(canvas.width, canvas.height);


        const state = 'NC'
        
        try {
            const res = await fetch('http://localhost:8080/api/state/'+state);
            const data = await res.json();

            setState(state, data.lean, data.confidence);
        } catch (err) {
            alert('Failed to fetch state predictions:' + err);
        }
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