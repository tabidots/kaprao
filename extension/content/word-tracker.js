// word-tracker.js
import { HighlightOverlay } from './highlighter.js';

function graphemeIndexToCharOffset(graphemes, gIndex) {
    gIndex = Math.min(gIndex, graphemes.length); // HARD SAFETY

    let n = 0;
    for (let i = 0; i < gIndex; i++) {
        const g = graphemes[i];
        if (!g) {
            console.warn("Undefined grapheme", i, graphemes);
            continue;
        }
        n += g.length;
    }
    return n;
}

export class WordTracker {
    constructor(popupManager) {
        this.popupManager = popupManager;
        this.highlightOverlay = new HighlightOverlay();
        this.enabled = true;

        // this.scanner = new ThaiPrefixScanner(getData());
        this.segmentCache = new WeakMap();

        this.currentCapture = null; // Cache current word bounds
        this.cursorRange = document.createRange(); // Reusable range for cursor position checks
        this.lastMouseEvent = null;
        this.lastMouseMoveTime = 0;

        this.handleMouseMove = this.handleMouseMove.bind(this);
        this.handleMouseLeave = this.handleMouseLeave.bind(this);
    }

    start() {
        document.addEventListener('mousemove', this.handleMouseMove);
        document.addEventListener('mouseleave', this.handleMouseLeave);
        this.enabled = true;
    }

    stop() {
        document.removeEventListener('mousemove', this.handleMouseMove);
        document.removeEventListener('mouseleave', this.handleMouseLeave);
        this.enabled = false;
        this.cleanup();
    }

    isCursorOverText(node, offset, x, y) {
        this.cursorRange.setStart(node, offset);
        this.cursorRange.setEnd(node, offset);
        
        const rects = this.cursorRange.getClientRects();
        // Single-rect requirement eliminates cases where a text node
        // spans multiple lines
        if (!rects.length || rects.length > 1) return false;

        const rect = rects[0];
        const padding = 25;
        if (x >= rect.left - padding &&
            x <= rect.right + padding &&
            y >= rect.top - padding &&
            y <= rect.bottom + padding) {
            return true;
        }

        return false;
    }

    async handleMouseMove(e) {
        // if (!this.enabled || this.isThrottled()) return;
        if (!this.enabled ) return;

        this.lastMouseEvent = e;
        this.popupManager.position(e.clientX, e.clientY);

        const ele = document.elementFromPoint(e.clientX, e.clientY);
        const range = document.caretRangeFromPoint(e.clientX, e.clientY);

        if (["TEXTAREA", "INPUT", "SELECT", "HTML", "BODY"].includes(
            ele?.tagName ?? "UNDEFINED_TAG") ||
            !range || range.startContainer.nodeType !== Node.TEXT_NODE) {
            this.cleanup();
            return;
        }

        const node = range.startContainer;
        const offset = range.startOffset;
        const text = node.data;

        if (!this.isCursorOverText(node, offset, e.clientX, e.clientY)) {
            this.cleanup();
            return;
        }

        // Only handle strings with Thai
        if (!/[ก-๙]/.test(text)) {
            this.cleanup();
            return;
        }

        // Check if we're still within the same word bounds
        // Compare by text content AND bounds, not DOM node reference
        if (this.currentCapture &&
            this.currentCapture.text === text &&  // ← Compare text instead of node
            offset >= this.currentCapture.startChar &&
            offset < this.currentCapture.endChar) {
            // Still in same word, no need to recompute
            return;
        }

        const response = await chrome.runtime.sendMessage({
            action: 'kapraoSegment',
            text: text,
            offset: offset
        });
        console.log('📥 RECEIVED:', response);

        const result = response?.result;
        
        if (!result) {
            this.highlightOverlay.clearAll();
            this.cleanup();
            return;
        }

        const { match } = result

        const startGi = match.start;
        const surface = match.surface;

        const startChar = graphemeIndexToCharOffset(result.graphemes, startGi);
        const endChar = graphemeIndexToCharOffset(
            result.graphemes,
            startGi + match.length
        );

        this.currentCapture = {
            text: text, 
            node: node,
            startChar,
            endChar,
            entries: result.entries
        };
        this.currentWord = node
        this.highlightOverlay.highlightWord(node, startChar, endChar);
        this.popupManager.show(result);
    }

    handleMouseLeave() {
        this.cleanup();
    }

    cleanup() {
        this.highlightOverlay.clearAll();
        this.popupManager.hide();
        this.currentCapture = null;
    }
}