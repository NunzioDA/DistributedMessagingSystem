# Creato da Nunzio D'Amore

import hashlib


## Effettua l'hash di una stringa in un range prestabilito con SHA256
## se range_2 non viene assegnato range_1 sarà il limite massimo
## e il minimo 0.
## Altrimenti range_2 sarà il massimo e range_1 il minimo
##
## Il range massimo non è compreso
def hash_to_range(input_string, range_1, range_2 = None):

    if(range_2 is None):
        range_max = range_1
        range_min = 0
    else:
        range_min =range_1
        range_max =range_2

    hashed = hashlib.sha256(input_string.encode()).hexdigest()
    hashed = hashlib.sha256(hashed.encode()).hexdigest()
    
    hashed_int = int(hashed, 16)

    hash_range = range_max - range_min
    mapped_value = (hashed_int % hash_range) + range_min
    
    return mapped_value
