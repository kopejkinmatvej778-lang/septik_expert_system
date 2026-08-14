# PNG rendering

## Renderer

Use Python + Pillow for MVP.

Existing pattern:

```python
from PIL import Image, ImageDraw, ImageFont
image = Image.open(template).convert("RGB")
draw = ImageDraw.Draw(image)
draw.text(...)
image.save(output, quality=95)
```

## Template

Default project template:

```text
output/septik-expert-kp-template-blank.png
```

The backend should pass template path through config, not hard-code local development paths.

## Layout from current КП scripts

Current working coordinates:

- client: `(129, 394)`
- address: `(390, 394)`
- phone: `(613, 394)`
- date: `(834, 394)`
- materials table: top `516`, bottom `872`
- materials total y: `891`
- works table: top `984`, bottom `1227`
- works total y: `1236`
- grand total y: `1286`
- x lines: `[52, 100, 487, 586, 676, 834, 969]`

## Font

Current scripts use Times New Roman:

```text
/System/Library/Fonts/Supplemental/Times New Roman.ttf
/System/Library/Fonts/Supplemental/Times New Roman Bold.ttf
```

On VPS, configure Times-compatible fonts and pass paths through env/config.

## Layout limits

Recommended MVP limits:

- materials: 12 rows maximum;
- works: 8 rows maximum;
- long item names shrink one step;
- if still too long, return `needs_layout_review=true`.

Do not silently crop important line names or totals.

## Output checks

After rendering:

- file exists;
- file size > 0;
- Pillow can reopen it;
- width/height match template;
- checksum is saved;
- warnings are returned.

## API result

```json
{
  "ok": true,
  "file_type": "proposal_png",
  "local_path": "/app/storage/rendered/proposals/proposal-id.png",
  "width": 1080,
  "height": 1527,
  "sha256": "...",
  "warnings": []
}
```
