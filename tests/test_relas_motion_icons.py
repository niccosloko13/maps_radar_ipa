from pathlib import Path
from xml.etree import ElementTree as ET
import unittest

ROOT=Path(__file__).resolve().parents[1]/'app'/'icons'
NAMES=['fixed','signal_radar','red_light','mobile','police','bump','electronic-bump','works','accident','toll','closure','signal']

class TestMotionIcons(unittest.TestCase):
    def test_svg_shapes_are_well_formed_and_renderable(self):
        for name in NAMES:
            with self.subTest(icon=name):
                tree=ET.parse(ROOT/(name+'.svg')).getroot()
                self.assertTrue(tree.tag.endswith('svg'))
                self.assertEqual(tree.attrib.get('viewBox'),'0 0 48 48')
                self.assertGreater(len(list(tree)),0)

if __name__=='__main__':unittest.main()
