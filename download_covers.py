#!/usr/bin/env python3
"""
download_covers.py  v2
======================
Downloads album covers for prog_metal_timeline.html and prog_metal_grid.html.

PRIMARY source  : iTunes Search API  (free, no key, ~99% hit rate for metal)
FALLBACK source : MusicBrainz + Cover Art Archive  (open, no key)

Place this script in the SAME folder as the two HTML files.
Covers are saved to  ./covers/<slug>.jpg

Re-running is safe — already-downloaded files are skipped automatically.

Requirements:
    pip install requests
"""

import re
import sys
import time
import shutil
import requests
from pathlib import Path

# ── config ────────────────────────────────────────────────────────────────────
COVERS_DIR   = Path(__file__).parent / "covers_no"
IMG_SIZE     = 600          # px  (iTunes supports 100 / 600 / 3000)
ITUNES_DELAY = 0.4          # ~20 req/min iTunes limit
MB_DELAY     = 1.1          # MusicBrainz: max 1 req/s
TIMEOUT      = 20

COVERS_DIR.mkdir(exist_ok=True)

SESSION = requests.Session()
SESSION.headers.update({
    "User-Agent": "ProgMetalCoverDownloader/2.0 (educational project)"
})


# ══════════════════════════════════════════════════════════════════════════════
#  SLUG — must match JS makeSlug() in both HTML files exactly
# ══════════════════════════════════════════════════════════════════════════════
def make_slug(band: str, album: str) -> str:
    s = (band + "-" + album).lower()
    s = s.replace("&", "and")
    s = re.sub(r"[:/]", "", s)
    s = s.replace("'", "").replace("\u2019", "")
    s = re.sub(r"\s+", "_", s)
    s = re.sub(r"[^a-z0-9_\-]", "", s)
    return s[:50]


# ══════════════════════════════════════════════════════════════════════════════
#  ALBUM LIST  — (band, album, itunes_override_or_None)
#  itunes_override: alternative search string for ambiguous/special titles
# ══════════════════════════════════════════════════════════════════════════════
ALBUMS = [
    # ── ORIGIN ────────────────────────────────────────────────────────────────
    ("King Crimson",          "In the Court of the Crimson King",        None),
    ("Black Sabbath",         "Black Sabbath",                           "Black Sabbath debut album 1970"),
    ("Black Sabbath",         "Paranoid",                                None),
    ("Black Sabbath",         "Master of Reality",                       None),
    ("Yes",                   "Close to the Edge",                       None),
    ("Genesis",               "Selling England by the Pound",            None),
    ("Emerson Lake & Palmer", "Brain Salad Surgery",                     "ELP Brain Salad Surgery"),
    ("King Crimson",          "Red",                                     "King Crimson Red 1974"),
    ("Black Sabbath",         "Sabotage",                                None),
    ("Rush",                  "2112",                                    None),
    ("Rush",                  "Hemispheres",                             None),
    ("Rush",                  "Permanent Waves",                         None),
    ("Rush",                  "Moving Pictures",                         None),
    ("Iron Maiden",           "Iron Maiden",                             "Iron Maiden self-titled 1980"),
    ("Iron Maiden",           "The Number of the Beast",                 None),
    ("Black Sabbath",         "Heaven and Hell",                         None),
    ("Black Sabbath",         "Mob Rules",                               None),
    ("Dio",                   "Holy Diver",                              None),

    # ── BIRTH ─────────────────────────────────────────────────────────────────
    ("Fates Warning",         "Night on Bröcken",                        "Fates Warning Night on Brocken"),
    ("Fates Warning",         "The Spectre Within",                      None),
    ("Watchtower",            "Energetic Disassembly",                   None),
    ("Fates Warning",         "Awaken the Guardian",                     None),
    ("Crimson Glory",         "Crimson Glory",                           "Crimson Glory album 1986"),
    ("Queensryche",           "Rage for Order",                          None),
    ("Crimson Glory",         "Transcendence",                           "Crimson Glory Transcendence"),
    ("Queensryche",           "Operation Mindcrime",                     None),
    ("Voivod",                "Killing Technology",                      None),
    ("Voivod",                "Dimension Hatross",                       "Voivod Dimension Hatross"),
    ("Voivod",                "Nothingface",                             None),
    ("Watchtower",            "Control and Resistance",                  None),
    ("Fates Warning",         "No Exit",                                 None),

    # ── CLASSIC ERA ───────────────────────────────────────────────────────────
    ("Atheist",               "Piece of Time",                           None),
    ("Atheist",               "Unquestionable Presence",                 None),
    ("Death",                 "Human",                                   "Death Human 1991 metal"),
    ("Fates Warning",         "Parallels",                               None),
    ("Queensryche",           "Empire",                                  None),
    ("Dream Theater",         "Images and Words",                        None),
    ("Cynic",                 "Focus",                                   "Cynic Focus 1993"),
    ("Death",                 "Individual Thought Patterns",             None),
    ("Dream Theater",         "Awake",                                   "Dream Theater Awake 1994"),
    ("Atheist",               "Elements",                                "Atheist Elements 1993"),
    ("Death",                 "Symbolic",                                None),
    ("Symphony X",            "The Divine Wings of Tragedy",             None),
    ("Dream Theater",         "A Change of Seasons",                     None),
    ("Dream Theater",         "Falling into Infinity",                   None),
    ("Fates Warning",         "A Pleasant Shade of Gray",                None),
    ("Symphony X",            "The Damnation Game",                      None),
    ("Savatage",              "Edge of Thorns",                          None),

    # ── EXPANSION ─────────────────────────────────────────────────────────────
    ("Tool",                  "Aenima",                                  None),
    ("Opeth",                 "Morningrise",                             None),
    ("Opeth",                 "My Arms Your Hearse",                     None),
    ("Ayreon",                "Into the Electric Castle",                None),
    ("Opeth",                 "Still Life",                              "Opeth Still Life 1999"),
    ("Pain of Salvation",     "The Perfect Element Part I",              None),
    ("Opeth",                 "Blackwater Park",                         None),
    ("Tool",                  "Lateralus",                               None),
    ("Pain of Salvation",     "Remedy Lane",                             None),
    ("Porcupine Tree",        "In Absentia",                             None),
    ("Devin Townsend",        "Ocean Machine Biomech",                   "Devin Townsend Ocean Machine"),
    ("Devin Townsend",        "Terria",                                  None),
    ("Devin Townsend",        "Accelerated Evolution",                   None),
    ("Meshuggah",             "Destroy Erase Improve",                   None),
    ("Meshuggah",             "Chaosphere",                              None),
    ("Meshuggah",             "Nothing",                                 "Meshuggah Nothing 2002"),
    ("Porcupine Tree",        "Deadwing",                                None),
    ("Dream Theater",         "Metropolis Part 2 Scenes from a Memory",  "Dream Theater Metropolis Scenes from a Memory"),
    ("Dream Theater",         "Six Degrees of Inner Turbulence",         None),
    ("Symphony X",            "V The New Mythology Suite",               "Symphony X New Mythology Suite"),
    ("Pain of Salvation",     "Be",                                      "Pain of Salvation Be 2004"),
    ("Porcupine Tree",        "Fear of a Blank Planet",                  None),
    ("Meshuggah",             "ObZen",                                   None),
    ("Opeth",                 "Ghost Reveries",                          None),
    ("Riverside",             "Second Life Syndrome",                    None),
    ("Tool",                  "10000 Days",                              None),
    ("Ayreon",                "The Human Equation",                      None),
    ("Fates Warning",         "FWX",                                     None),
    ("Isis",                  "Panopticon",                              "Isis Panopticon 2004 metal"),
    ("Mastodon",              "Leviathan",                               None),

    # ── MODERN ────────────────────────────────────────────────────────────────
    ("Savatage",              "Gutter Ballet",                           None),
    ("Between the Buried and Me", "Colors",                              None),
    ("Devin Townsend Project",    "Addicted",                            None),
    ("Periphery",                 "Periphery",                           "Periphery self-titled album 2010"),
    ("Animals as Leaders",        "Animals as Leaders",                  "Animals as Leaders self-titled"),
    ("Haken",                     "Visions",                             None),
    ("Opeth",                     "Heritage",                            None),
    ("Leprous",                   "Bilateral",                           None),
    ("Animals as Leaders",        "The Joy of Motion",                   None),
    ("Haken",                     "The Mountain",                        None),
    ("Periphery",                 "Juggernaut Alpha",                    None),
    ("Leprous",                   "Coal",                                None),
    ("Riverside",                 "Anno Domini High Definition",         None),
    ("Between the Buried and Me", "The Parallax II Future Sequence",     None),
    ("Caligula's Horse",          "In Contact",                          None),
    ("Leprous",                   "Malina",                              None),
    ("Haken",                     "Affinity",                            None),
    ("Dream Theater",             "A Dramatic Turn of Events",           None),
    ("Devin Townsend Project",    "Transcendence",                       None),
    ("Tool",                      "Fear Inoculum",                       None),
    ("Caligula's Horse",          "Rise Radiant",                        None),
    ("Leprous",                   "Aphelion",                            None),
    ("Haken",                     "Virus",                               None),
    ("Persefone",                 "Aathma",                              None),
    ("Opeth",                     "In Cauda Venenum",                    None),

    # ── MODERN · POST-DJENT DECADE (2015–2025) ────────────────────────────────
    ("Leprous",                   "The Congregation",                    None),
    ("Leprous",                   "Pitfalls",                            None),
    ("Rivers of Nihil",           "Where Owls Know My Name",             None),
    ("Blood Incantation",         "Hidden History of the Human Race",    "Blood Incantation Hidden History"),
    ("Dream Theater",             "Parasomnia",                          None),
    ("Tesseract",                 "Altered State",                       None),
    ("Tesseract",                 "Polaris",                             None),
    ("Meshuggah",                 "Nothing",                             None),
]

# Timeline HTML uses element id= values as filenames (e.g. "cov-kc.jpg")
# These map each id to the (band, album) whose downloaded slug file to copy from
TIMELINE_IDS = {
    "cov-kc":           ("King Crimson",              "In the Court of the Crimson King"),
    "cov-sabbath":      ("Black Sabbath",              "Paranoid"),
    "cov-sabbath-dio":  ("Black Sabbath",              "Heaven and Hell"),
    "cov-yes":          ("Yes",                        "Close to the Edge"),
    "cov-rush":         ("Rush",                       "2112"),
    "cov-maiden":       ("Iron Maiden",                "The Number of the Beast"),
    "cov-fw-spectre":   ("Fates Warning",              "The Spectre Within"),
    "cov-fw-guardian":  ("Fates Warning",              "Awaken the Guardian"),
    "cov-watchtower":   ("Watchtower",                 "Control and Resistance"),
    "cov-qr":           ("Queensryche",                "Operation Mindcrime"),
    "cov-cg":           ("Crimson Glory",              "Transcendence"),
    "cov-voivod":       ("Voivod",                     "Dimension Hatross"),
    "cov-fw-parallels": ("Fates Warning",              "Parallels"),
    "cov-atheist":      ("Atheist",                    "Unquestionable Presence"),
    "cov-death":        ("Death",                      "Human"),
    "cov-cynic":        ("Cynic",                      "Focus"),
    "cov-dt-iaw":       ("Dream Theater",              "Images and Words"),
    "cov-dt-awake":     ("Dream Theater",              "Awake"),
    "cov-sx":           ("Symphony X",                 "The Divine Wings of Tragedy"),
    "cov-fw-apsg":      ("Fates Warning",              "A Pleasant Shade of Gray"),
    "cov-tool":         ("Tool",                       "Lateralus"),
    "cov-pt":           ("Porcupine Tree",             "Fear of a Blank Planet"),
    "cov-opeth":        ("Opeth",                      "Blackwater Park"),
    "cov-meshuggah":    ("Meshuggah",                  "ObZen"),
    "cov-pos":          ("Pain of Salvation",          "Remedy Lane"),
    "cov-ayreon":       ("Ayreon",                     "Into the Electric Castle"),
    "cov-devin":        ("Devin Townsend",             "Ocean Machine Biomech"),
    "cov-btbam":        ("Between the Buried and Me",  "Colors"),
    "cov-periphery":    ("Periphery",                  "Juggernaut Alpha"),
    "cov-aal":          ("Animals as Leaders",         "The Joy of Motion"),
    "cov-riverside":    ("Riverside",                  "Second Life Syndrome"),
    "cov-haken":        ("Haken",                      "The Mountain"),
    "cov-leprous":      ("Leprous",                    "Malina"),
    "cov-calihorse":    ("Caligula's Horse",           "In Contact"),
    # ── new v3 entries ──────────────────────────────────────────────────────
    "cov-savatage":          ("Savatage",              "Gutter Ballet"),
    "cov-isis":              ("Isis",                  "Panopticon"),
    "cov-mastodon":          ("Mastodon",              "Leviathan"),
    "cov-leprous2":          ("Leprous",               "The Congregation"),
    "cov-rivers":            ("Rivers of Nihil",       "Where Owls Know My Name"),
    "cov-blood-incantation": ("Blood Incantation",     "Hidden History of the Human Race"),
    "cov-opeth2":            ("Opeth",                 "In Cauda Venenum"),
    "cov-dt-parasomnia":     ("Dream Theater",         "Parasomnia"),
    "cov-tesseract":         ("Tesseract",             "Altered State"),
    "cov-tesseract2":        ("Tesseract",             "Polaris"),
    "cov-meshuggah2":        ("Meshuggah",             "Nothing"),
}


# ══════════════════════════════════════════════════════════════════════════════
#  SOURCE 1 — iTunes Search API
# ══════════════════════════════════════════════════════════════════════════════
def itunes_get(band: str, album: str, override: str | None = None) -> str | None:
    """Return a 600px cover URL from iTunes, or None."""
    term   = override or f"{band} {album}"
    params = {"term": term, "entity": "album", "limit": 8, "media": "music"}
    try:
        r = SESSION.get("https://itunes.apple.com/search",
                        params=params, timeout=TIMEOUT)
        r.raise_for_status()
        results = r.json().get("results", [])
    except Exception as e:
        print(f"      iTunes error: {e}")
        return None

    band_l  = band.lower()
    album_l = album.lower()[:14]   # enough to disambiguate

    # Pass 1: exact artist + album match
    for res in results:
        if (band_l  in res.get("artistName",    "").lower() and
            album_l in res.get("collectionName","").lower()):
            art = res.get("artworkUrl100","")
            if art:
                return art.replace("100x100bb", f"{IMG_SIZE}x{IMG_SIZE}bb")

    # Pass 2: artist match only
    for res in results:
        if band_l in res.get("artistName","").lower():
            art = res.get("artworkUrl100","")
            if art:
                return art.replace("100x100bb", f"{IMG_SIZE}x{IMG_SIZE}bb")

    # Pass 3: anything with artwork
    for res in results:
        art = res.get("artworkUrl100","")
        if art:
            return art.replace("100x100bb", f"{IMG_SIZE}x{IMG_SIZE}bb")

    return None


# ══════════════════════════════════════════════════════════════════════════════
#  SOURCE 2 — MusicBrainz + Cover Art Archive
# ══════════════════════════════════════════════════════════════════════════════
def mb_get(band: str, album: str) -> str | None:
    """Return an image URL from MusicBrainz/CAA, or None."""
    try:
        params = {
            "query": f'release-group:"{album}" AND artist:"{band}"',
            "fmt":   "json", "limit": 5,
        }
        r = SESSION.get("https://musicbrainz.org/ws/2/release-group/",
                        params=params, timeout=TIMEOUT)
        r.raise_for_status()
        groups = r.json().get("release-groups", [])
        if not groups:
            return None
        rg_id = groups[0]["id"]
        time.sleep(0.3)
    except Exception as e:
        print(f"      MB error: {e}")
        return None

    try:
        r = SESSION.get(f"https://coverartarchive.org/release-group/{rg_id}/front",
                        timeout=TIMEOUT, allow_redirects=True)
        if r.status_code == 200 and "image" in r.headers.get("content-type",""):
            return r.url
        if "application/json" in r.headers.get("content-type",""):
            for img in r.json().get("images",[]):
                if img.get("front"):
                    t = img.get("thumbnails",{})
                    return t.get("500") or t.get("250") or img.get("image")
    except Exception as e:
        print(f"      CAA error: {e}")
    return None


# ══════════════════════════════════════════════════════════════════════════════
#  CORE DOWNLOAD
# ══════════════════════════════════════════════════════════════════════════════
def download_url(url: str, dest: Path) -> bool:
    try:
        r = SESSION.get(url, timeout=TIMEOUT, stream=True)
        r.raise_for_status()
        with open(dest, "wb") as f:
            for chunk in r.iter_content(8192):
                f.write(chunk)
        if dest.stat().st_size < 3000:
            dest.unlink(); return False
        return True
    except Exception as e:
        print(f"      DL error: {e}")
        dest.unlink(missing_ok=True)
        return False


def get_cover(slug: str, band: str, album: str,
              override: str | None = None) -> bool:
    """
    Download cover for (band, album) to covers/<slug>.jpg.
    Skips if file already exists and looks valid.
    Returns True if file is on disk after this call.
    """
    dest = COVERS_DIR / f"{slug}.jpg"
    if dest.exists() and dest.stat().st_size > 3000:
        return True

    # ── iTunes ───────────────────────────────────────────────────────────────
    url = itunes_get(band, album, override)
    time.sleep(ITUNES_DELAY)
    if url and download_url(url, dest):
        print(f"      ✓ iTunes  {dest.stat().st_size//1024} KB")
        return True

    # ── MusicBrainz + CAA ────────────────────────────────────────────────────
    print(f"      iTunes miss → MusicBrainz…")
    url = mb_get(band, album)
    time.sleep(MB_DELAY)
    if url and download_url(url, dest):
        print(f"      ✓ CAA     {dest.stat().st_size//1024} KB")
        return True

    print(f"      ✗ no cover found")
    return False


# ══════════════════════════════════════════════════════════════════════════════
#  MAIN
# ══════════════════════════════════════════════════════════════════════════════
def main():
    # Show existing state
    existing = {p.stem for p in COVERS_DIR.glob("*.jpg") if p.stat().st_size > 3000}
    total    = len(ALBUMS)
    slugs_needed = {make_slug(b, a) for b, a, _ in ALBUMS}
    missing  = slugs_needed - existing
    print(f"\n{'═'*62}")
    print(f"  Progressive Metal Cover Downloader  v2")
    print(f"  Output     : {COVERS_DIR.resolve()}")
    print(f"  Albums     : {total}  |  cached: {len(slugs_needed & existing)}  |  to fetch: {len(missing)}")
    print(f"{'═'*62}\n")

    # ── Step 1: download all grid slugs ──────────────────────────────────────
    ok = fail = skip = 0
    seen: set[str] = set()

    for band, album, override in ALBUMS:
        slug = make_slug(band, album)
        if slug in seen:
            continue
        seen.add(slug)

        dest = COVERS_DIR / f"{slug}.jpg"
        if dest.exists() and dest.stat().st_size > 3000:
            print(f"  — cached   {slug}")
            skip += 1
            continue

        label = f"{band} — {album}"
        print(f"  ↓ {label[:58]}")
        if get_cover(slug, band, album, override):
            ok += 1
        else:
            fail += 1

    # ── Step 2: timeline id aliases ──────────────────────────────────────────
    print(f"\n  Creating timeline aliases…\n")
    a_ok = a_fail = 0

    for tl_id, (band, album) in TIMELINE_IDS.items():
        dst = COVERS_DIR / f"{tl_id}.jpg"
        if dst.exists() and dst.stat().st_size > 3000:
            a_ok += 1
            continue

        src_slug = make_slug(band, album)
        src      = COVERS_DIR / f"{src_slug}.jpg"

        if src.exists() and src.stat().st_size > 3000:
            shutil.copy2(src, dst)
            a_ok += 1
        else:
            print(f"  ↓ alias {tl_id}  [{band} — {album}]")
            if get_cover(tl_id, band, album):
                a_ok += 1
            else:
                a_fail += 1

    # ── Summary ───────────────────────────────────────────────────────────────
    total_on_disk = len(list(COVERS_DIR.glob("*.jpg")))
    print(f"\n{'═'*62}")
    print(f"  Albums  : ✓ {ok + skip} ready  (downloaded {ok}, cached {skip}, failed {fail})")
    print(f"  Aliases : ✓ {a_ok}  ✗ {a_fail}")
    print(f"  Files in covers/ : {total_on_disk}")
    print(f"{'═'*62}")
    if fail or a_fail:
        print(f"\n  {fail + a_fail} covers still missing.")
        print(f"  Re-running will retry. For persistent failures, drop any")
        print(f"  <slug>.jpg manually into the covers/ folder.\n")


if __name__ == "__main__":
    main()
