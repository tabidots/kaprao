import { WordTracker } from './word-tracker.js';
import { PopupManager } from './popup-manager.js';
import { SettingsManager } from './settings.js';

function registerHandlebarsHelpers() {
    Handlebars.registerHelper('join', function (array, separator) {
        return array ? array.join(separator) : '';
    });

    Handlebars.registerHelper('eq', function (a, b) {
        return a === b;
    });

    Handlebars.registerHelper('gt', (a, b) => a > b);
    Handlebars.registerHelper('lte', (a, b) => a <= b);
    Handlebars.registerHelper('and', (a, b) => a && b);

    Handlebars.registerPartial(
        "entryBlock",
        Handlebars.templates.entryBlock
    );

    Handlebars.registerHelper('joinSyllables', function (roman) {
        roman = roman.replace(/([kpt])•h/g, '$1~h');
        roman = roman.replace(/([^ptks])•ng/g, '$1~ng');
        roman = roman.replace(/ng•(?![ptkslmnhrwyjc]g?)/g, 'ng~');
        roman = roman.replace(/•/g, '');
        roman = roman.replace(/~/g, '•');
        roman = roman.normalize('NFC');
        return roman;
    });

    Handlebars.registerHelper('spanifyThai', function (text) {
        text = text.replace(/</g, "&lt;");  // keep text like <from Wiktionary>
        text = text.replace(/>/g, "&gt;");
        text = text.replace(/\[([ก-๙ ]+?)\s/g, '<span lang="th">$1</span> ');   
        return text; 
    })
}

let settingsManager;
let popupManager;
let wordTracker;

async function init() {
    try {
        settingsManager = new SettingsManager();
        await settingsManager.load();

        registerHandlebarsHelpers();

        popupManager = new PopupManager(settingsManager);
        await popupManager.init();

        wordTracker = new WordTracker(popupManager);

        // Check initial state
        chrome.runtime.sendMessage({ action: 'getKapraoState' }, (response) => {
            if (response?.enabled === true) {
                wordTracker.start();
            }
        });

    } catch (error) {
        console.error('Kaprao initialization error:', error);
    }
}

chrome.runtime.onMessage.addListener((message) => {
    if (message.action === 'enableKaprao') {
        if (message.enabled) {
            wordTracker.start();
        } else {
            wordTracker.stop();
        }
        console.log('Kaprao extension', message.enabled ? 'enabled' : 'disabled');
    } else if (message.action === 'kapraoSettingsChanged') {
        // Settings manager already handles this via onChanged listener
        // Just update the settings
        settingsManager.settings = message.settings;
        settingsManager.notifyListeners();
    } else if (message.action === 'speakCurrent') {
        const audioElement = popupManager.popup.querySelector("#shortcut-hint");
        wordTracker.highlightOverlay.speakCurrent(audioElement);
    } else if (message.action === 'persistPopup') {
        popupManager.togglePersist();
        if (popupManager.persisted) {
            wordTracker.pause();
        } else {
            wordTracker.start();
        }
    }

});

init();