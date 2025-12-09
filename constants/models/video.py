VIDEO_TYPE_INTRUDER = 'INTR'
VIDEO_TYPE_FRIEND = 'FRND'
VIDEO_TYPE_UNKNOWN = 'UNKN'
VIDEO_TYPE_ANIMAL = 'ANML'

VIDEO_TYPES = (
    (VIDEO_TYPE_INTRUDER, 'Intruder'),
    (VIDEO_TYPE_FRIEND, 'Friend'),
    (VIDEO_TYPE_UNKNOWN, 'Unknown'), # if there is incertanity about recorder type
    (VIDEO_TYPE_ANIMAL, 'Animal') # check if model will be able to detect animals
)
