import traceback, face_recognition, os, multiprocessing, time
from typing import List, Tuple

from models.device import CameraGroupConnector
from models.video import Video
from models.user import Group, User, UserGroupConnector
from models.analyze import FilesAnalyze, FacesFromUser
from db.connector_sync import SessionSync 
from services.notifier import NotifierService 
from constants.notifications import *

class Analyzer:
    def worker_job(self, batch_size: int = 5, sleep_time: int = 5):
        while True:
            session = SessionSync()
            try:
                tasks = (
                    session.query(FilesAnalyze)
                    .filter_by(analyzed=False, deleted=False)
                    .order_by(FilesAnalyze.recorded_at)
                    .limit(batch_size)
                    .all()
                )
                
                task_ids = [task.id for task in tasks]
                session.close()
                
                if not task_ids:
                    print("Brak zadań")
                    time.sleep(sleep_time)
                    continue
                
                print(f"Znaleziono {len(task_ids)} twarzy do anlizy")
                
                processes = []
                for task_id in task_ids:
                    p = multiprocessing.Process(target=self._process_task, args=(task_id,))
                    p.start()
                    processes.append(p)
                
                # Czekaj na zakończenie wszystkich procesów
                for p in processes:
                    p.join()
                
                
            except Exception as e:
                print(f"{str(e)}")
                traceback.print_exc()
                if 'session' in locals():
                    session.close()
                time.sleep(sleep_time)

    def _load_user_faces_for_camera(self, session: SessionSync, camera_id: int) -> Tuple[List, List]:
        known_encodings = []
        known_metadata = []

        faces_query = (
            session.query(FacesFromUser)
            .join(FacesFromUser.user)
            .join(User.user_group_connectors)
            .join(UserGroupConnector.group)
            .join(Group.cameras_group_connector)
            .filter(
                CameraGroupConnector.camera_id == camera_id,
                FacesFromUser.deleted == False
            )
            .distinct()
            .all()
        )


        for face_record in faces_query:
            if not os.path.exists(face_record.file_path):
                continue

            try:
                image = face_recognition.load_image_file(face_record.file_path)
                encodings = face_recognition.face_encodings(image)

                if encodings:
                    known_encodings.append(encodings[0])
                    known_metadata.append({
                        'user_id': face_record.user_id,
                        'username': face_record.user.username if face_record.user else 'Unknown',
                        'file_path': face_record.file_path,
                        'face_id': face_record.id
                    })
                else:
                    print(f"Nie wykryto twarzy w: {face_record.file_path}")
                    
            except Exception as e:
                print(str(e))

        return known_encodings, known_metadata

    def _process_task(self, task_id: int):
        session = SessionSync()
        try:
            task = session.query(FilesAnalyze).filter_by(id=task_id).first()
            if not task:
                return

            known_encodings, known_metadata = self._load_user_faces_for_camera(
                session, 
                task.camera_id
            )

            if not known_encodings:
                print("Brak zarejestrowanych twarzy dla tej kamery")
                task.analyzed = True
                task.reported = False
                session.commit()
                return

            match_result = self._compare_and_identify(
                known_encodings, 
                known_metadata, 
                task.file_path,
                tolerance=0.6
            )

            task.analyzed = True
            
            if match_result is False:
                task.reported = True
                print("---------------------------------")
                print("             INTRUZ              ")
                print(f"    {task.file_path}")
                self._send_notification(task, VIDEO_TYPE_INTRUDER)
            elif match_result is True:
                task.reported = True
                print("---------------------------------")
                print("          PRZYJACIEL             ")
                print(f"    {task.file_path}")
                self._send_notification(task, VIDEO_TYPE_FRIEND)
            else:
                task.reported = False
                print("Brak rozpoznania")

            session.commit()

            # if os.path.isfile(task.file_path):
            #     os.remove(task.file_path)
            #     print(f"     USUNIETO {task.file_path}      ")
            #     task.deleted = False
            #     session.commit()
        except Exception as e:
            session.rollback()
            print(f"{str(e)}")
            traceback.print_exc()
        finally:
            session.close()

    @staticmethod
    def _compare_and_identify(known_encodings: List, known_metadata: List, unknown_image_path: str, tolerance: float = 0.6) -> bool | None:
        # Zwróć boola dla osoby
        # Zwróć nona dla false positive
        if not os.path.exists(unknown_image_path):
            return None

        try:
            unknown_image = face_recognition.load_image_file(unknown_image_path)
            unknown_encodings = face_recognition.face_encodings(unknown_image)

            if not unknown_encodings:
                print("Nie znaleziono twarzy na zdjęciu do porównania")
                return None

            unknown_encoding = unknown_encodings[0]

            results = face_recognition.compare_faces(
                known_encodings, 
                unknown_encoding, 
                tolerance=tolerance
            )
            distances = face_recognition.face_distance(known_encodings, unknown_encoding)

            if len(distances) > 0:
                best_match_index = distances.argmin()
                
                if results[best_match_index]:
                    match_info = known_metadata[best_match_index]
                    match_info['distance'] = float(distances[best_match_index])
                    match_info['confidence'] = float(1 - distances[best_match_index])
                    
                    print(f"    Rozpoznano: {match_info['username']}")
                    print(f"    Pewność: {match_info['confidence']:.2%}")
                    print(f"    Odległość: {match_info['distance']:.3f}")
                    print(f"    Użytkownik: {match_info['username']} (ID: {match_info['user_id']})")
                    print(f"    Pewność: {match_info['confidence']:.2%}")

                    return True
            
            print("Nei rozpoznano żadnej znanej osoby")
            return False
            
        except Exception as e:
            print(f"{str(e)}")
            return None

    @staticmethod
    def _send_notification(task, message_type):
        notification_tokens = set()
        for camera_group in task.camera.camera_groups:
            group = camera_group.group
            
            for user_group in group.user_group_connectors:
                user = user_group.user
                if user.notification_token and message_type in user.get_allowed_notification_types:
                    notification_tokens.add(user.notification_token)

        if len(notification_tokens):
            message = get_message_by_type(message_type)
            NotifierService().send_multicast(list(notification_tokens), "Powiadomienie o detekcji", message)

Analyzer().worker_job(batch_size=1, sleep_time=10)
