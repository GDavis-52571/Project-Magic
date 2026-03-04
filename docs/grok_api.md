# Grok (xAI) Image API Reference

## Image Generation (text-only)

**POST** `https://api.x.ai/v1/images/generations`

- Text prompt only, no reference images
- Model: `grok-imagine-image`

## Image Editing (with reference images)

**POST** `https://api.x.ai/v1/images/edits`

- Up to 3 input images via `images` array
- Images can be base64 data URIs or URLs
- Model: `grok-imagine-image`

### Authentication
```
Authorization: Bearer <XAI_API_KEY>
```

### Request Body (edits)
```json
{
  "model": "grok-imagine-image",
  "prompt": "descriptive scene prompt",
  "n": 1,
  "images": [
    {"url": "data:image/png;base64,...", "type": "base64"},
    {"url": "data:image/png;base64,...", "type": "base64"}
  ]
}
```

### Response
```json
{
  "data": [
    {
      "url": "https://...",
      "revised_prompt": "..."
    }
  ]
}
```

### Important Notes
- OpenAI SDK `edit()` method is NOT supported — use direct HTTP requests
- Images array accepts base64 data URIs or public URLs
- Max 3 reference images

### Source
https://docs.x.ai/developers/model-capabilities/images/generation
