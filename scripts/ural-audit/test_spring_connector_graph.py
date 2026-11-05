import unittest
import hashlib, tempfile
from pathlib import Path
from unittest.mock import patch
import numpy as np
from affine import Affine
from pyproj import Geod
import rasterio
from rasterio.transform import from_origin
from rasterio.warp import transform_bounds
from shapely.geometry import box
from spring_connector_graph import graph_route, basin_labels


class Identity:
    def transform(self,x,y): return x,y


class SpringConnectorGraphTest(unittest.TestCase):
    def test_basin_labels_real_raster_calls_d8_with_actual_transform(self):
        with tempfile.TemporaryDirectory() as tmp:
            path=Path(tmp)/'dem.tif';tr=from_origin(500000,6500600,30,30)
            data=np.arange(400,dtype='float32').reshape(20,20)
            with rasterio.open(path,'w',driver='GTiff',width=20,height=20,count=1,dtype='float32',crs='EPSG:32640',transform=tr,nodata=-9999) as ds:ds.write(data,1)
            sha=hashlib.sha256(path.read_bytes()).hexdigest()
            bounds=transform_bounds('EPSG:32640','EPSG:4326',500000,6500000,500600,6500600,densify_pts=21)
            with patch('spring_connector_graph.checked_shapes',return_value=[(box(-180,-90,180,90),42)]):
                labels,_,_,_=basin_labels(str(path),sha,None,None,[('unused','unused','unused')],bounds,[42,43,44],30)
            self.assertGreater(int((labels==1).sum()),0)
    def test_connected_interface_uses_geodesic_lengths(self):
        labels=np.array([[1,2],[1,2]],dtype=np.uint8)
        transform=Affine(.001,0,0,0,-.001,.002)
        result=graph_route(labels,transform,Identity(),(.001,.002),(.001,0))
        self.assertEqual(result['component_count'],1)
        self.assertAlmostEqual(result['start_join_m'],0)
        self.assertAlmostEqual(result['end_join_m'],0)
        expected=Geod(ellps='WGS84').inv(.001,.002,.001,0)[2]
        self.assertAlmostEqual(result['divide_length_m'],expected,places=5)

    def test_unknown_cells_do_not_create_an_interface(self):
        with self.assertRaisesRegex(ValueError,'no shared interface'):
            graph_route(np.array([[1,0,2]],dtype=np.uint8),Affine.identity(),Identity(),(0,0),(1,0))


if __name__=='__main__':unittest.main()

