async function loadGzipJson(url) {
    const response = await fetch(url);
    const blob = await response.blob();
    const ds = new DecompressionStream('gzip');
    const decompressedStream = blob.stream().pipeThrough(ds);
    const text = await new Response(decompressedStream).text();
    return JSON.parse(text);
}

const DATA_VERSION = 'v1';

const data = {
    thaiEn: [],
    index: new Map(),
    maxWordLength: 0
};
let loaded = false;

export async function initializeData() {
    if (loaded) return;
    loaded = true;

    const dataUrl = chrome.runtime.getURL(`data/thai_en.json.gz?v=${DATA_VERSION}`);
    data.thaiEn = await loadGzipJson(dataUrl);

    data.thaiEn.forEach((entry, entryIndex) => {
        for (const surface of [entry.thai, ...entry.variants]) {
            
            data.maxWordLength = Math.max(data.maxWordLength, surface.length);

            if (!data.index.has(surface)) {
                data.index.set(surface, []);
            }

            data.index.get(surface).push({
                index: entryIndex,
                isVariant: surface !== entry.thai
            });

        }
    });

}

export function getData() {
    return Object.freeze({
        thaiEn: data.thaiEn,
        index: data.index,
        maxWordLength: data.maxWordLength
    });
}