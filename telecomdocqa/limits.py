"""Step 8: protecting the public demo's free LLM quota.

Groq's free tier allows about 200,000 tokens a day, and one question uses
about 3,000, so the demo can answer only ~60 new questions a day. Two
simple tools stretch that:

- AnswerCache: the same question (with the same filters) is answered from
  memory instead of calling the LLM again. Visitors often click the same
  example questions, so this saves a lot.
- RateLimiter: each visitor may ask a few new questions per hour, and the
  whole demo has a daily cap, so one visitor can't use up everyone's quota.

Both live in memory: they reset when the server restarts, which is fine
for a demo. A production system would keep them in a shared store such
as Redis so several servers see the same counts.
"""

import time
from collections import OrderedDict, deque
from datetime import datetime, timezone


class AnswerCache:
    """Keeps the most recent answers. When full, the oldest-used one is dropped
    (an "LRU" cache: least recently used)."""

    def __init__(self, max_items=256):
        self.max_items = max_items
        self.items = OrderedDict()

    @staticmethod
    def key(question, filters):
        """Questions that differ only in capitals or spaces count as the same."""
        normalized = " ".join(question.lower().split())
        return (normalized, tuple(sorted((filters or {}).items())))

    def get(self, key):
        if key not in self.items:
            return None
        self.items.move_to_end(key)  # mark as recently used
        return self.items[key]

    def put(self, key, value):
        self.items[key] = value
        self.items.move_to_end(key)
        if len(self.items) > self.max_items:
            self.items.popitem(last=False)  # drop the least recently used


class RateLimiter:
    """At most `per_client_per_hour` new questions per client in any hour,
    and at most `per_day` for the whole service each (UTC) day."""

    def __init__(self, per_client_per_hour, per_day, clock=time.time):
        self.per_client_per_hour = per_client_per_hour
        self.per_day = per_day
        self.clock = clock  # tests pass a fake clock
        self.recent = {}    # client -> timestamps of their recent questions
        self.day = None
        self.today_count = 0

    def check(self, client):
        """Record one question. Returns None if allowed, or a message saying why not."""
        now = self.clock()

        today = datetime.fromtimestamp(now, tz=timezone.utc).date()
        if today != self.day:  # a new day: reset the daily count
            self.day, self.today_count = today, 0
        if self.today_count >= self.per_day:
            return "The demo has reached its daily question limit. Please try again tomorrow."

        times = self.recent.setdefault(client, deque())
        while times and now - times[0] > 3600:  # forget questions older than an hour
            times.popleft()
        if len(times) >= self.per_client_per_hour:
            return f"You can ask {self.per_client_per_hour} new questions per hour. Please try again later."

        times.append(now)
        self.today_count += 1
        return None
