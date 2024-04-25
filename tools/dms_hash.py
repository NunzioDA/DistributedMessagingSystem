import hashlib

def hash_to_range(input_string, range_min, range_max):
    hashed = hashlib.sha256(input_string.encode()).hexdigest()
    hashed_int = int(hashed, 16)

    hash_range = range_max - range_min + 1
    mapped_value = (hashed_int % hash_range) + range_min
    
    return mapped_value
