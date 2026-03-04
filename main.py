import os
import sys
import time
import base64
import requests
from dotenv import load_dotenv

load_dotenv()

XAI_API_KEY = os.getenv("XAI_API_KEY")
SCRYFALL_HEADERS = {"User-Agent": "ProjectMagic/1.0"}


COLOR_TO_BASIC = {
    "W": "!Plains",
    "U": "!Island",
    "B": "!Swamp",
    "R": "!Mountain",
    "G": "!Forest",
}


def fetch_scryfall_card(query):
    """Fetch a single random card from Scryfall."""
    resp = requests.get(
        "https://api.scryfall.com/cards/random",
        params={"q": query},
        headers=SCRYFALL_HEADERS,
    )
    resp.raise_for_status()
    data = resp.json()

    image_uris = data.get("image_uris") or data["card_faces"][0]["image_uris"]

    return {
        "name": data["name"],
        "type_line": data["type_line"],
        "oracle_text": data.get("oracle_text", ""),
        "flavor_text": data.get("flavor_text", ""),
        "colors": data.get("colors") or data.get("color_identity", []),
        "power": data.get("power"),
        "toughness": data.get("toughness"),
        "art_crop_url": image_uris["art_crop"],
    }


def fetch_creatures():
    """Fetch 2 random creatures from Scryfall."""
    c1 = fetch_scryfall_card("type:creature")
    time.sleep(0.1)
    c2 = fetch_scryfall_card("type:creature")
    return c1, c2


def fetch_land_for_color(colors):
    """Fetch a random basic land matching the given color(s). Falls back to Forest."""
    basic_name = COLOR_TO_BASIC.get(colors[0] if colors else "", "!Forest")
    time.sleep(0.1)
    return fetch_scryfall_card(basic_name)


def download_card_art(url):
    """Download card art and return as base64 data URI."""
    resp = requests.get(url, headers=SCRYFALL_HEADERS)
    resp.raise_for_status()
    b64 = base64.b64encode(resp.content).decode("utf-8")
    content_type = resp.headers.get("Content-Type", "image/jpeg")
    return f"data:{content_type};base64,{b64}"


def resolve_combat(c1, c2):
    """Simulate MTG combat between two creatures. Returns (outcome, description)."""
    try:
        p1, t1 = int(c1["power"]), int(c1["toughness"])
        p2, t2 = int(c2["power"]), int(c2["toughness"])
    except (TypeError, ValueError):
        # Handle */*, X/X, etc.
        return "unknown", "The combat outcome is uncertain — both creatures clash with unpredictable power."

    c1_dies = p2 >= t1
    c2_dies = p1 >= t2

    if c1_dies and c2_dies:
        return "trade", (
            f"Both creatures destroy each other! "
            f"{c1['name']} ({p1}/{t1}) and {c2['name']} ({p2}/{t2}) trade lethal blows."
        )
    elif c2_dies:
        return "c1_wins", (
            f"{c1['name']} ({p1}/{t1}) overpowers {c2['name']} ({p2}/{t2}), "
            f"delivering a killing blow while surviving the fight."
        )
    elif c1_dies:
        return "c2_wins", (
            f"{c2['name']} ({p2}/{t2}) overpowers {c1['name']} ({p1}/{t1}), "
            f"delivering a killing blow while surviving the fight."
        )
    else:
        return "stalemate", (
            f"Neither creature can finish the other! "
            f"{c1['name']} ({p1}/{t1}) and {c2['name']} ({p2}/{t2}) are locked in a stalemate."
        )


def generate_scene(cards, art_b64_list, outcome):
    """Generate a combined scene using Grok image editing API."""
    if not XAI_API_KEY:
        print("Error: XAI_API_KEY not set in .env file")
        sys.exit(1)

    creature1, creature2, land = cards

    if outcome == "c1_wins":
        scene_direction = (
            f"{creature1['name']} is ruthlessly striking down {creature2['name']}. "
            f"{creature2['name']} is clearly defeated — collapsing, crumbling, or being destroyed by the blow. "
            f"{creature1['name']} is the dominant victor."
        )
    elif outcome == "c2_wins":
        scene_direction = (
            f"{creature2['name']} is ruthlessly striking down {creature1['name']}. "
            f"{creature1['name']} is clearly defeated — collapsing, crumbling, or being destroyed by the blow. "
            f"{creature2['name']} is the dominant victor."
        )
    elif outcome == "trade":
        scene_direction = (
            f"Both {creature1['name']} and {creature2['name']} are killing each other simultaneously in violent combat — "
            f"each landing a fatal blow on the other. Both are visibly wounded, bleeding, and falling. "
            f"This is a brutal fight to the death, not a friendly encounter."
        )
    elif outcome == "stalemate":
        scene_direction = (
            f"{creature1['name']} and {creature2['name']} are clashing fiercely but neither can break through. "
            f"They are locked in an intense struggle, evenly matched."
        )
    else:
        scene_direction = (
            f"{creature1['name']} and {creature2['name']} clash with unpredictable, wild energy."
        )

    # Extract creature subtypes (e.g. "Creature — Human Soldier" -> "Human Soldier")
    c1_subtypes = creature1["type_line"].split(" — ")[-1] if " — " in creature1["type_line"] else ""
    c2_subtypes = creature2["type_line"].split(" — ")[-1] if " — " in creature2["type_line"] else ""

    prompt = (
        f"This is a Magic: The Gathering combat scene — one creature is attacking and the other is blocking. "
        f"The attacker is {creature1['name']}, a {c1_subtypes} creature. "
        f"The blocker is {creature2['name']}, a {c2_subtypes} creature. "
        f"{scene_direction} "
        f"The environment is inspired by a {land['name']} — use the land reference image only as loose inspiration "
        f"for the general mood, terrain type, and color palette. NEVER recreate the land art directly. "
        f"Re-orient the environment — show it from a completely different angle, perspective, or vantage point "
        f"to add depth and cinematic framing to the scene. "
        f"Build an original environment that fits the combat naturally, with the creatures grounded within it. "
        f"Use the creature reference images as loose inspiration for their appearance — "
        f"do NOT replicate poses or compositions from any reference image. "
        f"BOTH creatures MUST be clearly visible as two separate, distinct beings in the scene — never merged or blended together. "
        f"Every creature MUST be in mid-action — attacking, lunging, dodging, casting, charging, or recoiling from a hit. "
        f"No standing, posing, or static stances. Capture a frozen moment of intense combat. "
        f"Creatures can be shown from any angle — from behind, from the side, over the shoulder, etc. — "
        f"whatever serves the composition best. Not every face needs to be visible. "
        f"Take creative liberties to make the scene feel alive and cinematic. "
        f"Dramatic lighting, detailed fantasy art style."
    )

    print("  Generating scene...")

    resp = requests.post(
        "https://api.x.ai/v1/images/edits",
        headers={
            "Authorization": f"Bearer {XAI_API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "model": "grok-imagine-image",
            "prompt": prompt,
            "n": 1,
            "images": [{"url": uri, "type": "base64"} for uri in art_b64_list],
        },
    )
    resp.raise_for_status()
    data = resp.json()

    image_url = data["data"][0]["url"]
    image_resp = requests.get(image_url)
    image_resp.raise_for_status()

    os.makedirs("gen_scenes", exist_ok=True)
    output_path = os.path.join("gen_scenes", "scene.png")
    with open(output_path, "wb") as f:
        f.write(image_resp.content)

    return output_path


def format_card_box(card, tag=""):
    """Format a single card as a CLI box."""
    name = card["name"]
    typeline = card["type_line"]
    pt = f"{card.get('power', '?')}/{card.get('toughness', '?')}"
    colors = ", ".join(card.get("colors", [])) or "Colorless"

    lines = [
        f"  {tag}" if tag else "",
        f"  {name}",
        f"  {typeline}",
        f"  P/T: {pt}   Colors: {colors}",
    ]
    # Calculate box width
    content_lines = [l.strip() for l in lines if l.strip()]
    width = max(len(l) for l in content_lines) + 4

    box = []
    box.append("  +" + "-" * width + "+")
    for line in content_lines:
        box.append(f"  | {line:<{width - 2}} |")
    box.append("  +" + "-" * width + "+")
    return "\n".join(box)


def print_battle_card(c1, c2, outcome, combat_desc):
    """Print a VS display for the two creatures."""
    outcome_labels = {
        "c1_wins": f">>> {c1['name']} WINS <<<",
        "c2_wins": f">>> {c2['name']} WINS <<<",
        "trade": ">>> DOUBLE KO <<<",
        "stalemate": ">>> STALEMATE <<<",
        "unknown": ">>> OUTCOME UNKNOWN <<<",
    }

    print(format_card_box(c1, "ATTACKER"))
    print()
    vs_line = "  ~~~ VS ~~~"
    print(vs_line)
    print()
    print(format_card_box(c2, "BLOCKER"))
    print()

    result = outcome_labels.get(outcome, "???")
    print(f"  {result}")
    print(f"  {combat_desc}")
    print()


def main():
    print("=== Project Magic ===")
    print("1. Random cards")
    print("2. Choose your cards (coming soon)")
    print()

    choice = input("Enter choice: ").strip()

    if choice == "1":
        print("\nFetching random creatures from Scryfall...\n")
        c1, c2 = fetch_creatures()

        # Resolve combat
        outcome, combat_desc = resolve_combat(c1, c2)

        # Display card boxes
        print_battle_card(c1, c2, outcome, combat_desc)

        if outcome == "c1_wins":
            winner_colors = c1["colors"]
        elif outcome == "c2_wins":
            winner_colors = c2["colors"]
        else:
            winner_colors = c1["colors"]

        print(f"  Fetching land for winner's color ({', '.join(winner_colors) or 'colorless'})...")
        land = fetch_land_for_color(winner_colors)
        print(f"  Land: {land['name']}\n")

        cards = [c1, c2, land]

        print("  Downloading card art...")
        art_b64_list = []
        for card in cards:
            art_b64_list.append(download_card_art(card["art_crop_url"]))

        output_path = generate_scene(cards, art_b64_list, outcome)
        print(f"\n  Scene saved to {output_path}")

    elif choice == "2":
        print("\nComing soon!")

    else:
        print("\nInvalid choice.")


if __name__ == "__main__":
    main()
