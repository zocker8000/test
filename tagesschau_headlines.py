#!/usr/bin/env python3
"""Gibt die 10 wichtigsten Schlagzeilen von tagesschau.de aus.

Standardmäßig wird der offizielle RSS-Feed der Tagesschau-Startseite genutzt:
https://www.tagesschau.de/index~rss2.xml

Keine externen Abhängigkeiten nötig.
"""

from __future__ import annotations

import argparse
import sys
import xml.etree.ElementTree as ET
from typing import Iterable
from urllib.error import URLError, HTTPError
from urllib.request import Request, urlopen


DEFAULT_FEED_URL = "https://www.tagesschau.de/index~rss2.xml"
USER_AGENT = "Mozilla/5.0 (compatible; TagesschauHeadlines/1.0)"


def fetch_feed(url: str) -> bytes:
    request = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(request, timeout=15) as response:
        return response.read()


def extract_text(element: ET.Element | None, tag_names: Iterable[str]) -> str:
    if element is None:
        return ""
    for tag_name in tag_names:
        node = element.find(tag_name)
        if node is not None and node.text:
            return node.text.strip()
    return ""


def parse_headlines(xml_data: bytes, limit: int = 10) -> list[tuple[str, str]]:
    root = ET.fromstring(xml_data)
    channel = root.find("channel")
    if channel is None:
        raise ValueError("Ungültiger RSS-Feed: <channel> fehlt")

    headlines: list[tuple[str, str]] = []
    for item in channel.findall("item")[:limit]:
        title = extract_text(item, ["title"])
        link = extract_text(item, ["link"])
        if title:
            headlines.append((title, link))

    return headlines


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Gibt die 10 wichtigsten Schlagzeilen von tagesschau.de aus."
    )
    parser.add_argument(
        "--feed",
        default=DEFAULT_FEED_URL,
        help=f"RSS-Feed-URL (Standard: {DEFAULT_FEED_URL})",
    )
    parser.add_argument(
        "-n",
        "--number",
        type=int,
        default=10,
        help="Anzahl der Schlagzeilen (Standard: 10)",
    )
    args = parser.parse_args()

    try:
        xml_data = fetch_feed(args.feed)
        headlines = parse_headlines(xml_data, limit=args.number)
    except (HTTPError, URLError) as exc:
        print(f"Fehler beim Abrufen des Feeds: {exc}", file=sys.stderr)
        return 1
    except ET.ParseError as exc:
        print(f"Fehler beim Parsen des Feeds: {exc}", file=sys.stderr)
        return 1
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    for index, (title, link) in enumerate(headlines, start=1):
        if link:
            print(f"{index}. {title} - {link}")
        else:
            print(f"{index}. {title}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
