import importlib.util
import json
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('scale_reference', ROOT / 'scripts/scale_reference.py')
scale_reference = importlib.util.module_from_spec(spec)
spec.loader.exec_module(scale_reference)


class ScaleReferenceTests(unittest.TestCase):
    def setUp(self):
        self.meta_path = ROOT / 'assets/scale-reference/viewer-standing-left.json'
        self.meta = json.loads(self.meta_path.read_text())

    def test_physical_ratio_and_shared_baseline(self):
        g = scale_reference.layout(self.meta, 188.7, 1000, 170, 1470, 835)
        self.assertAlmostEqual(g['height_px'] / 1000, 170 / 188.7)
        self.assertAlmostEqual(g['top_px'] + g['height_px'], 1470)
        self.assertEqual(g['left_px'], 835)

    def test_ignores_transparent_canvas_padding_and_scales_both_axes(self):
        g = scale_reference.layout(self.meta, 188.7, 1000)
        x0, y0, x1, y1 = self.meta['visible_bounds_px']
        self.assertNotEqual(y1 - y0, self.meta['image_size_px'][1])
        self.assertAlmostEqual(g['width_px'] / (x1 - x0), g['height_px'] / (y1 - y0))

    def test_other_painting_and_reference_height(self):
        g = scale_reference.layout(self.meta, 80, 400, 160, 900)
        self.assertEqual(g['height_px'], 800)
        self.assertEqual(g['top_px'], 100)

    def test_invalid_heights(self):
        for value in [0, -1, float('nan'), float('inf')]:
            with self.subTest(value=value), self.assertRaises(ValueError):
                scale_reference.layout(self.meta, value, 1000)

    def test_embedded_asset_matches_dimensions_hash_and_viewbox(self):
        data = (self.meta_path.parent / self.meta['image']).read_bytes()
        g = scale_reference.layout(self.meta, 188.7, 1000)
        svg = ET.fromstring(scale_reference.svg_document(self.meta, data, g))
        self.assertEqual([float(x) for x in svg.attrib['viewBox'].split()], g['view_box'])
        self.assertTrue(svg[0].attrib['href'].startswith('data:image/png;base64,'))
        with self.assertRaises(ValueError):
            scale_reference.svg_document(self.meta, data + b'changed', g)


if __name__ == '__main__':
    unittest.main()
