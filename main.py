import os
import re
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


def safe_request(method, url, error_msg, timeout=15, **kwargs):
    """Make an HTTP request with error handling. Exits on failure."""
    try:
        resp = requests.request(method, url, timeout=timeout, **kwargs)
        resp.raise_for_status()
    except requests.RequestException as e:
        print(f"\n  Error: {error_msg} — {e}")
        sys.exit(1)
    return resp


def get_subtypes(card):
    """Extract creature/spell subtypes from a type line (e.g. 'Creature — Human Soldier' -> 'Human Soldier')."""
    type_line = card["type_line"]
    return type_line.split(" — ")[-1] if " — " in type_line else ""


def fetch_scryfall_card(query):
    """Fetch a single random card from Scryfall."""
    resp = safe_request(
        "GET", "https://api.scryfall.com/cards/random",
        "Could not reach Scryfall API",
        params={"q": query}, headers=SCRYFALL_HEADERS,
    )

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
    """Download card art and return (base64 data URI, raw bytes)."""
    resp = safe_request("GET", url, "Could not download card art", headers=SCRYFALL_HEADERS)
    b64 = base64.b64encode(resp.content).decode("utf-8")
    content_type = resp.headers.get("Content-Type", "image/jpeg")
    return f"data:{content_type};base64,{b64}", resp.content


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


def fetch_damage_spell():
    """Fetch a random instant or sorcery that deals damage."""
    time.sleep(0.1)
    return fetch_scryfall_card('(type:instant or type:sorcery) oracle:"deals" oracle:"damage"')


def parse_spell_damage(oracle_text):
    """Try to extract a numeric damage value from oracle text. Returns int or None."""
    match = re.search(r"deals\s+(\d+)\s+damage", oracle_text, re.IGNORECASE)
    if match:
        return int(match.group(1))
    return None


def resolve_spell(creature, spell):
    """Resolve a damage spell against a creature. Returns (outcome, description)."""
    damage = parse_spell_damage(spell["oracle_text"])

    try:
        toughness = int(creature["toughness"])
    except (TypeError, ValueError):
        toughness = None

    if damage is not None and toughness is not None:
        if damage >= toughness:
            return "killed", (
                f"{spell['name']} deals {damage} damage to {creature['name']} "
                f"(toughness {toughness}) — lethal! The creature is destroyed."
            )
        else:
            return "survived", (
                f"{spell['name']} deals {damage} damage to {creature['name']} "
                f"(toughness {toughness}) — it survives, battered but still standing."
            )
    else:
        return "unknown", (
            f"{spell['name']} unleashes its power on {creature['name']} — "
            f"the outcome is uncertain and chaotic."
        )


def build_combat_prompt(cards, outcome):
    """Build the image generation prompt for creature-vs-creature combat."""
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

    c1_subtypes = get_subtypes(creature1)
    c2_subtypes = get_subtypes(creature2)

    return (
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


def build_spell_prompt(cards, outcome):
    """Build the image generation prompt for a spell targeting a creature."""
    creature, spell, land = cards

    c_subtypes = get_subtypes(creature)
    spell_type = "instant" if "Instant" in spell["type_line"] else "sorcery"

    if outcome == "killed":
        outcome_direction = (
            f"The spell is LETHAL. {creature['name']} is being destroyed, disintegrated, or torn apart by the spell's effect. "
            f"Show the creature in its final moments — overwhelmed and consumed by the spell's power."
        )
    elif outcome == "survived":
        outcome_direction = (
            f"The spell hits hard but {creature['name']} SURVIVES. The creature is visibly hurt, staggered, scorched, or wounded — "
            f"but still standing, enduring the blast through sheer resilience. Show the creature bracing against the impact."
        )
    else:
        outcome_direction = (
            f"The spell's effect on {creature['name']} is chaotic and unpredictable. "
            f"Show a dramatic moment of impact — the outcome hangs in the balance."
        )

    return (
        f"Generate a dramatic Magic: The Gathering scene of a creature being hit by a powerful {spell_type} spell. "
        f"The creature is {creature['name']}, a {c_subtypes}. "
        f"The spell is {spell['name']} — here is exactly what it does: \"{spell['oracle_text']}\" "
        f"Use the spell's card art as creative inspiration for how the spell's magic manifests visually — "
        f"the colors, energy, effects, and mood it conveys. Do NOT recreate the spell art directly. "
        f"Instead, imagine what this spell would look like the moment it strikes the creature. "
        f"{outcome_direction} "
        f"The environment is inspired by a {land['name']} — use the land reference image as loose inspiration "
        f"for the setting's mood, terrain, and palette. Do NOT recreate the land art. "
        f"Build an original environment from a fresh angle and perspective. "
        f"Use the creature reference image as loose inspiration for the creature's appearance — "
        f"do NOT replicate its pose or composition. "
        f"The creature should be reacting to the spell — recoiling, shielding, roaring in pain, or being flung back. "
        f"The spell effect should be the visual centerpiece — big, dramatic, and unmistakable. "
        f"Think of this as a screenshot from a cinematic trailer. "
        f"Take massive creative liberties. Dramatic lighting, detailed fantasy art style."
    )


def generate_scene(cards, art_b64_list, outcome, mode="combat"):
    """Generate a combined scene using Grok image editing API."""
    if not XAI_API_KEY:
        print("Error: XAI_API_KEY not set in .env file")
        sys.exit(1)

    if mode == "spell":
        prompt = build_spell_prompt(cards, outcome)
    else:
        prompt = build_combat_prompt(cards, outcome)

    print("  Generating scene...")

    resp = safe_request(
        "POST", "https://api.x.ai/v1/images/edits",
        "Image generation failed", timeout=60,
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
    data = resp.json()

    image_url = data["data"][0]["url"]
    image_resp = safe_request("GET", image_url, "Could not download generated image", timeout=30)

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


def print_matchup(card_a, tag_a, card_b, tag_b, separator, outcome, outcome_labels, description):
    """Print a matchup display between two cards with outcome."""
    print(format_card_box(card_a, tag_a))
    print()
    print(f"  ~~~ {separator} ~~~")
    print()
    print(format_card_box(card_b, tag_b))
    print()
    print(f"  {outcome_labels.get(outcome, '???')}")
    print(f"  {description}")
    print()


def print_battle_card(c1, c2, outcome, combat_desc):
    """Print a VS display for the two creatures."""
    print_matchup(c1, "ATTACKER", c2, "BLOCKER", "VS", outcome, {
        "c1_wins": f">>> {c1['name']} WINS <<<",
        "c2_wins": f">>> {c2['name']} WINS <<<",
        "trade": ">>> DOUBLE KO <<<",
        "stalemate": ">>> STALEMATE <<<",
        "unknown": ">>> OUTCOME UNKNOWN <<<",
    }, combat_desc)


def print_spell_card(creature, spell, outcome, spell_desc):
    """Print a display for a spell targeting a creature."""
    print_matchup(creature, "TARGET", spell, f"SPELL ({spell['type_line']})", "HIT BY", outcome, {
        "killed": f">>> {creature['name']} IS DESTROYED <<<",
        "survived": f">>> {creature['name']} SURVIVES <<<",
        "unknown": ">>> OUTCOME UNKNOWN <<<",
    }, spell_desc)


def download_art_set(cards, labels):
    """Download card art for a list of cards, save to gen_images/, return base64 list."""
    art_b64_list = []
    os.makedirs("gen_images", exist_ok=True)
    for card, label in zip(cards, labels):
        data_uri, raw_bytes = download_card_art(card["art_crop_url"])
        art_b64_list.append(data_uri)
        img_path = os.path.join("gen_images", f"{label}.jpg")
        with open(img_path, "wb") as f:
            f.write(raw_bytes)
        print(f"    Saved {label} card art -> {img_path}")
    return art_b64_list


def main():
    print("=== Project Magic ===")
    print("1. Creature combat (random)")
    print("2. Spell attack (random)")
    print("3. Choose your cards (coming soon)")
    print()

    choice = input("Enter choice: ").strip()

    if choice == "1":
        print("\nFetching random creatures from Scryfall...\n")
        c1, c2 = fetch_creatures()

        outcome, combat_desc = resolve_combat(c1, c2)
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
        art_b64_list = download_art_set(cards, ["attacker", "defender", "land"])

        output_path = generate_scene(cards, art_b64_list, outcome, mode="combat")
        print(f"\n  Scene saved to {output_path}")

    elif choice == "2":
        print("\nFetching a random creature from Scryfall...")
        creature = fetch_scryfall_card("type:creature")

        print(f"  Got: {creature['name']}")
        print("\nFetching a random damage spell...")
        spell = fetch_damage_spell()
        print(f"  Got: {spell['name']}")

        outcome, spell_desc = resolve_spell(creature, spell)
        print()
        print_spell_card(creature, spell, outcome, spell_desc)

        spell_colors = spell["colors"]
        print(f"  Fetching land for spell's color ({', '.join(spell_colors) or 'colorless'})...")
        land = fetch_land_for_color(spell_colors)
        print(f"  Land: {land['name']}\n")

        cards = [creature, spell, land]
        print("  Downloading card art...")
        art_b64_list = download_art_set(cards, ["creature", "spell", "land"])

        output_path = generate_scene(cards, art_b64_list, outcome, mode="spell")
        print(f"\n  Scene saved to {output_path}")

    elif choice == "3":
        print("\nComing soon!")

    else:
        print("\nInvalid choice.")


if __name__ == "__main__":
    main()
