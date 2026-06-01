import json
import time

try:
    import redis
except ImportError:  # pragma: no cover
    redis = None


class IntegrationSessionStore:
    def __init__(self, redis_url="", ttl_seconds=1800, key_prefix="hireyo:session:"):
        self.ttl_seconds = max(int(ttl_seconds or 1800), 60)
        self.key_prefix = key_prefix or "hireyo:session:"
        self._memory = {}
        self._redis = self._build_redis_client(redis_url)

    def _build_redis_client(self, redis_url):
        if not redis_url or redis is None:
            return None

        try:
            client = redis.Redis.from_url(redis_url, decode_responses=True)
            client.ping()
            return client
        except Exception:
            return None

    def _key(self, token):
        return f"{self.key_prefix}{token}"

    def get(self, token):
        if self._redis:
            raw = self._redis.get(self._key(token))
            if not raw:
                return None
            try:
                return json.loads(raw)
            except json.JSONDecodeError:
                return None

        item = self._memory.get(token)
        if not item:
            return None
        if item["expires_at"] < time.time():
            del self._memory[token]
            return None
        return item["data"]

    def set(self, token, data):
        if self._redis:
            payload = json.dumps(data, ensure_ascii=True)
            self._redis.setex(self._key(token), self.ttl_seconds, payload)
            return

        self._memory[token] = {
            "data": data,
            "expires_at": time.time() + self.ttl_seconds,
        }
