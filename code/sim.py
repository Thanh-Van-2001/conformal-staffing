"""Trace-driven simulation of an EMS unit pool as an M_t/G/c_t FCFS queue,
and sample-average-approximation (SAA) staffing optimisation.

Model. Calls arrive at times a_1 <= a_2 <= ... within an operational day
(hours since 04:00). Each call needs one unit for S_i hours. The number of
units on duty is c_p in hour p = 0..P-1 (c_p >= 1, held at c_{P-1} after the
day ends until the queue clears). Calls are served first come, first served;
a unit that is busy when its shift ends finishes its call (no pre-emption).

Daily cost = L * sum_p c_p  +  w * sum_i W_i, where W_i is the wait of call i
in hours and w is the cost of one hour of waiting in unit-hours.
"""
import numpy as np
from numba import njit


@njit(cache=True)
def _push(heap, hs, x):
    i = hs
    heap[i] = x
    while i > 0:
        par = (i - 1) // 2
        if heap[par] <= heap[i]:
            break
        tmp = heap[par]
        heap[par] = heap[i]
        heap[i] = tmp
        i = par
    return hs + 1


@njit(cache=True)
def _pop(heap, hs):
    hs -= 1
    heap[0] = heap[hs]
    i = 0
    while True:
        l = 2 * i + 1
        r = l + 1
        m = i
        if l < hs and heap[l] < heap[m]:
            m = l
        if r < hs and heap[r] < heap[m]:
            m = r
        if m == i:
            break
        tmp = heap[m]
        heap[m] = heap[i]
        heap[i] = tmp
        i = m
    return hs


@njit(cache=True)
def sim_day(arr, svc, c, L):
    """Return (total wait in hours, number of calls that waited > 0,
    number that waited > 10 minutes) for one day."""
    n = arr.shape[0]
    P = c.shape[0]
    heap = np.empty(n + 1)
    hs = 0
    tot = 0.0
    nw = 0
    nw10 = 0
    last = 0.0
    for i in range(n):
        s = arr[i] if arr[i] > last else last
        while True:
            while hs > 0 and heap[0] <= s:
                hs = _pop(heap, hs)
            p = int(s // L)
            cap = c[p] if p < P else c[P - 1]
            if hs < cap:
                break
            nxt = heap[0]
            q = p + 1
            moved = False
            while q < P and q * L < nxt:
                if c[q] > hs:
                    s = q * L
                    moved = True
                    break
                q += 1
            if not moved:
                s = nxt
        wt = s - arr[i]
        tot += wt
        if wt > 1e-12:
            nw += 1
        if wt > 10.0 / 60.0:
            nw10 += 1
        hs = _push(heap, hs, s + svc[i])
        last = s
    return tot, nw, nw10


@njit(cache=True)
def mean_wait(arr, svc, off, c, L):
    D = off.shape[0] - 1
    tot = 0.0
    for d in range(D):
        a = off[d]
        b = off[d + 1]
        tw, _, _ = sim_day(arr[a:b], svc[a:b], c, L)
        tot += tw
    return tot / D


@njit(cache=True)
def per_day_stats(arr, svc, off, c, L):
    D = off.shape[0] - 1
    out = np.empty((D, 4))
    for d in range(D):
        a = off[d]
        b = off[d + 1]
        tw, nw, nw10 = sim_day(arr[a:b], svc[a:b], c, L)
        out[d, 0] = tw
        out[d, 1] = nw
        out[d, 2] = nw10
        out[d, 3] = b - a
    return out


@njit(cache=True)
def busy_profile(arr, svc, off, P, L):
    """Mean number of calls in service (infinite-server) at each hour midpoint."""
    D = off.shape[0] - 1
    m = np.zeros(P)
    for d in range(D):
        for i in range(off[d], off[d + 1]):
            a = arr[i]
            e = a + svc[i]
            for p in range(P):
                t = (p + 0.5) * L
                if a <= t < e:
                    m[p] += 1.0
    return m / D


def daily_cost(arr, svc, off, c, L, w):
    return L * float(np.sum(c)) + w * mean_wait(arr, svc, off, c, L)


def sqrt_start(arr, svc, off, P, L, beta=0.5):
    m = busy_profile(arr, svc, off, P, L)
    return np.maximum(1, np.ceil(m + beta * np.sqrt(m))).astype(np.int64)


def optimise(arr, svc, off, L, w, c0, max_sweeps=50):
    """Coordinate descent over integer staffing levels with common random
    numbers (the sampled days are fixed across all candidate plans)."""
    c = np.asarray(c0, dtype=np.int64).copy()
    best = daily_cost(arr, svc, off, c, L, w)
    n_eval = 1
    for _ in range(max_sweeps):
        improved = False
        for t in range(c.shape[0]):
            for d in (-1, 1):
                while c[t] + d >= 1:
                    c[t] += d
                    v = daily_cost(arr, svc, off, c, L, w)
                    n_eval += 1
                    if v < best - 1e-9:
                        best = v
                        improved = True
                    else:
                        c[t] -= d
                        break
        if not improved:
            break
    return c, best, n_eval


def optimise_multistart(arr, svc, off, L, w, starts):
    best_c, best_v = None, np.inf
    for c0 in starts:
        c, v, _ = optimise(arr, svc, off, L, w, c0)
        if v < best_v:
            best_c, best_v = c, v
    return best_c, best_v
