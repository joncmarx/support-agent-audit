"""Time-boxed, resumable batch runner. The linked machine kills any command after about three minutes, so
every paid batch runs in chunks: stop submitting new calls after `max_seconds`, write each result the
moment it completes, and let the next chunk pick up what's left."""
import json, time
from concurrent.futures import ThreadPoolExecutor, as_completed


def run_jobs(jobs, fn, out_path, workers=8, max_seconds=110):
    """jobs: list of (key, payload); fn(key, payload) -> record (dict). Returns the number left."""
    t0, n, errors = time.time(), 0, []
    it = iter(jobs)
    with ThreadPoolExecutor(workers) as pool, open(out_path, "a") as f:
        futs = {}

        def submit():
            if time.time() - t0 > max_seconds:
                return
            nxt = next(it, None)
            if nxt is not None:
                futs[pool.submit(fn, *nxt)] = nxt[0]
        for _ in range(workers):
            submit()
        while futs:
            done = next(as_completed(list(futs)))
            key = futs.pop(done)
            try:
                f.write(json.dumps(done.result(), ensure_ascii=False) + "\n"); f.flush(); n += 1
            except Exception as e:  # a crash in our own code, not a model failure (those come back as records)
                errors.append((key, str(e)[:200]))
            submit()
    left = len(jobs) - n
    print(f"{out_path.name}: +{n} this chunk, {left} left, {len(errors)} errors {errors[:3]}")
    return left
