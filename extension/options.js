document.addEventListener('DOMContentLoaded', async () => {
    refreshOptions();

    // Also refresh when tab becomes visible
    document.addEventListener('visibilitychange', () => {
        if (!document.hidden) {
            refreshOptions();
        }
    });

    document.getElementById('open-shortcuts').addEventListener('click', (e) => {
        e.preventDefault();
        chrome.tabs.create({ url: 'chrome://extensions/shortcuts' });
    });

    await displayCurrentShortcuts();
});

function refreshOptions() {
    chrome.storage.sync.get({
        theme: 'system',
        font: 'loopless'
    }, (items) => {
        // Update UI even if values didn't change
        document.getElementById('theme').value = items.theme;
        document.getElementById('font').value = items.font;
        console.log('Options refreshed:', items);
    });
}

// Save on change
function saveSettings() {
    const settings = {
        theme: document.getElementById('theme').value,
        font: document.getElementById('font').value
    };

    chrome.storage.sync.set(settings, () => {
        // Show saved indicator
        const indicator = document.getElementById('saved');
        indicator.classList.add('show');
        setTimeout(() => indicator.classList.remove('show'), 2000);

        // Notify all tabs to update
        chrome.tabs.query({}, (tabs) => {
            tabs.forEach(tab => {
                chrome.tabs.sendMessage(tab.id, {
                    action: 'kapraoSettingsChanged',
                    settings: settings
                }).catch(() => { }); // Ignore errors for tabs without content script
            });
        });
    });
}

document.getElementById('theme').addEventListener('change', saveSettings);
document.getElementById('font').addEventListener('change', saveSettings);

async function displayCurrentShortcuts() {
    try {
        const commands = await chrome.commands.getAll();

        const activationShortcut = commands.find(command => command.name === '_execute_action')?.shortcut;
        document.getElementById('activation-shortcut').textContent = activationShortcut || 'Not set';

        const audioShortcut = commands.find(command => command.description.includes('Speak'))?.shortcut;
        document.getElementById('speak-shortcut').textContent = audioShortcut || 'Not set';

        const fontShortcut = commands.find(command => command.description.includes('font'))?.shortcut;
        document.getElementById('font-shortcut').textContent = fontShortcut || 'Not set';

        const persistShortcut = commands.find(command => command.description.includes('Keep'))?.shortcut;
        document.getElementById('persist-shortcut').textContent = persistShortcut || 'Not set';

    } catch (error) {
        console.error('Error fetching shortcuts:', error);
    }
}