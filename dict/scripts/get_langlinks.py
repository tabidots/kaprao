#!/usr/bin/env python3
"""
Wikipedia Language Link Fetcher
Get the linked article title for an English Wikipedia article in a target language.
"""

import argparse
from chinese_converter import to_traditional
import requests
import sys
import sqlite3
from dict.scripts.paths import DB_PATH


def get_langlink(english_title, target_lang, base_url="https://en.wikipedia.org"):
    """
    Fetch the language link for an English Wikipedia article in the target language.
    
    Args:
        english_title (str): Title of the English Wikipedia article
        target_lang (str): Target language code (e.g., 'my' for Burmese, 'fr' for French)
        base_url (str): Base URL for Wikipedia API (default: English Wikipedia)
    
    Returns:
        str: The article title in the target language, or "no article" if none exists
    """
    # Wikipedia API endpoint
    api_url = f"{base_url}/w/api.php"

    # Parameters for the API request
    params = {
        "action": "query",
        "titles": english_title,
        "prop": "langlinks",
        "lllang": target_lang,
        "format": "json",
        "formatversion": "2"  # Simplified JSON output
    }

    # Set a descriptive User-Agent header (required by Wikimedia)
    headers = {
        'User-Agent': 'LangLinkFetcher/1.0 (https://github.com/yourusername/langlink-fetcher; your-email@example.com) requests/2.0'
    }

    try:
        # Make the API request with custom headers
        response = requests.get(api_url, params=params,
                                headers=headers, timeout=10)
        response.raise_for_status()

        data = response.json()

        # Extract the page data
        pages = data.get("query", {}).get("pages", [])

        if not pages:
            return "no article"

        # Get the first page (there should be only one)
        page = pages[0]

        # Check if the page exists and has langlinks
        if "missing" in page or "langlinks" not in page:
            return "no article"

        # Get the language links
        langlinks = page.get("langlinks", [])

        if langlinks and len(langlinks) > 0:
            # Return the title in the target language
            return langlinks[0]["title"]
        else:
            return "no article"

    except requests.exceptions.RequestException as e:
        print(f"Error making API request: {e}", file=sys.stderr)
        return "error"
    except (KeyError, IndexError, ValueError) as e:
        print(f"Error parsing API response: {e}", file=sys.stderr)
        return "error"


def main():
    # Set up argument parser
    parser = argparse.ArgumentParser(
        description="Get the linked article title for an English Wikipedia article in a target language",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s "Moken language" -lang my
  %(prog)s "Python" -lang fr
  %(prog)s "United States" --language es --base-url "https://simple.wikipedia.org"
        """
    )

    # Positional argument for the English title
    parser.add_argument(
        "title",
        help="English Wikipedia article title (enclose in quotes if it contains spaces)"
    )

    # Required argument for language code
    parser.add_argument(
        "-l", "--lang", "--language",
        dest="language",
        required=True,
        help="Target language code (e.g., 'my' for Burmese, 'fr' for French, 'es' for Spanish)"
    )

    # Optional argument for base URL
    parser.add_argument(
        "-b", "--base-url",
        dest="base_url",
        default="https://en.wikipedia.org",
        help="Base URL for Wikipedia (default: https://en.wikipedia.org)"
    )

    # Parse arguments
    args = parser.parse_args()

    # Get the language link
    result = get_langlink(args.title, args.language, args.base_url)

    # Print the result
    print(result)

    # Return appropriate exit code
    sys.exit(0 if result not in ["error"] else 1)


if __name__ == "__main__":
    main()

    # from sinopy import pinyin, chars2baxter
    # from taibun import Converter

    # conv = Converter('POJ')

    # with sqlite3.connect(DB_PATH) as conn:
    #     c = conn.cursor()
    #     c.execute("""
    #         SELECT segmentation, head_noun, english, thai FROM th_wikipedia
    #         WHERE 
    #               has_oov = 1 AND categories like '%in China%'
             
    #         ORDER BY -- head_noun nulls last, 
    #                 -- english, length(segmentation) DESC, segmentation
    #               segmentation, english
    #     """)
    #     batch = []
    #     for segmentation, head_noun, english, thai in c.fetchall():
    #         if not english:
    #             result = get_langlink(thai, "zh", base_url="https://th.wikipedia.org")
    #         else:
    #             result = get_langlink(english, "zh")
            
    #         if result in ["no article", "error"]:
    #             mandarin, hokkien = "", ""
    #         else:
    #             result = to_traditional(result)
    #             mandarin = pinyin(result)
    #             hokkien = conv.get(result).title()
    #             if len(mandarin.split()) == 3:
    #                 a, b, c = mandarin.split()
    #                 mandarin = f"{a} {b}{c}".title()
    #             else:
    #                 mandarin = mandarin.title()
    #         print(f"{segmentation}\t{result} ({mandarin})\t{hokkien}")
            
            # if result in ["no article", "error"]:
            #     continue
            # print(f"{thai}\t{result} ({english})")
