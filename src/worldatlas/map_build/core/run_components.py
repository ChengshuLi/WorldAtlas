"""Group grid runs without expanding them into individual cells."""

from array import array


class RunComponents:
    """Group connected runs by a common root ID."""

    def __init__(self) -> None:
        """Start without any runs to connect."""
        self._parents = array("I")
        self._sizes = array("I")

    def __len__(self) -> int:
        """Count the runs tracked by this instance.

        Returns:
            Number of runs added, including runs joined into the same set.
        """
        return len(self._parents)

    def add(self) -> int:
        """Add a run as its own connected set.

        Returns:
            New run ID.
        """
        run_id = len(self._parents)
        # Reaching this limit requires materializing over four billion nodes.
        if run_id >= 0xFFFFFFFF:  # pragma: no cover
            raise ValueError("too many connected runs for uint32 IDs")
        self._parents.append(run_id)
        self._sizes.append(1)
        return run_id

    def find(self, x: int) -> int:
        """Find the root of a run's connected set.

        Args:
            x: Run ID.

        Returns:
            Current root ID. Shorten the parent chain along the way.
        """
        parents = self._parents
        while parents[x] != x:
            parents[x] = parents[parents[x]]
            x = parents[x]
        return x

    def union(self, a: int, b: int) -> None:
        """Join the connected sets of two runs if they are distinct.

        Args:
            a: ID of the first run.
            b: ID of the second run.
        """
        first_root = self.find(a)
        second_root = self.find(b)
        if first_root == second_root:
            return
        if self._sizes[first_root] < self._sizes[second_root]:
            first_root, second_root = second_root, first_root
        # Keep the first root when both groups contain the same number of runs.
        self._parents[second_root] = first_root
        self._sizes[first_root] += self._sizes[second_root]
