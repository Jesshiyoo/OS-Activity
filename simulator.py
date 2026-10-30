"""
Contiguous Memory Allocation Simulator
Strategies: First-Fit, Best-Fit, Worst-Fit
Supports allocation, deallocation, and fragmentation reporting.

Memory model:
 - Memory is a list of fixed regions (the initial holes). The regions are
   separated by memory that is already in use (OS, other programs), so free
   blocks in different regions are never merged with each other.
 - Inside one region, a process is placed at the start of the chosen hole
   and the left-over becomes a smaller hole. When a process ends, its block
   is freed and merged with free neighbours in the same region.
"""

class Block:
    def __init__(self, region, start, size, pid=None):
        self.region, self.start, self.size, self.pid = region, start, size, pid

    @property
    def free(self):
        return self.pid is None


class Memory:
    def __init__(self, holes):
        self.blocks = []
        self.bases = []
        base = 0
        for r, h in enumerate(holes):
            self.blocks.append(Block(r, base, h))
            self.bases.append(base)
            base += h + 1000000  # gap = memory in use by other things
        self.rejected = []
        self.allocated = []
        self.log = []

    def holes(self):
        return [b for b in self.blocks if b.free]

    def pick(self, size, strategy):
        cands = [b for b in self.holes() if b.size >= size]
        if not cands:
            return None
        if strategy == "First-Fit":
            return cands[0]                      # first in address order
        if strategy == "Best-Fit":
            return min(cands, key=lambda b: b.size)   # smallest that fits
        if strategy == "Worst-Fit":
            return max(cands, key=lambda b: b.size)   # largest hole
        raise ValueError(strategy)

    def allocate(self, pid, size, strategy):
        b = self.pick(size, strategy)
        if b is None:
            self.rejected.append(pid)
            self.log.append(f"{pid} ({size} KB) -> REJECTED")
            return False
        i = self.blocks.index(b)
        left = b.size - size
        b.pid, b.size = pid, size
        if left > 0:
            self.blocks.insert(i + 1, Block(b.region, b.start + size, left))
        self.allocated.append(pid)
        self.log.append(f"{pid} ({size} KB) -> region {b.region} at offset "
                        f"{b.start - self.bases[b.region]} KB, leaves {left} KB")
        return True

    def free_process(self, pid):
        for i, b in enumerate(self.blocks):
            if b.pid == pid:
                b.pid = None
                self.log.append(f"{pid} finished -> freed {b.size} KB")
                self._merge()
                return True
        return False

    def _merge(self):
        out = []
        for b in self.blocks:
            if out and out[-1].free and b.free and out[-1].region == b.region:
                out[-1].size += b.size
            else:
                out.append(b)
        self.blocks = out

    def external_fragmentation(self):
        hs = [b.size for b in self.holes()]
        total = sum(hs)
        largest = max(hs) if hs else 0
        pct = 0.0 if total == 0 else (1 - largest / total) * 100
        return total, largest, pct

    def memory_map(self):
        out = []
        for b in self.blocks:
            out.append(("Hole" if b.free else b.pid, b.size, b.region))
        return out


def run(holes, events, strategy):
    mem = Memory(holes)
    for ev in events:
        if ev[0] == "alloc":
            mem.allocate(ev[1], ev[2], strategy)
        else:
            mem.free_process(ev[1])
    return mem


def report(name, mem):
    total, largest, pct = mem.external_fragmentation()
    print(f"=== {name} ===")
    for line in mem.log:
        print("  " + line)
    print("  Allocated:", ", ".join(mem.allocated) or "none")
    print("  Rejected :", ", ".join(mem.rejected) or "none")
    print("  Final memory map (type, size KB, region):")
    for t, s, r in mem.memory_map():
        print(f"    region {r}: {t:<5} {s} KB")
    print(f"  Total free = {total} KB, largest hole = {largest} KB")
    print(f"  External fragmentation = {pct:.1f}%  (1 - largest/total)")
    print("  Internal fragmentation = 0 KB (variable partitions are used)")
    print()


if __name__ == "__main__":
    STRATS = ["First-Fit", "Best-Fit", "Worst-Fit"]

    print("##### TEST 1: Given data #####\n")
    holes = [100, 500, 200, 300, 600]
    events = [("alloc", "P1", 212), ("alloc", "P2", 417), ("alloc", "P3", 112),
              ("alloc", "P4", 426), ("free", "P2"), ("alloc", "P5", 200)]
    for s in STRATS:
        report(s, run(holes, events, s))

    print("##### TEST 2: Scenario where Best-Fit is worse than First-Fit #####\n")
    holes2 = [300, 200]
    events2 = [("alloc", "A", 150), ("alloc", "B", 150), ("alloc", "C", 200)]
    for s in ["First-Fit", "Best-Fit"]:
        report(s, run(holes2, events2, s))
