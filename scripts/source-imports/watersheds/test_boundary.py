import unittest

import numpy as np
from shapely.geometry import LineString

from watersheds.boundary import Divide, Join, assemble, connect_waypoints, distance, flow_to_point, geodesic, intersection
from watersheds.terrain import Grid


class BoundaryTests(unittest.TestCase):
    def test_a_shared_catchment_has_no_invented_divide_inside_it(self):
        grid = Grid(np.zeros((3, 3)), (0., .01, 0., .03, 0., -.01), 'EPSG:4326')
        graph = Divide()
        graph.add_grid(grid, {3: np.ones((3, 3), dtype=bool),
                              100: np.ones((3, 3), dtype=bool)}, [(3, 100)])
        self.assertEqual(graph.edges, set())

    def test_shared_catchment_edges_remain_possible_boundary_routes(self):
        grid = Grid(np.zeros((3, 3)), (0., .01, 0., .03, 0., -.01), 'EPSG:4326')
        first = np.tile([True, True, False], (3, 1))
        second = np.tile([False, True, True], (3, 1))
        graph = Divide()
        graph.add_grid(grid, {3: first, 100: second}, [(3, 100)])
        self.assertEqual({a[1] for a, b in graph.edges} | {b[1] for a, b in graph.edges}, {1, 2})
        self.assertTrue(all(a[1] == b[1] for a, b in graph.edges))

    def test_a_third_destination_does_not_invent_an_interface_for_an_unchanged_pair(self):
        grid = Grid(np.zeros((3, 3)), (0., .01, 0., .03, 0., -.01), 'EPSG:4326')
        graph = Divide()
        graph.add_grid(grid, {3: np.ones((3, 3), dtype=bool),
                              100: np.ones((3, 3), dtype=bool),
                              900: np.tile([False, False, True], (3, 1))}, [(3, 100)])
        self.assertEqual(graph.edges, set())

    def test_waypoint_connections_keep_endpoints_and_declared_points(self):
        line = LineString([(i * .001, 0.) for i in range(10)])
        points = [(.002, .0002), (.006, -.0002)]
        result, receipts = connect_waypoints(line, points, 20.)
        coordinates = list(result.coords)
        self.assertEqual(coordinates[0], line.coords[0])
        self.assertEqual(coordinates[-1], line.coords[-1])
        self.assertLess(coordinates.index(points[0]), coordinates.index(points[1]))
        self.assertIn((.004, 0.), coordinates)
        self.assertEqual(len(receipts), 2)
        self.assertTrue(result.is_simple)

    def test_a_waypoint_already_at_a_divide_vertex_keeps_the_line_unchanged(self):
        line = LineString([(0., 0.), (.001, 0.), (.002, 0.)])
        result, receipts = connect_waypoints(line, [(.001, 0.)], 20.)
        self.assertEqual(list(result.coords), list(line.coords))
        self.assertEqual(receipts[0]['length_m'], 0.)

    def test_overlapping_waypoint_connections_keep_both_points_in_order(self):
        line = LineString([(i * .001, 0.) for i in range(6)])
        points = [(.0022, .0001), (.0028, .0002)]
        result, receipts = connect_waypoints(line, points, 20.)
        coordinates = list(result.coords)
        self.assertLess(coordinates.index(points[0]), coordinates.index(points[1]))
        self.assertEqual(len(receipts), 1)
        self.assertTrue(result.is_simple)

    def test_attachments_expand_to_enclose_crossings_of_the_source_route(self):
        line = LineString([(0., 0.), (.004, 0.), (.004, .004), (0., .004),
                           (0., .002), (.003, .002), (.003, .001), (.001, .001)])
        point = (.002, -.0001)
        result, receipts = connect_waypoints(line, [point], 20.)
        self.assertTrue(result.is_simple)
        self.assertIn(point, result.coords)
        self.assertEqual(receipts[0]['start'], [0., 0.])
        self.assertEqual(result.coords[-1], line.coords[-1])

    def test_out_of_order_or_invalid_waypoints_are_reported(self):
        line = LineString([(i * .001, 0.) for i in range(6)])
        with self.assertRaisesRegex(ValueError, 'ordered divide'):
            connect_waypoints(line, [(.004, .0001), (.001, .0001)], 20.)
        with self.assertRaisesRegex(ValueError, 'finite WGS84'):
            connect_waypoints(line, [(0., 91.)], 20.)
        with self.assertRaisesRegex(ValueError, 'positive geodesic'):
            connect_waypoints(line, [(.002, .0001)], 0.)

    def test_waypoint_cannot_double_back_beyond_a_fixed_boundary_endpoint(self):
        line = LineString([(0., 0.), (.001, 0.), (.002, 0.)])
        with self.assertRaisesRegex(ValueError, 'simple ordered line'):
            connect_waypoints(line, [(.004, 0.)], 20.)

    def graph(self):
        graph = Divide()
        graph.coordinates = {(0, 0): (0., 0.), (0, 1): (.01, 0.),
                             (0, 2): (.02, 0.), (1, 1): (.01, .01),
                             (1, 2): (.02, .01)}
        graph.edges = {((0, 0), (0, 1)), ((0, 1), (0, 2)),
                       ((0, 1), (1, 1)), ((1, 1), (1, 2)), ((0, 2), (1, 2))}
        return graph

    def test_connected_pieces_and_loop_are_routed_between_actual_joins(self):
        graph = self.graph()
        first = intersection(graph, LineString([(0., -.01), (0., .01)]), (0., 0.))
        last = intersection(graph, LineString([(.02, -.01), (.02, .02)]), (.02, 0.))
        route = graph.route(first, last)
        self.assertEqual(list(route.coords), [(0., 0.), (.01, 0.), (.02, 0.)])

    def test_two_fractional_joins_on_the_same_reversed_edge(self):
        graph = Divide()
        graph.coordinates = {(0, 0): (.01, 0.), (0, 1): (0., 0.)}
        graph.edges = {((0, 0), (0, 1))}
        first = intersection(graph, LineString([(.007, -.01), (.007, .01)]), (.007, 0.))
        last = intersection(graph, LineString([(.002, -.01), (.002, .01)]), (.002, 0.))
        self.assertEqual(list(graph.route(first, last).coords), [(.007, 0.), (.002, 0.)])

    def test_disconnected_divide_is_not_joined_with_an_invented_segment(self):
        graph = self.graph()
        graph.coordinates[(3, 0)], graph.coordinates[(3, 1)] = (.03, 0.), (.04, 0.)
        graph.edges.add(((3, 0), (3, 1)))
        first = Join((0., 0.), {graph: ((0, 0), (0, 1))})
        last = Join((.04, 0.), {graph: ((3, 0), (3, 1))})
        with self.assertRaisesRegex(ValueError, 'disconnected'):
            graph.route(first, last)

    def test_connector_selection_uses_native_vertices_without_coordinate_rounding(self):
        graph = self.graph()
        join = graph.nearest_vertex((.01001, .00999))
        self.assertEqual(join.point, graph.coordinates[(1, 1)])
        self.assertIn((1, 1), join.edges[graph])

    def test_native_overlapping_domains_share_the_same_grid_edges(self):
        origin = (0., .01, 0., .03, 0., -.01)
        first = Grid(np.zeros((2, 2)), origin, 'EPSG:4326', native_origin=origin)
        second = Grid(np.zeros((2, 2)), (0., .01, 0., .02, 0., -.01),
                      'EPSG:4326', native_origin=origin, window_offset=(1, 0))
        graph = Divide()
        for grid in (first, second):
            graph.add_grid(grid, {group: np.tile([group == 1, group == 3], (2, 1)) for group in (1, 3)}, [(1, 3)])
        self.assertEqual(len(graph.edges), 3)
        self.assertEqual(len(graph.coordinates), 4)

    def test_unknown_is_not_used_as_an_opposing_basin(self):
        grid = Grid(np.zeros((2, 2)), (0., .01, 0., .03, 0., -.01), 'EPSG:4326')
        graph = Divide()
        graph.add_grid(grid, {1: np.tile([True, False], (2, 1))}, [(1, 3)])
        self.assertEqual(graph.edges, set())

    def test_context_cells_influence_flow_but_do_not_add_overlapping_output_edges(self):
        grid = Grid(np.zeros((4, 2)), (0., .01, 0., .04, 0., -.01), 'EPSG:4326')
        labels = np.tile([1, 3], (4, 1))
        graph = Divide()
        graph.add_grid(grid, {group: labels == group for group in (1, 3)}, [(1, 3)], output_bounds=[0., .01, .02, .03])
        self.assertEqual(len(graph.edges), 2)
        np.testing.assert_allclose(sorted(graph.coordinates.values()),
                                   [(.01, .01), (.01, .02), (.01, .03)])

    def test_projected_output_areas_partition_one_connected_native_divide(self):
        grid = Grid(np.zeros((4, 2)), (2249900., 2., 0., 900100., 0., -2.), 'EPSG:3413')
        labels = np.tile([1, 3], (4, 1))
        complete, partitioned = Divide(), Divide()
        complete.add_grid(grid, {group: labels == group for group in (1, 3)}, [(1, 3)])
        for bounds in ([2249900, 900092, 2249904, 900096],
                       [2249900, 900096, 2249904, 900100]):
            partitioned.add_grid(grid, {group: labels == group for group in (1, 3)}, [(1, 3)], bounds, bounds_crs=3413)
        self.assertEqual(partitioned.edges, complete.edges)
        self.assertEqual(partitioned.coordinates, complete.coordinates)
        route = partitioned.route(partitioned.nearest_vertex(complete.coordinates[(0, 1)]),
                                  partitioned.nearest_vertex(complete.coordinates[(4, 1)]))
        self.assertTrue(route.is_simple)

    def test_final_assembly_preserves_endpoints_and_has_shared_joins(self):
        graph = self.graph()
        before = LineString([(-.01, -.01), (0., 0.), (0., .01)])
        after = LineString([(.02, -.01), (.02, 0.), (.03, .01)])
        joins = [intersection(before, graph, (0., 0.)), intersection(graph, after, (.02, 0.))]
        geometry = assemble([before, graph, after], joins, (-.01, -.01), (.03, .01))
        self.assertEqual(geometry['coordinates'][0], [-.01, -.01])
        self.assertEqual(geometry['coordinates'][-1], [.03, .01])
        self.assertEqual(geometry['coordinates'].count([0., 0.]), 1)
        self.assertTrue(LineString(geometry['coordinates']).is_simple)

    def test_repeated_source_coordinates_do_not_create_zero_length_output_segments(self):
        source = LineString([(0., 0.), (.01, 0.), (.01, 0.), (.02, .01)])
        geometry = assemble([source], [], (0., 0.), (.02, .01))
        self.assertEqual(geometry['coordinates'], [[0., 0.], [.01, 0.], [.02, .01]])
        self.assertTrue(LineString(geometry['coordinates']).equals(source))

    def test_source_line_can_be_cut_at_an_actual_interior_endpoint(self):
        source = LineString([(0., 0.), (.01, 0.), (.02, 0.)])
        geometry = assemble([source], [], (.005, 0.), (.015, 0.))
        self.assertEqual(geometry['coordinates'], [[.005, 0.], [.01, 0.], [.015, 0.]])

    def test_invalid_latitude_and_uncut_longitude_discontinuity_are_rejected(self):
        for points in [[(0., 91.), (1., 89.)], [(179., 0.), (-179., 1.)]]:
            with self.subTest(points=points), self.assertRaisesRegex(ValueError, 'WGS84 line'):
                assemble([LineString(points)], [], points[0], points[-1])

    def test_explicit_geodesic_connector_has_no_old_length_requirement(self):
        for endpoint in [(44.0001, 43.), (44.1, 43.)]:
            points = geodesic((44., 43.), endpoint, 20.)
            self.assertEqual(points[0], (44., 43.))
            self.assertEqual(points[-1], endpoint)
            self.assertTrue(all(distance(a, b) <= 20.000001 for a, b in zip(points, points[1:])))

    def test_missing_source_intersection_is_reported(self):
        with self.assertRaisesRegex(ValueError, 'no source-supported intersection'):
            intersection(LineString([(0, 0), (1, 0)]), LineString([(0, 1), (1, 1)]), (.5, .5))

    def test_stream_head_connection_is_built_directly_from_flow_and_exact_source_point(self):
        grid = Grid(np.zeros((3, 3)), (44., .001, 0., 43., 0., -.001), 'EPSG:4326')
        labels = np.array([[1, 2, 2], [1, 2, 2], [1, 2, 2]])
        flow = np.full((3, 3), -1)
        flow.ravel()[[1, 4, 7]] = [4, 7, 8]
        point = (44.00251, 42.99751)
        curve, report = flow_to_point(grid, flow, labels, point, 2, [1], .5)
        self.assertEqual(tuple(curve.coords[-1]), point)
        self.assertEqual(report['flow_cells'], 2)
        self.assertGreater(report['point_snap_m'], 0)
        divide = Divide()
        divide.add_grid(grid, {group: labels == group for group in (1, 2)}, [(1, 2)])
        join = intersection(divide, curve, point)
        self.assertAlmostEqual(join.point[0], 44.001)

    def test_head_connection_does_not_guess_a_route_when_no_upstream_divide_exists(self):
        grid = Grid(np.zeros((3, 3)), (44., .001, 0., 43., 0., -.001), 'EPSG:4326')
        labels = np.full((3, 3), 2)
        with self.assertRaisesRegex(ValueError, 'no source-backed divide'):
            flow_to_point(grid, np.full((3, 3), -1), labels, (44.0015, 42.9985), 2, [1], 1.)

    def test_source_point_cell_need_not_be_traversed_by_raster_flow(self):
        grid = Grid(np.zeros((3, 3)), (44., .001, 0., 43., 0., -.001), 'EPSG:4326')
        labels = np.array([[1, 2, 2], [1, 2, 2], [1, 2, 2]])
        flow = np.full((3, 3), -1)
        flow.ravel()[[1, 4]] = [4, 7]
        point = (44.0025, 42.9975)
        curve, receipt = flow_to_point(grid, flow, labels, point, 2, [1], 1.)
        self.assertEqual(tuple(curve.coords[-1]), point)
        self.assertGreater(receipt['point_snap_m'], 0)
        self.assertEqual(receipt['flow_cells'], 1)


if __name__ == '__main__':
    unittest.main()
