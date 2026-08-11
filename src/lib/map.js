import createMapModule from './wasm/main.mjs'

let modulePromise = null;
export function getModule() {
    if (!modulePromise) modulePromise = createMapModule()
    return modulePromise;
}