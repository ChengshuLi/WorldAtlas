"""Group grid runs without expanding them into individual cells."""

from array import array


class RunComponents:
    """Group connected runs by a common root ID."""

    def __init__(self) -> None:
        """Start without any runs to connect."""
        self.parent = array("I")
        self.size = array("I")

    def add(self) -> int:
        """Add a run as its own connected set.

        Returns:
            New run ID.
        """
        i = len(self.parent)
        # Reaching this limit requires materializing over four billion nodes.
        if i >= 0xFFFFFFFF:  # pragma: no cover
            raise ValueError("too many connected runs for uint32 IDs")
        self.parent.append(i)
        self.size.append(1)
        return i

    def find(self, x: int) -> int:
        """Find the root of a run's connected set.

        Args:
            x: Run ID.

        Returns:
            Current root ID. Shorten the parent chain along the way.
        """
        p = self.parent
        while p[x] != x:
            p[x] = p[p[x]]
            x = p[x]
        return x

    def union(self, a: int, b: int) -> None:
        """Join the connected sets of two runs if they are distinct.

        Args:
            a: ID of the first run.
            b: ID of the second run.
        """
        ra = self.find(a)
        rb = self.find(b)
        if ra == rb:
            return
        if self.size[ra] < self.size[rb]:
            ra, rb = rb, ra
        self.parent[rb] = ra
        self.size[ra] += self.size[rb]
