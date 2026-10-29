#!/usr/bin/env python3
"""Place a transparent reference person at a measured, uniformly scaled height."""
import argparse
import base64
import hashlib
import json
import math
from pathlib import Path
import struct

DEFAULT_META = Path(__file__).resolve().parents[1] / 'assets/scale-reference/viewer-standing-left.json'


def layout(metadata, painting_height_cm, painting_height_px, person_height_cm=170,
           baseline_px=0, left_px=0):
    values = [painting_height_cm, painting_height_px, person_height_cm, baseline_px, left_px]
    if not all(math.isfinite(x) for x in values) or min(values[:3]) <= 0:
        raise ValueError('Heights must be positive and all coordinates must be finite.')
    x0, y0, x1, y1 = metadata['visible_bounds_px']
    iw, ih = metadata['image_size_px']
    if not (0 <= x0 < x1 <= iw and 0 <= y0 < y1 <= ih):
        raise ValueError('Visible bounds must lie inside the source image.')
    height = painting_height_px * person_height_cm / painting_height_cm
    factor = height / (y1 - y0)
    return {
        'left_px': left_px, 'top_px': baseline_px - height,
        'width_px': (x1 - x0) * factor, 'height_px': height,
        'baseline_px': baseline_px, 'uniform_scale': factor,
        'view_box': [x0, y0, x1 - x0, y1 - y0],
        'person_height_cm': person_height_cm,
        'painting_height_cm': painting_height_cm,
    }


def svg_document(metadata, png_bytes, geometry):
    if png_bytes[:8] != b'\x89PNG\r\n\x1a\n' or png_bytes[12:16] != b'IHDR':
        raise ValueError('Asset must be a PNG image.')
    size = list(struct.unpack('>II', png_bytes[16:24]))
    if size != metadata['image_size_px']:
        raise ValueError('PNG dimensions differ from the measured metadata.')
    if hashlib.sha256(png_bytes).hexdigest() != metadata['sha256']:
        raise ValueError('PNG changed; inspect and update its visible bounds before use.')
    vb = ' '.join(str(x) for x in geometry['view_box'])
    image_data = base64.b64encode(png_bytes).decode('ascii')
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{geometry["width_px"]:.6f}" '
            f'height="{geometry["height_px"]:.6f}" viewBox="{vb}" '
            'preserveAspectRatio="xMidYMid meet" overflow="hidden">'
            f'<image width="{size[0]}" height="{size[1]}" '
            f'href="data:image/png;base64,{image_data}"/></svg>\n')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--metadata', type=Path, default=DEFAULT_META)
    parser.add_argument('--painting-height-cm', type=float, required=True)
    parser.add_argument('--painting-height-px', type=float, required=True)
    parser.add_argument('--person-height-cm', type=float, default=170)
    parser.add_argument('--baseline-px', type=float, default=0)
    parser.add_argument('--left-px', type=float, default=0)
    parser.add_argument('--output-svg', type=Path)
    args = parser.parse_args()
    metadata = json.loads(args.metadata.read_text(encoding='utf-8'))
    try:
        geometry = layout(metadata, args.painting_height_cm, args.painting_height_px,
                          args.person_height_cm, args.baseline_px, args.left_px)
        if args.output_svg:
            image = args.metadata.parent / metadata['image']
            doc = svg_document(metadata, image.read_bytes(), geometry)
            args.output_svg.parent.mkdir(parents=True, exist_ok=True)
            args.output_svg.write_text(doc, encoding='utf-8')
    except (ValueError, KeyError, OSError) as error:
        parser.error(str(error))
    print(json.dumps(geometry, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
