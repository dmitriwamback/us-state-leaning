# US State Leaning
<p>Based on data on recent polling, and previous elections, this 3D-WebGL based app will demonstrate the current leanings of each state.</p>

## Disclaimer: This app does not determine which state will vote for which party. This app only demonstrates the current leaning of each state.

<p>A real issue is that sometimes the AI model hallucinates, especially for competitive states and swing states such as Arizona, Michigan, Nevada, Pennsylvania, and Wisconsin. (The AI generally switches between Toss-up, Democratic, or Republican for these states a lot).</p>

<p>Additionally, a few noticeable problems I witnessed was Nebraska classified as 'Toss-up' despite being a strong Republican state overall. However, the AI does a good job at classifying other strong/historically Democratic (such as California or Vermont) and Republican states (such as West Virginia or Wyoming) well.</p>

<p>Also, the program classifies Toss-up states depending on the initial leaning in the predictor/cache files.</p>

### How toss-ups are calculated:

<ul>
    <li>If the lean is classified as toss-up, then the program looks at the net_margin.</li>
    <li>If the net_margin is positive, then the state is labeled Democratic and negative for Republican.</li>
    <li>If the designated cook_pvi has the same party as the net_margin, then the program uses the percentage points in the cook_pvi instead of the calculated net margin.</li>
    <li>Otherwise, the program uses the net_margin for the percentage points.</li>
    <li>Finally, assuming we use net_margin as the percentage points, if the abs(net_margin) <= 1, then the state is classified as 'toss-up'.</li>
    <li>*The data comes from each of the dedicated state information from predictor/cache/[Abbr].json</li>
</ul>

### Technologies:

<ul>
    <li>C++ and Emscripten for WebGL (To visualize a 3D United States map, with thickness of states representing the electoral votes).</li>
    <li>Python Flask server for prediction (takes all demographic, polling, and news data to make an assumption of how states will vote).</li>
    <li>Perplexity Sonar Pro Model to scrape the web for relevant data.</li>
    <li>Svelte and JavaScript for the front end.</li>
</ul>

### Data compiled from Gemini 3.5 Flash (as of August 2nd 2026)
<p></p>
<img width="2230" height="1148" alt="Image" src="https://github.com/user-attachments/assets/8f2bd563-6da4-4bf3-9ce3-c9a6124578ee" />

### Data compiled from Sonar Pro (as of August 3rd 2026)
<img width="2240" height="1152" alt="Image" src="https://github.com/user-attachments/assets/043eaaeb-eead-4dce-b3f6-6429cad666db" />

### Data as of August 12th 2026
<img width="1316" height="878" alt="Image" src="https://github.com/user-attachments/assets/80890294-b4fa-4db2-af70-08058401344e" />

### Data as of August 18th 2026
<img width="1288" height="845" alt="Image" src="https://github.com/user-attachments/assets/ddac4644-4be0-430f-859e-8c8c971a99de" />

### Data as of August 19th 2026 (with a few modifications to the compute_lean.py and predictor.py)
### (With the addition of Maine's 1st and 2nd and Nebraska's 1st, 2nd, and 3rd congressional districts)

<img width="1643" height="1046" alt="Image" src="https://github.com/user-attachments/assets/8fa2482e-58be-4976-970b-52c4f78e3414" />

## How to run

<ul>
    <li>1. <code>python app.py</code> in the predictor directory.</li>
    <li>2. <code>npm run dev</code> in the repo directory.</li>
</ul>