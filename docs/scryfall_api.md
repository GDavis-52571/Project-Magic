# Scryfall API Reference

## Random Card Endpoint

**GET** `https://api.scryfall.com/cards/random`

### Query Parameters
- `q` — Scryfall search syntax (e.g., `type:creature`, `type:land`)

### Headers
- `User-Agent` — Required. Identify your app (e.g., `ProjectMagic/1.0`)

### Rate Limiting
- 50–100ms delay between requests

### Response Fields (relevant)
| Field | Description |
|-------|-------------|
| `name` | Card name |
| `type_line` | Full type line (e.g., "Creature — Dragon") |
| `oracle_text` | Rules text |
| `flavor_text` | Flavor text (may be absent) |
| `image_uris.art_crop` | URL to cropped art image |

### Example Request
```
GET https://api.scryfall.com/cards/random?q=type:creature
User-Agent: ProjectMagic/1.0
```

### Notes
- Some cards (double-faced, split) use `card_faces` instead of top-level `image_uris`
- No authentication required

### Source
https://scryfall.com/docs/api
