# Project Magic 🧙‍♂️

AI-generated Magic: The Gathering combat scenes. Pulls two random creature cards and a land from Scryfall, simulates combat using power/toughness, then generates an original battle scene using the Grok image API.

## How it works

1. Fetches 2 random creatures from Scryfall
2. Simulates MTG combat (power vs toughness)
3. Fetches a basic land matching the winner's color
4. Downloads card art as reference
5. Generates an AI scene depicting the combat outcome
6. Saves the result to `gen_scenes/`

## Setup

```
pip install -r requirements.txt
cp .env.example .env
```

Add your xAI API key to `.env`.

## Usage

```
python main.py
```

Pick option 1, and let it rip.

## Disclaimer

This project is not affiliated with, endorsed by, or sponsored by Wizards of the Coast, Hasbro, Scryfall, or xAI. Magic: The Gathering is a trademark of Wizards of the Coast LLC. Card data and artwork are retrieved via the [Scryfall API](https://scryfall.com/) and remain the property of their respective owners. AI-generated images are produced via the [Grok API](https://docs.x.ai/) and are subject to xAI's terms of use. This project is for personal/educational use only.
