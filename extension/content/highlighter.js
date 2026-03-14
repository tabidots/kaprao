export class HighlightOverlay {
    constructor() {
        this.overlay = null;
        this.currentHighlights = [];
        this.range = document.createRange();

        this.initOverlay();
        this.watchForRemoval();
    }

    initOverlay() {
        this.overlay = document.createElement('div');
        this.overlay.id = "kaprao-overlay";
        this.overlay.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            width: 100%;
            height: 100%;
            pointer-events: none;
            z-index: 10000;
        `;
        document.body.appendChild(this.overlay);
    }

    watchForRemoval() {
        // Re-inject popup if DOM is rehydrated (Next.js, etc)
        // (Usually the highlighter is fine, compared to the popup, but JIC...)
        const observer = new MutationObserver((mutations) => {
            const overlay = document.getElementById('kaprao-overlay');

            if (!overlay) {
                this.initOverlay();
                observer.disconnect();
            }
        });

        observer.observe(document.body, {
            childList: true,
            subtree: false
        });
    }

    highlightWord(container, start, end, color = 'rgba(255, 255, 0, 0.3)') {
        this.clearAll();

        try {
            // const range = document.createRange();
            this.range.setStart(container, start);
            this.range.setEnd(container, end);

            const rects = this.range.getClientRects();

            for (const rect of rects) {
                if (rect.width === 0 || rect.height === 0) continue;

                const highlight = document.createElement('div');
                highlight.style.cssText = `
                    position: absolute;
                    left: ${rect.left}px;
                    top: ${rect.top}px;
                    width: ${rect.width}px;
                    height: ${rect.height}px;
                    background-color: ${color};
                    border-radius: 2px;
                    pointer-events: none;
                `;

                this.overlay.appendChild(highlight);
                this.currentHighlights.push(highlight);
            }
        } catch (e) {
            console.error('Error creating highlight:', e);
        }
    }

    clearAll() {
        for (const highlight of this.currentHighlights) {
            if (highlight.parentNode) {
                highlight.remove();
            }
        }
        this.currentHighlights = [];
        this.range.collapse();
    }

    destroy() {
        this.clearAll();
        if (this.overlay && this.overlay.parentNode) {
            this.overlay.remove();
        }
    }

    getThaiVoice() {
        return new Promise(resolve => {

            let voices = speechSynthesis.getVoices();
            if (voices.length) {
                resolve(this.pickThai(voices));
                return;
            }

            speechSynthesis.onvoiceschanged = () => {
                voices = speechSynthesis.getVoices();
                resolve(this.pickThai(voices));
            };
        });
    }

    pickThai(voices) {
        return voices.find(v =>
            v.lang === "th-TH" &&
            /siri|enhanced|premium/i.test(v.name)
        ) || voices.find(v => v.lang === "th-TH");
    }

    speakPromise(text) {
        speechSynthesis.cancel();
        return new Promise(async resolve => {
            const u = new SpeechSynthesisUtterance(text);
            u.lang = "th-TH";
            u.rate = 1.0;
            u.pitch = 1.0;

            const thai = await this.getThaiVoice();
            if (!thai) {
                resolve;
                return;
            }
                
            u.voice = thai;
            u.onend = resolve;
            speechSynthesis.speak(u);
        });
    }

    async speakCurrent(audioElement = null) {
        if (!this.range) return;

        const text = this.range.toString();
        audioElement?.classList.add('playing');
        await this.speakPromise(text);
        audioElement?.classList.remove('playing');
    }
}