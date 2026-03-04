-- Redis Token Bucket (atomic via Lua)
-- KEYS[1] = bucket key
-- ARGV[1] = now_ms (int)
-- ARGV[2] = rate tokens per second (number)
-- ARGV[3] = burst capacity (int)

local key = KEYS[1]
local now_ms = tonumber(ARGV[1])
local rate = tonumber(ARGV[2])
local burst = tonumber(ARGV[3])

-- Hash fields
local TOKENS_F = "tokens"
local TS_F = "ts"

local data = redis.call("HMGET", key, TOKENS_F, TS_F)
local tokens = tonumber(data[1])
local ts = tonumber(data[2])

if tokens == nil then
  tokens = burst
end
if ts == nil then
  ts = now_ms
end

-- refill
local delta_ms = now_ms - ts
if delta_ms < 0 then
  delta_ms = 0
end

local refill = (delta_ms / 1000.0) * rate
tokens = math.min(burst, tokens + refill)
ts = now_ms

local allowed = 0
local retry_after_ms = 0

if tokens >= 1.0 then
  allowed = 1
  tokens = tokens - 1.0
else
  -- need (1 - tokens) tokens, at rate tokens/s => seconds = need/rate
  if rate > 0 then
    local need = 1.0 - tokens
    retry_after_ms = math.ceil((need / rate) * 1000.0)
  else
    retry_after_ms = 1000
  end
end

-- persist
redis.call("HSET", key, TOKENS_F, tokens, TS_F, ts)
-- set TTL to clean up inactive buckets (2*burst/rate seconds, at least 1s)
local ttl_sec = 1
if rate > 0 then
  ttl_sec = math.max(1, math.ceil((burst / rate) * 2))
end
redis.call("EXPIRE", key, ttl_sec)

return {allowed, tokens, retry_after_ms}