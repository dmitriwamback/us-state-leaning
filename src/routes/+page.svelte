<script>
    import { onMount } from 'svelte';
    import { getModule } from '$lib/map.js'
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
    let showData = $state(false);

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

    let demDigits = $derived(String(Math.min(demVotes, 999)).padStart(3, '0').split(''));
    let repDigits = $derived(String(Math.min(repVotes, 999)).padStart(3, '0').split(''));

    let setViewportSize
    let setCameraOffset

    let isMouseDown = false;
    let lastxlocation = 0, lastylocation = 0;
    let canvas;
    let zoom = 1;

    const strengthMultipliers = {
        'Strong': 1, 'Lean': 0.75, 'Tilt': 0.25, 'Toss-up': 0.1
    }

    onMount(async () => {
        canvas = document.getElementById("webgl");

        const resize = () => {
            const dpr = window.devicePixelRatio || 1;

            canvas.width = window.innerWidth * dpr;
            canvas.height = window.innerHeight * dpr;

            if (setViewportSize) {
                setViewportSize(canvas.width, canvas.height);
            }
        };

        resize();
        window.addEventListener("resize", resize);

        moduleInstance = await getModule();
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

            for (const [abbr, ev] of Object.entries(ELECTORAL_VOTES)) {

                const verdict = data[abbr];
                const entry = { abbr, name: STATE_NAMES[abbr], ev, sources: verdict?.sources || [] };

                if (!verdict) {
                    noDataVotes += ev;
                    noDataStates.push(entry);
                    continue;
                }

                let points = Math.round(10 * verdict.net_margin) / 10
                let lean = points > 0 ? 'D' : 'R'

                let confidence = verdict.confidence

                if (lean == verdict.cook_pvi.party && Math.abs(points) < verdict.cook_pvi.percentage_points) {
                    points = verdict.cook_pvi.percentage_points
                    if (lean == 'R') points *= -1
                    confidence = 0.9
                }

                if (Math.abs(points) < 1) lean = 'Toss-up'

                if (lean === 'D') {
                    demVotes += ev;
                    demStates.push({ ...entry, lean: 'D', confidence: confidence, current_margin: points });
                }
                else if (lean === 'R') {
                    repVotes += ev;
                    repStates.push({ ...entry, lean: 'R', confidence: confidence, current_margin: points });
                }
                else {
                    tossUpVotes += ev;
                    tossUpStates.push({ ...entry, confidence: confidence, current_margin: points });
                }
                setState(abbr, lean, Math.min(Math.abs(points)/10, 1));
            }
        }
        catch (err) {
            error = err.message;
        }
        finally {
            loading = false;
        }

        requestAnimationFrame(loop)
    });

    function formatMargin(margin) {
        if (margin == 0) return 'EVEN';
        if (margin > 0) return `D+${margin}`;
        if (margin < 0) return `R+${-margin}`;
    }

    function loop() {
        window.onmousedown = () => isMouseDown = true;
        window.onmouseup = () => isMouseDown = false;

        window.onmousemove = (e) => {
            if (e.pageY > 1000) return;

            const sensitivity = (30.5 * canvas.clientWidth) / 1920.0;
            const xlocation = (e.pageY / canvas.clientWidth - 0.5) * sensitivity / zoom;
            const ylocation = (e.pageX / canvas.clientWidth - 0.5) * sensitivity / zoom;

            if (isMouseDown) {
                setCameraOffset(xlocation - lastxlocation, ylocation - lastylocation)
            }

            lastxlocation = xlocation;
            lastylocation = ylocation;
        };
    }
</script>

<canvas id="webgl"></canvas>


<div class="dashboard">

    <!-- HEADER / FORECAST -->
    <header class="page-header">
        <div>
            <div class="eyebrow">Electoral College Forecast</div>
            <h1>Current Presidential Forecast</h1>
            <p>
                State-by-state assessment based on current polling,
                reporting, and available evidence.
            </p>
        </div>
    </header>


    <!-- FORECAST SUMMARY -->
    <section class="forecast-card">

        <div class="forecast-top">
            <div>
                <span class="forecast-label">Electoral college</span>
                <div class="forecast-number">
                    {demVotes + repVotes + tossUpVotes}
                    <span>/ 538 EV</span>
                </div>
            </div>

            <div class="win-target">
                <strong>270</strong>
                <span>EV to win</span>
            </div>
        </div>


        <!-- PARTY TOTALS -->
        <div class="party-grid">

            <div class="party-box democrat">
                <div class="party-name">
                    <span class="party-dot"></span>
                    Democrats
                </div>

                <div class="counter">
                    {#each demDigits as d}
                        <span class="counter-digit">{d}</span>
                    {/each}
                    <span class="counter-suffix">EV</span>
                </div>

                <div class="party-states">
                    {demStates.length} states
                </div>
            </div>


            <div class="party-box tossup">
                <div class="party-name">
                    <span class="party-dot"></span>
                    Toss-up
                </div>

                <div class="party-votes simple">
                    {tossUpVotes}
                    <span>EV</span>
                </div>

                <div class="party-states">
                    {tossUpStates.length} states
                </div>
            </div>


            <div class="party-box republican">
                <div class="party-name">
                    <span class="party-dot"></span>
                    Republicans
                </div>

                <div class="counter">
                    {#each repDigits as d}
                        <span class="counter-digit">{d}</span>
                    {/each}
                    <span class="counter-suffix">EV</span>
                </div>

                <div class="party-states">
                    {repStates.length} states
                </div>
            </div>

            {#if noDataVotes > 0}
                <div class="party-box nodata">
                    <div class="party-name">
                        <span class="party-dot"></span>
                        No data
                    </div>

                    <div class="party-votes simple">
                        {noDataVotes}
                        <span>EV</span>
                    </div>

                    <div class="party-states">
                        Insufficient evidence
                    </div>
                </div>
            {/if}

        </div>


        <!-- ELECTORAL BAR -->
        <div class="ev-bar">

            <div
                class="bar-dem"
                style={`width:${(demVotes / 538) * 100}%`}
            ></div>

            <div
                class="bar-tossup"
                style={`width:${(tossUpVotes / 538) * 100}%`}
            ></div>

            <div
                class="bar-rep"
                style={`width:${(repVotes / 538) * 100}%`}
            ></div>

        </div>

        <div class="bar-labels">
            <span>0</span>
            <span>270 EV</span>
            <span>538</span>
        </div>

    </section>


    <!-- TOSS UPS -->
    {#if tossUpStates.length > 0}

        <section class="section">

            <div class="section-heading">
                <div>
                    <div class="eyebrow">Most competitive</div>
                    <h2>Toss-up states</h2>
                </div>

                <div class="section-count">
                    {tossUpStates.length} states
                </div>
            </div>


            <div class="tossup-grid">

                {#each tossUpStates as state (state.abbr)}

                    {@render stateEntry(state)}

                {/each}

            </div>

        </section>

    {/if}


    <!-- STATE DATA TOGGLE -->
    <div class="data-control">

        <div>
            <div class="eyebrow">Detailed data</div>
            <h2>State-by-state breakdown</h2>
        </div>

        <button
            class:active={showData}
            class="data-toggle"
            aria-expanded={showData}
            onclick={() => (showData = !showData)}
        >
            <span>
                {showData ? 'Hide state data' : 'Show state data'}
            </span>

            <span class="arrow">
                {showData ? '↑' : '↓'}
            </span>
        </button>

    </div>


    <!-- STATE DATA -->
    {#if showData}

        <div class="state-columns">

            <!-- DEMOCRATIC -->
            <section class="state-column">

                <div class="column-heading democrat-heading">

                    <div class="heading-title">
                        <span class="heading-dot democrat-dot"></span>

                        <div>
                            <h2>Democratic</h2>
                            <span>
                                {demStates.length} states · {demVotes} EV
                            </span>
                        </div>
                    </div>

                </div>


                <div class="column-content">

                    {#each demStates as state (state.abbr)}

                        {@render stateEntry(state)}

                    {/each}


                    {#each noDataStates as state (state.abbr)}

                        <article class="state-card no-data-card">

                            <div class="state-header">

                                <div>
                                    <h3>{state.name}</h3>
                                    <span class="abbr">
                                        {state.abbr}
                                    </span>
                                </div>

                                <strong>{state.ev} EV</strong>

                            </div>

                            <div class="no-sources">
                                No data available
                            </div>

                        </article>

                    {/each}

                </div>

            </section>


            <!-- REPUBLICAN -->
            <section class="state-column">

                <div class="column-heading republican-heading">

                    <div class="heading-title">
                        <span class="heading-dot republican-dot"></span>

                        <div>
                            <h2>Republican</h2>
                            <span>
                                {repStates.length} states · {repVotes} EV
                            </span>
                        </div>
                    </div>

                </div>


                <div class="column-content">

                    {#each repStates as state (state.abbr)}

                        {@render stateEntry(state)}

                    {/each}

                </div>

            </section>

        </div>

    {/if}

</div>


<!-- STATE CARD SNIPPET -->
{#snippet stateEntry(state)}

    <article class="state-card">

        <div class="state-header">

            <div class="state-name">

                <h3>{state.name}</h3>

                <span class="abbr">
                    {state.abbr}
                </span>

            </div>

            <strong class="state-ev">
                {state.ev} EV
            </strong>

        </div>


        <!-- STATUS -->
        <div class="state-status" data-lean={state.lean === 'D' ? 'dem' : state.lean === 'R' ? 'rep' : 'tossup'}>

            <span class="status-dot"></span>

            <span>
                {state.lean === 'D' ? 'Democrat' : state.lean === 'R' ? 'Republican' : 'Toss-up'}
                {#if state.current_margin !== undefined}
                    · {formatMargin(state.current_margin)}
                {/if}
            </span>

            {#if state.confidence != null}

                <span class="confidence">
                    {Math.round(state.confidence * 100)}% confidence
                </span>

            {/if}

        </div>


        <!-- SOURCES -->
        {#if state.sources?.length > 0}

            <div class="sources">

                <div class="sources-heading">
                    <span>Evidence</span>
                    <span>{state.sources.length} sources</span>
                </div>


                {#each state.sources as src, index (`${state.abbr}-${index}-${src.link}`)}

                    <a
                        class="source"
                        href={src.link}
                        target="_blank"
                        rel="noopener noreferrer"
                    >

                        <div class="source-title">

                            <strong>
                                {src.name}
                            </strong>

                            {#if src.verified}

                                <span
                                    class="verified"
                                    title="Verified source"
                                >
                                    ✓
                                </span>

                            {/if}

                        </div>


                        <div class="source-meta">

                            <span>
                                {src.party}
                                {src.margin != null
                                    ? ` +${src.margin}`
                                    : ''}
                            </span>

                            <span>·</span>

                            <span>
                                {src.date_range}
                            </span>

                        </div>


                        {#if src.details}

                            <p>
                                {src.details}
                            </p>

                        {/if}

                    </a>

                {/each}

            </div>

        {:else}

            <div class="no-sources">
                No sources available
            </div>

        {/if}

    </article>

{/snippet}


<style>

    @import url('https://fonts.googleapis.com/css2?family=Newsreader:ital,wght@0,500;0,600;0,700;1,500&family=IBM+Plex+Sans:wght@400;500;600;700&family=IBM+Plex+Mono:wght@500;600;700&display=swap');

    /* =========================================================
       TOKENS
       ========================================================= */

    :global(*) {
        box-sizing: border-box;
    }

    :global(body) {
        margin: 0;
        background: #0c1015;
        color: #262019;
        font-family: 'IBM Plex Sans', ui-sans-serif, system-ui, sans-serif;
    }

    #webgl {
        display: block;
        width: 100vw;
        height: 100vh;
    }


    /* =========================================================
       DASHBOARD — the "paper record" beneath the live map
       ========================================================= */

    .dashboard {
        position: relative;
        width: 100%;
        margin: 0;
        padding: 46px 0 90px;
        background: #efe7d5;
        box-shadow: 0 -1px 0 #c9a34a inset;
    }

    .dashboard > * {
        width: min(1320px, calc(100% - 48px));
        margin: 0 auto;
    }

    .dashboard::before {
        content: "";
        position: absolute;
        top: 0;
        left: 0;
        right: 0;
        height: 6px;
        background: linear-gradient(90deg, #1f3a5f 0 33%, #a9862f 33% 67%, #8c2f2a 67% 100%);
        opacity: 0.75;
    }


    /* =========================================================
       HEADER
       ========================================================= */

    .page-header {
        display: flex;
        align-items: flex-start;
        justify-content: space-between;
        gap: 30px;
        margin-bottom: 30px;
    }

    .eyebrow {
        color: #8c7a4e;
        font-family: 'IBM Plex Mono', monospace;
        font-size: 10px;
        font-weight: 600;
        letter-spacing: .14em;
        text-transform: uppercase;
    }

    .page-header h1 {
        margin: 8px 0 9px;
        font-family: 'Newsreader', serif;
        font-size: 34px;
        font-weight: 600;
        line-height: 1.08;
        letter-spacing: -.01em;
        color: #1c1811;
    }

    .page-header p {
        margin: 0;
        max-width: 620px;
        color: #6b6046;
        font-size: 14px;
        line-height: 1.55;
    }

    .header-badge {
        display: flex;
        align-items: center;
        gap: 8px;
        padding: 8px 13px;
        border: 1.5px dashed rgba(140, 47, 42, 0.5);
        border-radius: 999px;
        background: rgba(140, 47, 42, 0.06);
        color: #8c2f2a;
        font-family: 'IBM Plex Mono', monospace;
        font-size: 10px;
        font-weight: 600;
        letter-spacing: .1em;
        text-transform: uppercase;
        white-space: nowrap;
        transform: rotate(-2deg);
    }

    .live-dot {
        width: 6px;
        height: 6px;
        border-radius: 50%;
        background: #8c2f2a;
        box-shadow: 0 0 6px rgba(140, 47, 42, 0.7);
    }


    /* =========================================================
       FORECAST CARD
       ========================================================= */

    .forecast-card {
        padding: 30px 30px 26px;
        border: 1px solid rgba(28, 24, 17, 0.14);
        border-radius: 4px;
        background: #f8f3e6;
        box-shadow: 0 1px 0 rgba(28, 24, 17, 0.05);
    }

    .forecast-top {
        display: flex;
        align-items: center;
        justify-content: space-between;
        padding-bottom: 20px;
        border-bottom: 1px solid rgba(28, 24, 17, 0.12);
    }

    .forecast-label {
        display: block;
        color: #8c7a4e;
        font-family: 'IBM Plex Mono', monospace;
        font-size: 10px;
        font-weight: 600;
        letter-spacing: .12em;
        text-transform: uppercase;
    }

    .forecast-number {
        margin-top: 5px;
        font-family: 'Newsreader', serif;
        font-size: 32px;
        font-weight: 600;
        letter-spacing: -.01em;
        color: #1c1811;
    }

    .forecast-number span {
        color: #9a8f70;
        font-family: 'IBM Plex Sans', sans-serif;
        font-size: 13px;
        font-weight: 500;
    }

    .win-target {
        text-align: right;
    }

    .win-target strong {
        display: block;
        font-family: 'Newsreader', serif;
        font-size: 26px;
        font-weight: 600;
        color: #1c1811;
    }

    .win-target span {
        color: #9a8f70;
        font-family: 'IBM Plex Mono', monospace;
        font-size: 10px;
        letter-spacing: .06em;
        text-transform: uppercase;
    }


    /* =========================================================
       PARTY LEDGER ROWS
       ========================================================= */

    .party-grid {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 1px;
        margin-top: 24px;
        border: 1px solid rgba(28, 24, 17, 0.12);
        background: rgba(28, 24, 17, 0.12);
    }

    .party-box {
        padding: 18px 20px;
        background: #f8f3e6;
        border-top: 3px solid transparent;
    }

    .democrat { border-top-color: #1f3a5f; }
    .republican { border-top-color: #8c2f2a; }
    .tossup { border-top-color: #a9862f; }
    .nodata { border-top-color: #a49a80; }

    .party-name {
        display: flex;
        align-items: center;
        gap: 7px;
        color: #6b6046;
        font-family: 'IBM Plex Mono', monospace;
        font-size: 11px;
        font-weight: 600;
        letter-spacing: .04em;
        text-transform: uppercase;
    }

    .party-dot,
    .heading-dot {
        width: 6px;
        height: 6px;
        flex-shrink: 0;
        border-radius: 50%;
    }

    .democrat .party-dot,
    .democrat-dot {
        background: #1f3a5f;
    }

    .republican .party-dot,
    .republican-dot {
        background: #8c2f2a;
    }

    .tossup .party-dot {
        background: #a9862f;
    }

    .nodata .party-dot {
        background: #a49a80;
    }

    /* Signature: mechanical tally-counter digits */
    .counter {
        display: flex;
        align-items: stretch;
        gap: 2px;
        margin-top: 10px;
    }

    .counter-digit {
        display: flex;
        align-items: center;
        justify-content: center;
        width: 24px;
        height: 34px;
        border-radius: 2px;
        background: #16202b;
        box-shadow:
            inset 0 1px 0 rgba(255, 255, 255, 0.08),
            inset 0 -2px 0 rgba(0, 0, 0, 0.35);
        color: #f4efe1;
        font-family: 'IBM Plex Mono', monospace;
        font-size: 20px;
        font-weight: 600;
        font-variant-numeric: tabular-nums;
    }

    .counter-suffix {
        align-self: flex-end;
        margin-left: 6px;
        margin-bottom: 4px;
        color: #9a8f70;
        font-family: 'IBM Plex Mono', monospace;
        font-size: 10px;
        letter-spacing: .06em;
        text-transform: uppercase;
    }

    .party-votes.simple {
        margin-top: 12px;
        font-family: 'IBM Plex Mono', monospace;
        font-size: 28px;
        font-weight: 600;
        color: #3a3223;
    }

    .party-votes.simple span {
        margin-left: 3px;
        color: #9a8f70;
        font-size: 11px;
        font-weight: 500;
        text-transform: uppercase;
    }

    .party-states {
        margin-top: 8px;
        color: #9a8f70;
        font-size: 11px;
    }


    /* =========================================================
       EV BAR — ledger ruler
       ========================================================= */

    .ev-bar {
        display: flex;
        height: 7px;
        margin-top: 26px;
        overflow: hidden;
        border-radius: 999px;
        background: rgba(28, 24, 17, 0.1);
    }

    .bar-dem { background: #1f3a5f; }
    .bar-tossup { background: #a9862f; }
    .bar-rep { background: #8c2f2a; }

    .bar-labels {
        display: flex;
        justify-content: space-between;
        margin-top: 9px;
        color: #9a8f70;
        font-family: 'IBM Plex Mono', monospace;
        font-size: 10px;
        letter-spacing: .04em;
    }

    .bar-labels span:nth-child(2) {
        color: #6b6046;
        font-weight: 600;
    }


    /* =========================================================
       SECTIONS
       ========================================================= */

    .section {
        margin-top: 46px;
    }

    .section-heading,
    .data-control {
        display: flex;
        align-items: flex-end;
        justify-content: space-between;
        gap: 20px;
        margin-bottom: 16px;
    }

    .section-heading h2,
    .data-control h2 {
        margin: 6px 0 0;
        font-family: 'Newsreader', serif;
        font-size: 21px;
        font-weight: 600;
        color: #1c1811;
    }

    .section-count {
        color: #9a8f70;
        font-family: 'IBM Plex Mono', monospace;
        font-size: 11px;
    }


    /* =========================================================
       TOSSUP GRID
       ========================================================= */

    .tossup-grid {
        display: grid;
        grid-template-columns: repeat(3, 1fr);
        gap: 12px;
    }


    /* =========================================================
       STATE DATA TOGGLE
       ========================================================= */

    .data-control {
        margin-top: 50px;
        padding-top: 28px;
        border-top: 1px solid rgba(28, 24, 17, 0.12);
    }

    .data-toggle {
        display: flex;
        align-items: center;
        gap: 10px;
        padding: 9px 14px;
        border: 1px solid rgba(28, 24, 17, 0.22);
        border-radius: 3px;
        background: #f8f3e6;
        color: #3a3223;
        cursor: pointer;
        font: inherit;
        font-family: 'IBM Plex Mono', monospace;
        font-size: 11px;
        font-weight: 600;
        letter-spacing: .02em;
        transition: border-color .15s ease, background .15s ease;
    }

    .data-toggle:hover,
    .data-toggle.active {
        border-color: #a9862f;
        background: #f2e9d0;
    }

    .arrow {
        color: #9a8f70;
        font-size: 13px;
    }

    .state-columns {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 16px;
    }

    .column-heading {
        padding: 15px 18px;
        border: 1px solid rgba(28, 24, 17, 0.14);
        border-radius: 3px;
        background: #f8f3e6;
    }

    .heading-title {
        display: flex;
        align-items: center;
        gap: 10px;
    }

    .heading-title h2 {
        margin: 0;
        font-family: 'Newsreader', serif;
        font-size: 16px;
        font-weight: 600;
        color: #1c1811;
    }

    .heading-title span:not(.heading-dot) {
        display: block;
        margin-top: 2px;
        color: #9a8f70;
        font-family: 'IBM Plex Mono', monospace;
        font-size: 10px;
    }

    .column-content {
        display: flex;
        flex-direction: column;
        gap: 8px;
        margin-top: 10px;
    }


    /* =========================================================
       STATE CARD
       ========================================================= */

    .state-card {
        padding: 16px 18px;
        border: 1px solid rgba(28, 24, 17, 0.14);
        border-radius: 3px;
        background: #f8f3e6;
        transition: border-color .15s ease, transform .15s ease;
    }

    .state-card:hover {
        border-color: rgba(28, 24, 17, 0.3);
        transform: translateY(-1px);
    }

    .state-header {
        display: flex;
        align-items: flex-start;
        justify-content: space-between;
        gap: 15px;
    }

    .state-name {
        display: flex;
        align-items: baseline;
        gap: 7px;
    }

    .state-name h3 {
        margin: 0;
        font-family: 'Newsreader', serif;
        font-size: 17px;
        font-weight: 600;
        color: #1c1811;
    }

    .abbr {
        color: #9a8f70;
        font-family: 'IBM Plex Mono', monospace;
        font-size: 10px;
        font-weight: 600;
        letter-spacing: .06em;
    }

    .state-ev {
        color: #6b6046;
        font-family: 'IBM Plex Mono', monospace;
        font-size: 12px;
        white-space: nowrap;
    }


    /* =========================================================
       STATUS
       ========================================================= */

    .state-status {
        display: inline-flex;
        align-items: center;
        gap: 7px;
        margin-top: 12px;
        padding: 5px 10px;
        border: 1px solid rgba(28, 24, 17, 0.14);
        border-radius: 999px;
        background: rgba(28, 24, 17, 0.03);
        color: #3a3223;
        font-family: 'IBM Plex Mono', monospace;
        font-size: 10px;
        font-weight: 600;
    }

    .status-dot {
        width: 6px;
        height: 6px;
        border-radius: 50%;
        background: #9a8f70;
    }

    .state-status[data-lean="dem"] .status-dot { background: #1f3a5f; }
    .state-status[data-lean="rep"] .status-dot { background: #8c2f2a; }
    .state-status[data-lean="tossup"] .status-dot { background: #a9862f; }

    .confidence {
        padding-left: 8px;
        margin-left: 1px;
        border-left: 1px solid rgba(28, 24, 17, 0.18);
        color: #9a8f70;
        font-weight: 500;
    }


    /* =========================================================
       SOURCES
       ========================================================= */

    .sources {
        margin-top: 16px;
        border-top: 1px solid rgba(28, 24, 17, 0.12);
    }

    .sources-heading {
        display: flex;
        justify-content: space-between;
        padding: 11px 0 5px;
        color: #9a8f70;
        font-family: 'IBM Plex Mono', monospace;
        font-size: 9px;
        font-weight: 600;
        letter-spacing: .1em;
        text-transform: uppercase;
    }

    .source {
        display: block;
        padding: 11px 0;
        border-top: 1px solid rgba(28, 24, 17, 0.08);
        color: inherit;
        text-decoration: none;
    }

    .source:hover .source-title strong {
        color: #1f3a5f;
        text-decoration: underline;
    }

    .source-title {
        display: flex;
        align-items: center;
        gap: 6px;
    }

    .source-title strong {
        color: #2a2419;
        font-size: 12px;
        font-weight: 600;
        transition: color .15s ease;
    }

    .verified {
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: 15px;
        height: 15px;
        border: 1px solid rgba(140, 47, 42, 0.4);
        border-radius: 50%;
        color: #8c2f2a;
        font-size: 9px;
        font-weight: 700;
        transform: rotate(-6deg);
    }

    .source-meta {
        display: flex;
        gap: 6px;
        margin-top: 4px;
        color: #9a8f70;
        font-family: 'IBM Plex Mono', monospace;
        font-size: 10px;
    }

    .source p {
        margin: 7px 0 0;
        color: #6b6046;
        font-size: 11.5px;
        line-height: 1.55;
    }

    .no-sources {
        margin-top: 14px;
        padding: 11px;
        border: 1px dashed rgba(28, 24, 17, 0.2);
        border-radius: 3px;
        color: #9a8f70;
        font-family: 'IBM Plex Mono', monospace;
        font-size: 11px;
        text-align: center;
    }

    .no-data-card {
        opacity: .6;
    }


    /* =========================================================
       RESPONSIVE
       ========================================================= */

    @media (max-width: 950px) {

        .tossup-grid {
            grid-template-columns: 1fr 1fr;
        }

        .state-columns {
            grid-template-columns: 1fr;
        }

    }


    @media (max-width: 650px) {

        .dashboard > * {
            width: calc(100% - 20px);
        }

        .dashboard {
            padding-top: 25px;
        }

        .page-header {
            flex-direction: column;
        }

        .header-badge {
            align-self: flex-start;
        }

        .forecast-card {
            padding: 20px;
        }

        .forecast-top {
            align-items: flex-start;
        }

        .party-grid {
            grid-template-columns: 1fr;
        }

        .tossup-grid {
            grid-template-columns: 1fr;
        }

        .data-control {
            align-items: flex-start;
            flex-direction: column;
        }

        .state-name {
            flex-direction: column;
            gap: 2px;
        }

    }

</style>