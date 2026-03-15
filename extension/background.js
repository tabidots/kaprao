// background.js
import { ThaiPrefixScanner } from './segmenter.js';

// Track enabled state per tab
const tabStates = new Map();

// Persist tab states to storage
async function getTabState(tabId) {
    const result = await chrome.storage.local.get(`kaprao_tab_${tabId}`);
    return result[`kaprao_tab_${tabId}`] ?? false; // Default disabled
}

async function setTabState(tabId, enabled) {
    await chrome.storage.local.set({ [`kaprao_tab_${tabId}`]: enabled });
}

async function deleteTabState(tabId) {
    await chrome.storage.local.remove(`kaprao_tab_${tabId}`);
}

// Initialize tab state on extension install
chrome.runtime.onInstalled.addListener(() => {
    console.log('Extension installed/updated');
});

// When content script is injected, set default icon
chrome.tabs.onUpdated.addListener((tabId, changeInfo) => {
    if (changeInfo.status === 'complete') {
        // Set default state if not already set
        if (!tabStates.has(tabId)) {
            tabStates.set(tabId, true); // Default to enabled
            updateIcon(tabId);
        }
    }
});

// When tab is activated, update icon
chrome.tabs.onActivated.addListener((activeInfo) => {
    updateIcon(activeInfo.tabId);
});

// Listen for clicks on the extension icon
chrome.action.onClicked.addListener(async (tab) => {
    const currentState = await getTabState(tab.id);
    const newState = !currentState;

    await setTabState(tab.id, newState);
    updateIcon(tab.id);

    chrome.tabs.sendMessage(tab.id, {
        action: 'enableKaprao',
        enabled: newState
    }).catch(() => { });
});

// Clean up when tab is closed
chrome.tabs.onRemoved.addListener((tabId) => {
    deleteTabState(tabId);
});

async function updateIcon(tabId) {
    try {
        // Verify tab exists first
        await chrome.tabs.get(tabId);

        const enabled = await getTabState(tabId);

        await chrome.action.setIcon({
            tabId: tabId,
            path: {
                "16": enabled ? "img/icon-16.png" : "img/icon-16-off.png",
                "48": enabled ? "img/icon-48.png" : "img/icon-48-off.png",
                "128": enabled ? "img/icon-128.png" : "img/icon-128-off.png"
            }
        });

        await chrome.action.setTitle({
            tabId: tabId,
            title: enabled ? "Kaprao (Active)" : "Kaprao (Disabled)"
        });
    } catch (error) {
        // Tab doesn't exist, ignore
        console.log('Cannot update icon, tab does not exist:', tabId);
    }
}

/* ================
/* DATA LOADING    
/* ================ */

let scanner = null;
let loadingPromise = null;

async function ensureDictionaryLoaded() {
    // Already loaded
    if (scanner) return scanner;

    // Currently loading
    if (loadingPromise) {
        await loadingPromise;
        return scanner;
    }

    // Start loading
    loadingPromise = loadDictionary();
    await loadingPromise;
    return scanner;
}

const DATA_VERSION = 'v1';

async function loadDictionary() {
    console.log('Loading dictionary in background...');

    const url = chrome.runtime.getURL(`data/thai_en.json.gz?v=${DATA_VERSION}`);
    const response = await fetch(url);
    const blob = await response.blob();
    const ds = new DecompressionStream('gzip');
    const decompressedStream = blob.stream().pipeThrough(ds);
    const text = await new Response(decompressedStream).text();
    const parsed = JSON.parse(text);

    // Build index
    const index = new Map();
    let maxWordLength = 0;

    parsed.forEach((entry, entryIndex) => {
        for (const surface of [entry.thai, ...entry.variants]) {
            maxWordLength = Math.max(maxWordLength, surface.length);

            if (!index.has(surface)) {
                index.set(surface, []);
            }

            index.get(surface).push({
                index: entryIndex,
                isVariant: surface !== entry.thai
            });
        }
    });

    const dictionaryData = {
        thaiEn: parsed,
        index: index,
        maxWordLength: maxWordLength
    };

    scanner = new ThaiPrefixScanner(dictionaryData);
}


chrome.commands.onCommand.addListener(async (command) => {
    if (command === 'toggle-kaprao') {
        const tabs = await chrome.tabs.query({ active: true, currentWindow: true });
        if (tabs[0]) {
            const tab = tabs[0];
            const currentState = await getTabState(tab.id);
            const newState = !currentState;

            await setTabState(tab.id, newState);
            updateIcon(tab.id);

            chrome.tabs.sendMessage(tab.id, {
                action: 'enableKaprao',
                enabled: newState
            }).catch(() => { });
        }
    }

    if (command === "speak-current") {
        // Send to content script
        chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
            if (tabs[0]?.id) {
                chrome.tabs.sendMessage(tabs[0].id, {
                    action: "speakCurrent"
                }).catch(error => {
                    console.log('Content script not ready:', error.message);
                });
            }
        });
    }

    if (command === "change-font") {
        // Cycle through fonts
        const fonts = ['loopless', 'looped', 'playful', 'handwritten'];

        // Get current font setting
        const result = await chrome.storage.sync.get({ 
            theme: 'system', 
            font: 'loopless'
        });
        const currentFont = result.font;

        // Find next font
        const currentIndex = fonts.indexOf(currentFont);
        const nextIndex = (currentIndex + 1) % fonts.length;
        const nextFont = fonts[nextIndex];

        // Update settings (preserve theme!)
        const newSettings = {
            ...result,
            font: nextFont
        };

        await chrome.storage.sync.set(newSettings);

        // Notify all tabs
        chrome.tabs.query({}, (tabs) => {
            tabs.forEach(tab => {
                chrome.tabs.sendMessage(tab.id, {
                    action: 'kapraoSettingsChanged',
                    settings: newSettings
                }).catch(() => { });
            });
        });
    }

});


chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {

    if (message.action === 'getKapraoState' && sender.tab) {
        chrome.tabs.get(sender.tab.id).then(() => {
            getTabState(sender.tab.id).then(enabled => {
                sendResponse({ enabled: enabled });
                updateIcon(sender.tab.id);
            });
        }).catch(() => {
            console.log('Tab no longer exists:', sender.tab.id);
        });
        return true; // Keep channel open
    }

    if (message.type === 'get-kaprao-shortcuts') {
        chrome.commands.getAll().then(commands => {
            const shortcuts = {};
            commands.forEach(command => {
                if (command.name === 'speak-current') {
                    shortcuts.speak = command.shortcut || 'Alt+3';
                } else if (command.name === '_execute_action' || command.name === 'toggle-kaprao') {
                    shortcuts.toggle = command.shortcut || 'Alt+K';
                }
            });
            sendResponse({ success: true, shortcuts });
        }).catch(error => {
            sendResponse({ success: false, error: error.message });
        });
        return true; // Keep channel open for async response
    }

    if (message.action === 'kapraoSegment') {
        ensureDictionaryLoaded()
            .then((scanner) => {
                const result = scanner.getAt(message.text, message.offset);
                sendResponse({ result });
            })
            .catch(error => {
                console.error('❌ Error in promise chain:', error);
                sendResponse({ result: null, error: error.message });
            });

        return true; // Keep channel open
    }

    // If message not recognized, don't respond
    return false;
});