# US Election Map Predictor
<p>Based on data on recent polling, demographics, and previous elections, this 3D-WebGL based app will demonstrate the current leanings of each state.</p>

## Disclaimer: This app does not determine which state will vote for which party. This app only demonstrates the current leaning of each state.

### Technologies:

<ul>
    <li>C++, Emscripten and Assimp for WebGL (To visualize a 3D United States map, with thickness of states representing the electoral votes).</li>
    <li>Python Flask server for prediction (takes all demographic, polling, and news data to make an assumption of how states will vote).</li>
    <li>Svelte and JavaScript for the front end.</li>
</ul>