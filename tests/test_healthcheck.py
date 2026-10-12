from pipeline.healthcheck import SHELL, problems


def test_problems():
    jobs = ["/jobs/a-1", "/jobs/b-2", "/jobs/c-3"]
    pages = {
        "/": (200, "<h1>Home</h1>"),
        "/api/geo": (404, "Page not found"),
        "/jobs/a-1": (200, "<h1>Job</h1>"),
        "/jobs/b-2": (200, f"<div {SHELL}></div>"),
        "/jobs/c-3": (200, "<title>Page not found | HiresHere</title>"),
    }
    fail, warn = problems(pages, jobs)
    assert fail == ["/api/geo: HTTP 404", "/jobs/c-3: shows Page not found"]
    assert warn == ["/jobs/b-2: served by the browser fallback (Pages Functions are off)"]
    assert problems({"/": (200, "ok")}, []) == ([], [])
