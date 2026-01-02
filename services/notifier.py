import firebase_admin
from firebase_admin import credentials, messaging
from typing import List

from utils.env_variables import FIREBASE_CERTIFICATE_PATH

cred = credentials.Certificate(FIREBASE_CERTIFICATE_PATH)
firebase_admin.initialize_app(cred)

class NotifierService:
    def send_notification(self, token: str, title: str, body: str):
        try:
            message = self._get_mesage_body(title, body, token)
            response = messaging.send(message)
            print(f"Wysłano 1 powiadomienie")
            return response
        except Exception as e:
            print(str(e))
            return 

    def send_multicast(self, tokens: List[str], title: str, body: str):
        try:
            messages = [self._get_mesage_body(title, body, token) for token in tokens]

            response = messaging.send_each(messages)
            print(f"Wysłano {response.success_count}/{len(tokens)} powiadomień")
            if response.failure_count > 0:
                print(f"Niepowodzenia: {response.failure_count}")
            return response
        except Exception as e:
            print(str(e))
            return

    @staticmethod
    def _get_mesage_body(title: str, body: str, token: str):
        return messaging.Message(
                notification=messaging.Notification(title=title, body=body),
                android=messaging.AndroidConfig(
                    priority="high",
                    notification=messaging.AndroidNotification(
                        channel_id='watchdog_alerts',
                        default_sound=True,
                        click_action="FLUTTER_NOTIFICATION_CLICK"
                    )
                ),
                token=token
            )


