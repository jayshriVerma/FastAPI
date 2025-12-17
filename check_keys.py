import redis

r = redis.Redis(host="localhost", port=6379, db=0)
print(r.keys())
print(len(r.keys()))
# r.delete(*r.keys())  # delete all keys in the redis database