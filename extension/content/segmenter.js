// segmenter.js

const DEPENDENT_VOWELS = 'ัาิีึืุูำะ';
const INDEPENDENT_VOWELS = 'เแโใไ';
const DIACRITICS = '์่้๊๋็ฺ';

function isValidWordStart(text, pos) {
    if (pos >= text.length) return false;

    const ch = text[pos];

    // Can't start with diacritics or dependent vowels
    if (DIACRITICS.includes(ch) || DEPENDENT_VOWELS.includes(ch)) {
        return false;
    }

    // Can't start after independent vowel
    if (pos > 0 && INDEPENDENT_VOWELS.includes(text[pos - 1])) {
        return false;
    }

    // Can't start after linking short "a" (ัะ)
    if (pos > 0 && text[pos - 1] === '\u0E31') {
        return false;
    }

    return true;
}

function isValidWordEnd(text, pos) {
    if (pos > text.length) return false;

    const remainder = text.substring(pos);
    if (remainder.length === 0) return true;

    const nextChar = remainder[0];
    const nextNextChar = remainder.length > 1 ? remainder[1] : '';

    // Can't end before dependent vowels or diacritics
    if (DEPENDENT_VOWELS.includes(nextChar) || DIACRITICS.includes(nextChar)) {
        return false;
    }

    // Can't end if next character is followed by silencer (์)
    if (nextNextChar === '\u0E4C') {
        return false;
    }

    return true;
}

function isBetter(a, b, fullSurface) {
    if (!b) return true;

    const aIsWhole = a.length === 1 && a[0].surface === fullSurface;
    const bIsWhole = b.length === 1 && b[0].surface === fullSurface;

    if (aIsWhole && !bIsWhole) return false;
    if (!aIsWhole && bIsWhole) return true;

    return a.length < b.length;
}


function canHavePOS(seg, targetPOSstart) {
    return seg.entries.some(e => e.glosses?.some(g => g.pos?.startsWith(targetPOSstart)));
}


export class ThaiPrefixScanner {
    constructor(data) {
        this.data = data;
        this.cache = new WeakMap();
        this.segCache = new WeakMap();
        this.seg = new Intl.Segmenter("th", { granularity: "grapheme" });
    }

    split(node, text) {
        if (typeof node !== "object") {
            console.error("INVALID CACHE KEY:", node);
            return;
        }
        let c = this.cache.get(node);
        if (c && c.text === text) return c.g;

        const g = [...this.seg.segment(text)].map(s => s.segment);
        this.cache.set(node, { text, g });
        return g;
    }

    scoreSegmentation(segments) {
        if (!segments || segments.length === 0) return -Infinity;

        let score = -segments.length * 1000; // Strongly prefer fewer segments

        for (let i = 0; i < segments.length; i++) {
            const seg = segments[i];

            // Length bonus: prefer longer segments within same count
            score += seg.surface.length * 5;

            // V + N pattern bonus (includes V + N. exp.)
            if (i < segments.length - 1) {
                const next = segments[i + 1];

                if (canHavePOS(seg, 'v') && canHavePOS(next, 'n')) {
                    score += 120;
                }
            }

            // Penalty: simple verb (not v. exp.) before verb expression
            if (i > 0) {
                const prev = segments[i - 1];
                if (canHavePOS(prev, 'v') && !canHavePOS(prev, 'v. exp.') && canHavePOS(seg, 'v. exp.')) {
                    score -= 80;
                }
            }
        }

        return score;
    }

    /**
     * Unified DP segmentation
     * @param {Array} g - Array of graphemes
     * @param {Object} options - Configuration options
     * @param {boolean} options.allowGaps - Allow single grapheme gaps when no match found
     * @param {boolean} options.filterCompounds - Exclude compound entries
     * @param {string} options.fullSurface - Full surface for isBetter comparison
     * @returns {Array|null} - Segmentation or null if no complete path
     */
    segmentWithDP(g, options = {}) {
        const {
            allowGaps = true,
            filterCompounds = false,
            fullSurface = null
        } = options;

        const n = g.length;
        const dp = Array(n + 1).fill(null);
        dp[n] = [];

        // Reconstruct text for validation
        const text = g.join('');

        for (let i = n - 1; i >= 0; i--) {
            // Check if this is a valid word start position
            const charPos = g.slice(0, i).join('').length;
            if (!isValidWordStart(text, charPos)) {
                // Not a valid start, skip trying to start a word here
                // But still allow gap if needed
                if (allowGaps && dp[i + 1] !== null) {
                    dp[i] = [
                        {
                            start: i,
                            length: 1,
                            surface: g[i],
                            entries: []
                        },
                        ...dp[i + 1]
                    ];
                }
                continue;
            }

            let buf = "";
            const maxLen = Math.min(this.data.maxWordLength, n - i);

            for (let len = 1; len <= maxLen; len++) {
                buf += g[i + len - 1];

                // Check if this is a valid word end position
                const endCharPos = g.slice(0, i + len).join('').length;
                if (!isValidWordEnd(text, endCharPos)) {
                    continue; // Invalid end, try next length
                }

                const hits = this.data.index.get(buf);
                if (!hits) continue;

                let validHits = hits;
                if (filterCompounds) {
                    validHits = hits.filter(h => !this.data.thaiEn[h.index].is_compound);
                    if (!validHits.length) continue;
                }

                if (dp[i + len] !== null) {
                    const candidate = [
                        {
                            start: i,
                            length: len,
                            surface: buf,
                            entries: validHits.map(h => ({
                                ...this.data.thaiEn[h.index],
                                isVariant: h.isVariant
                            }))
                        },
                        ...dp[i + len]
                    ];

                    let shouldUpdate = false;

                    if (fullSurface) {
                        shouldUpdate = isBetter(candidate, dp[i], fullSurface);
                    } else {
                        if (!dp[i]) {
                            shouldUpdate = true;
                        } else {
                            const candidateScore = this.scoreSegmentation(candidate);
                            const currentScore = this.scoreSegmentation(dp[i]);
                            shouldUpdate = candidateScore > currentScore;
                        }
                    }

                    if (shouldUpdate) {
                        dp[i] = candidate;
                    }
                }
            }

            // Allow single grapheme gaps if no valid word found
            if (!dp[i] && allowGaps && dp[i + 1] !== null) {
                dp[i] = [
                    {
                        start: i,
                        length: 1,
                        surface: g[i],
                        entries: []
                    },
                    ...dp[i + 1]
                ];
            }
        }

        return dp[0];
    }

    // Get or compute segmentation for entire text (main text segmentation)
    getSegmentation(node, text) {
        let cached = this.segCache.get(node);
        if (cached && cached.text === text) {
            return cached.segments;
        }

        const g = this.split(node, text);
        const segments = this.segmentWithDP(g, {
            allowGaps: true,
            filterCompounds: false
        });

        this.segCache.set(node, { text, segments });
        return segments;
    }

    // Segment compound surface (inner segmentation)
    segmentSurface(node, surface) {
        const g = this.split(node, surface);

        return this.segmentWithDP(g, {
            allowGaps: false,          // Don't allow gaps in compound segmentation
            filterCompounds: true,     // Exclude compound entries
            fullSurface: surface       // Use isBetter comparison
        });
    }

    // Find which segment contains the cursor
    findSegmentAtCursor(segments, cursorGi) {
        if (!segments) return null;

        for (const seg of segments) {
            const endGi = seg.start + seg.length;
            if (cursorGi >= seg.start && cursorGi < endGi) {
                return seg;
            }
        }
        return null;
    }

    getAt(node, text, offset) {
        const g = this.split(node, text);

        // Find grapheme index at cursor
        let pos = 0, gi = 0;
        for (const c of g) {
            if (pos >= offset) break;
            pos += c.length;
            gi++;
        }
        gi = Math.min(gi, g.length - 1);

        // Get consistent segmentation for entire text
        const segments = this.getSegmentation(node, text);

        // Find which segment contains cursor
        const bestMatch = this.findSegmentAtCursor(segments, gi);

        if (!bestMatch || !bestMatch.entries.length) {
            return null;
        }

        let innerSegments = null;

        // Only segment compounds
        if (bestMatch.entries.some(e => e.is_compound)) {
            const seg = this.segmentSurface(node, bestMatch.surface);
            if (seg && seg.length > 1) {
                innerSegments = seg;
            }
        }

        return {
            graphemes: g,
            match: bestMatch,
            innerSegments
        };
    }
}