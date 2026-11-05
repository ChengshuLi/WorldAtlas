# WGS84 sampled-gap research

The diagnostic samples the retained source line and modeled interface, then uses WGS84 inverse geodesic distances to rank sampled point pairs. An initial geodesic pair supplies an upper bound. The ECEF chord between two points is no longer than a surface geodesic, so an ECEF search radius based on that upper bound retains any sampled pair that could improve it. The 1 mm numerical search cushion is an engineering guard, not a formal proof of all floating-point behavior. Final comparisons are WGS84 distances, not chord distances.

This is a sampled estimate, not an exact minimum between continuous lines; the requested sample step is a target rather than a proven maximum spacing. The source and modeled interface remain research inputs and do not establish a surveyed divide. Old fixed-eight candidate results should be treated as historical and rerun, not assumed equivalent.
