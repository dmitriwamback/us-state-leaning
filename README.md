# US State Leaning
<p>Based on data on recent polling, demographics, and previous elections, this 3D-WebGL based app will demonstrate the current leanings of each state.</p>

## Disclaimer: This app does not determine which state will vote for which party. This app only demonstrates the current leaning of each state.

### Technologies:

<ul>
    <li>C++ and Emscripten for WebGL (To visualize a 3D United States map, with thickness of states representing the electoral votes).</li>
    <li>Python Flask server for prediction (takes all demographic, polling, and news data to make an assumption of how states will vote).</li>
    <li>Google Perplexity Sonar Pro Model to scrape the web for relevant data.</li>
    <li>Svelte and JavaScript for the front end.</li>
</ul>

### Data compiled from Gemini 3.5 Flash (as of August 2nd 2026)
<img width="2230" height="1148" alt="Image" src="https://github.com/user-attachments/assets/8f2bd563-6da4-4bf3-9ce3-c9a6124578ee" />

## How to run

<ul>
    <li>1. <code>python app.py</code> in the predictor directory.</li>
    <li>2. <code>npm run dev</code> in the repo directory.</li>
</ul>