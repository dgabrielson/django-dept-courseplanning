"""
Iterative maximal singular value matching
"""


class ImsvmRefuse(Exception):
    pass


import numpy as np


def imsvm(rankings, match_all=False, k_threshold=0.85, rank_threshold=None):
    """
    Given a matrix ``rankings`` of people -> section rankings.
    Return a list of (i,j) pairs which indicate the best
    matches.
    Note: This only consitutes a single round, and does
    not handle anything regarding the data; this is strictly
    the numeric calculations.
    """
    results = []
    # A is the row normalized rankings matrix.
    A = rankings - np.mean(rankings, axis=1).reshape(-1, 1)
    fill = min((2 * A.min(), 0))
    row_shape, col_shape = A.shape
    while True:
        if len(results) == min(A.shape):
            break
        U, s, V = np.linalg.svd(A)
        m = s.max()
        s[s < k_threshold * m] = 0
        count = np.count_nonzero(s)
        if count == 0:
            raise ImsvmRefuse("nothing left; too much noise")
        S = np.zeros((U.shape[1], V.shape[0]))
        S[:count, :count] = np.diag(s[:count])
        B = np.dot(np.dot(U, S), V)
        for _ in range(count):
            i, j = np.unravel_index(B.argmax(), B.shape)
            if rank_threshold is not None and A[i, j] < rank_threshold:
                break
            results.append((i, j))
            B[i, :] = fill * np.ones(col_shape)
            B[:, j] = fill * np.ones(row_shape)
            A[i, :] = fill * np.ones(col_shape)
            A[:, j] = fill * np.ones(row_shape)
        if not match_all:
            break
    return results
