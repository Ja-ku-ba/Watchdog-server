from constants.models.video import *

NOTIFICATION_TYPES = (
    (VIDEO_TYPE_INTRUDER, 'Wykryto intruza'),
    (VIDEO_TYPE_FRIEND, 'Wykryto przyjaciela'),
    (VIDEO_TYPE_UNKNOWN, 'Rozpoczęto nagrywanie'), # if there is incertanity about recorder type
    (VIDEO_TYPE_ANIMAL, 'Wykryto zwierzę') # check if model will be able to detect animals
)

def get_message_by_type(notification_type):
    for e in NOTIFICATION_TYPES:
        if e[0] == notification_type:
            return e[1]
    return ''