"""Separate monochrome schematic defaults from vivid quantitative results."""
import copy
import unittest
from xml.etree.ElementTree import fromstring
import geometry_diagram_from_spec as geometry
from cumcm_plot_style import get_palette


class MonochromeTests(unittest.TestCase):
    def spec(self):
        return {"canvas": {"width": 240, "height": 180},
                "style": {"bg_color": "#999999", "ink": "#123456"},
                "regions": [{"x": 0, "y": 0, "width": 50, "height": 100, "fill": "#CCCCCC", "label": "区域"}],
                "polygons": [{"points": [[80, 10], [120, 10], [100, 50]], "fill": "#ABCDEF", "fill_opacity": .2, "hatch": "cross"}],
                "vectors": [{"start": [20, 40], "end": [100, 80], "color": "#FF0000", "label": "力"}],
                "lines": [{"start": [10, 100], "end": [150, 100], "style": "dashed"}],
                "points": [{"xy": [20, 40], "color": "#808080", "label": "A"}]}

    def test_legacy_colors_and_gray_fills_do_not_leak_by_default(self):
        svg = fromstring(geometry.render(self.spec()))
        self.assertEqual(svg.get("data-color-mode"), "monochrome")
        for element in svg.iter():
            for key in ("fill", "stroke"):
                if key in element.attrib:
                    self.assertIn(element.get(key), {"none", "#000000", "#FFFFFF", "url(#hatch-cross)", "url(#hatch-diagonal)"})
            self.assertNotIn("fill-opacity", element.attrib)

    def test_line_and_hatch_distinctions_survive(self):
        svg = geometry.render(self.spec())
        self.assertIn('stroke-dasharray="7,5"', svg)
        self.assertIn('fill="url(#hatch-cross)"', svg)
        self.assertIn('marker-end="url(#arrow-accent)"', svg)

    def test_explicit_historical_color_override(self):
        spec = self.spec()
        spec["style"]["color_mode"] = "color"
        svg = geometry.render(spec)
        self.assertIn('#FF0000', svg)
        self.assertIn('#CCCCCC', svg)
        self.assertIn('data-color-mode="color"', svg)

    def test_color_choice_does_not_change_geometry(self):
        spec = self.spec()
        mono = fromstring(geometry.render(spec))
        color = copy.deepcopy(spec)
        color["style"]["color_mode"] = "color"
        chromatic = fromstring(geometry.render(color))
        keys = {"x", "y", "x1", "x2", "y1", "y2", "cx", "cy", "r", "d", "points", "viewBox", "marker-end"}
        self.assertEqual([{k: v for k, v in node.attrib.items() if k in keys} for node in mono.iter()],
                         [{k: v for k, v in node.attrib.items() if k in keys} for node in chromatic.iter()])

    def test_result_palette_remains_vivid(self):
        expected = ["#2A9D8F", "#E76F51", "#E9C46A", "#457B9D", "#9B5DE5", "#F15BB5"]
        self.assertEqual(get_palette({}), expected)
        self.assertEqual(get_palette({"style_profile": "cumcm-vivid"}), expected)
        self.assertNotEqual(get_palette({}), ["#000000"])

    def test_invalid_color_mode_is_not_guessed(self):
        spec = self.spec()
        spec["style"]["color_mode"] = "grayscale"
        with self.assertRaises(ValueError):
            geometry.render(spec)


if __name__ == "__main__":
    unittest.main(verbosity=2)
