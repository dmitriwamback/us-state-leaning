<script>
    import { onMount } from 'svelte';
    let moduleInstance;
 
    let demVotes = $state(0);
    let repVotes = $state(0);
    let tossUpVotes = $state(0);
    let noDataVotes = $state(0);
    let loading = $state(true);
    let error = $state(null);
    let demStates = $state([]);
    let repStates = $state([]);
    let tossUpStates = $state([]);
    let noDataStates = $state([]);

    const ELECTORAL_VOTES = {
        AL: 9,  AK: 3,  AZ: 11, AR: 6,
        CA: 54, CO: 10, CT: 7,  DE: 3,
        FL: 30, GA: 16, HI: 4,  ID: 4,
        IL: 19, IN: 11, IA: 6,  KS: 6,
        KY: 8,  LA: 8,  ME: 4,  MD: 10,
        MA: 11, MI: 15, MN: 10, MS: 6,
        MO: 10, MT: 4,  NE: 5,  NV: 6,
        NH: 4,  NJ: 14, NM: 5,  NY: 28,
        NC: 16, ND: 3,  OH: 17, OK: 7,
        OR: 8,  PA: 19, RI: 4,  SC: 9,
        SD: 3,  TN: 11, TX: 40, UT: 6,
        VT: 3,  VA: 13, WA: 12, WV: 4,
        WI: 10, WY: 3,  DC: 3,
    };

    const STATE_NAMES = {
        AL: "Alabama",          AK: "Alaska",       AZ: "Arizona",      AR: "Arkansas",
        CA: "California",       CO: "Colorado",     CT: "Connecticut",  DE: "Delaware",
        FL: "Florida",          GA: "Georgia",      HI: "Hawaii",       ID: "Idaho",
        IL: "Illinois",         IN: "Indiana",      IA: "Iowa",         KS: "Kansas",
        KY: "Kentucky",         LA: "Louisiana",    ME: "Maine",        MD: "Maryland",
        MA: "Massachusetts",    MI: "Michigan",     MN: "Minnesota",    MS: "Mississippi",
        MO: "Missouri",         MT: "Montana",      NE: "Nebraska",     NV: "Nevada",
        NH: "New Hampshire",    NJ: "New Jersey",   NM: "New Mexico",   NY: "New York",
        NC: "North Carolina",   ND: "North Dakota", OH: "Ohio",         OK: "Oklahoma",
        OR: "Oregon",           PA: "Pennsylvania", RI: "Rhode Island", SC: "South Carolina",
        SD: "South Dakota",     TN: "Tennessee",    TX: "Texas",        UT: "Utah",
        VT: "Vermont",          VA: "Virginia",     WA: "Washington",   WV: "West Virginia",
        WI: "Wisconsin",        WY: "Wyoming",      DC: "Washington DC",
    };

    let setViewportSize
    let setCameraOffset

    let isMouseDown = false;
    let lastxlocation = 0, lastylocation = 0;
    let canvas;
    let zoom = 1;

    onMount(async () => {
        canvas = document.getElementById("webgl");

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

        setCameraOffset = moduleInstance.cwrap('setCameraOffset', null, ['number', 'number'])

        const state = ''
        
        try {
            const res = await fetch('http://localhost:8080/api/states');
            const data = await res.json();

            setState(state, data.lean, data.confidence);
        } 
        catch (err) {
            console.log('Failed to fetch state predictions:' + err);
        }

        try {
            const res = await fetch('http://localhost:8080/api/cached');
            const data = await res.json();

            for (const [abbr, verdict] of Object.entries(data)) {
                const lean = verdict.lean == 'Toss-up' ? verdict.cook_pvi.party : verdict.lean;
                setState(abbr, lean, Math.min(verdict.cook_pvi.percentage_points/10.0, 1));
            }

            for (const [abbr, ev] of Object.entries(ELECTORAL_VOTES)) {
                const verdict = data[abbr];
                const lean = verdict.lean == 'Toss-up' ? verdict.cook_pvi.party : verdict.lean;
                const entry = { abbr, name: STATE_NAMES[abbr], ev };

                if (!verdict) {
                    noDataVotes += ev;
                    noDataStates.push(entry);
                    continue;
                }

                if (lean === 'D') {
                    demVotes += ev;
                    demStates.push({ ...entry, confidence: verdict.confidence, current_margin: verdict.current_margin });
                } 
                else if (lean === 'R') {
                    repVotes += ev;
                    repStates.push({ ...entry, confidence: verdict.confidence, current_margin: verdict.current_margin });
                } 
                else {
                    tossUpVotes += ev;
                    tossUpStates.push({ ...entry, confidence: verdict.confidence, current_margin: verdict.current_margin });
                }
            }

            demStates = demStates;
            repStates = repStates;
            tossUpStates = tossUpStates;
            noDataStates = noDataStates;
        } 
        catch (err) {
            error = err.message;
        } 
        finally {
            loading = false;
            console.log(loading);
            console.log(error);
        }

        requestAnimationFrame(loop)
    });

    function formatMargin(margin) {
        if (!margin || margin.party === 'EVEN' || margin.percentage_points === 0) {
            return 'EVEN';
        }
        const points = Number.isInteger(margin.percentage_points)
            ? margin.percentage_points
            : margin.percentage_points.toFixed(1);
        return `${margin.party}+${points}`;
    }

    function loop() {
        window.onmousedown = () => isMouseDown = true;
        window.onmouseup = () => isMouseDown = false;

        window.onmousemove = (e) => {
        if (e.pageY > 1000) return;

        const sensitivity = (30.5 * canvas.clientWidth) / 1920.0;
        const xlocation = (e.pageY / canvas.clientWidth - 0.5) * sensitivity / zoom;
        const ylocation = (e.pageX / canvas.clientWidth - 0.5) * sensitivity / zoom;

        console.log(xlocation)
        console.log(ylocation)

        if (isMouseDown) {
            setCameraOffset(xlocation - lastxlocation, ylocation - lastylocation)
        }

        lastxlocation = xlocation;
        lastylocation = ylocation;
    };
    }

</script>

<canvas id="webgl"></canvas>
<div id="content">

    {#if loading}
        <p class="status">Loading current state leanings...</p>
    {:else if error}
        <p class="status error">Failed to load predictions: {error}</p>
    {:else}
        <div class="summary">
            <div class="party dem">
                <span class="label">Democrats</span>
                <span class="votes">{demVotes}</span>
            </div>
            <div class="party rep">
                <span class="label">Republicans</span>
                <span class="votes">{repVotes}</span>
            </div>
            <div class="party tossup">
                <span class="label">Toss-up</span>
                <span class="votes">{tossUpVotes}</span>
            </div>
            {#if noDataVotes > 0}
                <div class="party nodata">
                    <span class="label">No data yet</span>
                    <span class="votes">{noDataVotes}</span>
                </div>
            {/if}
        </div>
        <p class="note">270 electoral votes needed to win</p>
        <div class="state-lists">
            {#if demStates.length > 0}
                <div class="state-group">
                    <h3 class="dem-heading">Democrats ({demStates.length})</h3>
                    <ul>
                        {#each demStates as s}
                            <li>
                                <div class="state-row">
                                    <span class="state-name">{s.name}</span>
                                    <span class="ev">{s.ev} EV</span>
                                </div>
                                <div class="margin">{formatMargin(s.current_margin)}</div>
                            </li>
                        {/each}
                    </ul>
                </div>
            {/if}

            {#if repStates.length > 0}
                <div class="state-group">
                    <h3 class="rep-heading">Republicans ({repStates.length})</h3>
                    <ul>
                        {#each repStates as s}
                            <li>
                                <div class="state-row">
                                    <span class="state-name">{s.name}</span>
                                    <span class="ev">{s.ev} EV</span>
                                </div>
                                <div class="margin">{formatMargin(s.current_margin)}</div>
                            </li>
                        {/each}
                    </ul>
                </div>
            {/if}

            {#if tossUpStates.length > 0}
                <div class="state-group">
                    <h3 class="tossup-heading">Toss-up ({tossUpStates.length})</h3>
                    <ul>
                        {#each tossUpStates as s}
                            <li>
                                <div class="state-row">
                                    <span class="state-name">{s.name}</span>
                                    <span class="ev">{s.ev} EV</span>
                                </div>
                                <div class="margin">{formatMargin(s.current_margin)}</div>
                            </li>
                        {/each}
                    </ul>
                </div>
            {/if}

            {#if noDataStates.length > 0}
                <div class="state-group">
                    <h3 class="nodata-heading">No data yet ({noDataStates.length})</h3>
                    <ul>
                        {#each noDataStates as s}
                            <li>{s.name} <span class="ev">{s.ev} EV</span></li>
                        {/each}
                    </ul>
                </div>
            {/if}
        </div>
    {/if}
</div>

<style>
    :global(html), :global(body) {
        padding: 0;
        margin: 0;
        width: 100%;
        height: 100%;
        background-color: rgb(20, 30, 36);
    }
    #webgl {
        display: block;
        width: 100vw;
        height: 100vh;
    }
    #content {
        font-family: system-ui, sans-serif;
        color: white;
        padding: 1rem;
        padding-top: 2.5rem;
        justify-items: center;
        text-align: center;
    }
 
    .status {
        opacity: 0.7;
        font-size: 0.9rem;
    }
 
    .status.error {
        color: #ff8080;
    }
 
    .summary {
        display: flex;
        gap: 1.5rem;
        flex-wrap: wrap;
    }
 
    .party {
        display: flex;
        flex-direction: column;
        align-items: center;
        min-width: 100px;
    }
 
    .party .label {
        font-size: 1.15rem;
        opacity: 0.7;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
 
    .party .votes {
        font-size: 3.8rem;
        font-weight: 700;
    }
 
    .dem .votes { color: #2b59d9; }
    .rep .votes { color: #d92b2b; }
    .tossup .votes { color: #a6a6a6; }
    .nodata .votes { color: #4a4a55; }
 
    .note {
        margin-top: 0.5rem;
        font-size: 1.15rem;
        opacity: 0.5;
    }

    .state-lists {
        display: flex;
        gap: 2rem;
        flex-wrap: wrap;
        justify-content: center;
        margin-top: 1.5rem;
        text-align: left;
    }

    .state-group {
        min-width: 180px;
    }

    .state-group h3 {
        font-size: 0.9rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        margin-bottom: 0.4rem;
    }

    .dem-heading { color: #2b59d9; }
    .rep-heading { color: #d92b2b; }
    .tossup-heading { color: #a6a6a6; }
    .nodata-heading { color: #4a4a55; }

    .state-group ul {
        list-style: none;
        padding: 0;
        margin: 0;
        font-size: 0.85rem;
        opacity: 0.85;
    }

    .state-group li {
        display: flex;
        justify-content: space-between;
        padding: 0.15rem 0;
    }

    .state-group .ev {
        opacity: 0.6;
        margin-left: 0.5rem;
    }

    .state-group li {
        display: flex;
        flex-direction: column;
        padding: 0.3rem 0;
    }

    .state-row {
        display: flex;
        justify-content: space-between;
    }

    .margin {
        font-size: 0.75rem;
        opacity: 0.55;
        margin-top: 0.1rem;
    }
</style>