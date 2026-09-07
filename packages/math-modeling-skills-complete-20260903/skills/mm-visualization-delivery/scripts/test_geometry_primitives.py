"""Regression of angle direction and nonfinite geometry rejection."""
import unittest
import geometry_diagram_from_spec as g

class GeometryTests(unittest.TestCase):
    def test_negative_quarter_is_small(self):
        path,_,_=g.arc_path(0,0,10,0,-90)
        self.assertIn(' 0 0 0 ',path)
    def test_positive_major_arc(self):
        self.assertIn(' 0 1 1 ',g.arc_path(0,0,10,0,270)[0])
    def test_cross_zero_minor_arc(self):
        self.assertIn(' 0 0 1 ',g.arc_path(0,0,10,350,370)[0])
    def test_degenerate_arcs(self):
        for radius,start,end in [(0,0,90),(-1,0,90),(10,0,0),(10,0,360),(10,0,float('nan'))]:
            with self.subTest(radius=radius,start=start,end=end),self.assertRaises(ValueError):g.arc_path(0,0,radius,start,end)
    def test_invalid_vectors(self):
        for end in [[float('nan'),1],[float('inf'),1],[0,0]]:
            with self.subTest(end=end),self.assertRaises(ValueError):g.render({'canvas':{'width':200,'height':200},'vectors':[{'start':[0,0],'end':end}]})

if __name__=='__main__':unittest.main()
