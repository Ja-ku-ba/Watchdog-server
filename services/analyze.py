import os
import datetime
from dateutil import parser
import shutil

from fastapi import UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from models.analyze import FilesAnalyze, FacesFromUser
from models.device import Camera, CameraGroupConnector
from models.user import User, Group, UserGroupConnector


UPLOAD_DIR = "/home/kuba/Desktop/watchdog_server/storages"
UPLOAD_DIR_UNKNOWN = UPLOAD_DIR + '/to_analyze'
UPLOAD_DIR_KNOWN = UPLOAD_DIR + '/known_users'

os.makedirs(UPLOAD_DIR, exist_ok=True)

class AnalyzeService:

    def __init__(self, session: AsyncSession, camera: Camera):
        self._session = session
        self._camera = camera

    async def save_file_to_analyze(self, file: UploadFile, recorded_at: str):
        try:
            if not file.content_type.startswith("image/"):
                return {"error": "Plik nie jest zdjęciem"}

            reported_at = datetime.datetime.now()
            file_path = os.path.join(UPLOAD_DIR_UNKNOWN, self._camera.camera_uid)
            if not os.path.exists(file_path):
                os.makedirs(file_path)
            file_path = os.path.join(file_path, f'{reported_at}_{file.filename}')
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)

            data = {
                "reported_at": reported_at,
                "recorded_at": parser.isoparse(recorded_at),
                "file_path": file_path,
                "camera_id": self._camera.id
            }
            new_analyze = FilesAnalyze(**data)
            self._session.add(new_analyze)
            await self._session.commit()

            return True
        except Exception as e:
            print(str(e) + '================')
            return False


class PseudoAnalyzeService:

    def __init__(self, session: AsyncSession, user: User):
        self._session = session
        self._user = user

    async def get_cameras_for_user(self) -> list[Camera]:
        stmt = (
            select(Camera)
            .join(CameraGroupConnector, Camera.id == CameraGroupConnector.camera_id)
            .join(Group, CameraGroupConnector.group_id == Group.id)
            .join(UserGroupConnector, Group.id == UserGroupConnector.group_id)
            .filter(UserGroupConnector.user_id == self._user.id)
            .distinct()
        )
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def save_file_to_analyze(self, file: UploadFile):
        try:
            if not file.content_type.startswith("image/"):
                return {"error": "Plik nie jest zdjęciem"}
            
            created_at = datetime.datetime.now()
            file_path = os.path.join(UPLOAD_DIR_UNKNOWN, self._user.username)
            
            if not os.path.exists(file_path):
                os.makedirs(file_path)
            
            file_path = os.path.join(file_path, f'{created_at}_{file.filename}')
            
            with open(file_path, "wb") as buffer:
                shutil.copyfileobj(file.file, buffer)
            
            data = {
                "created_at": created_at,
                "file_path": file_path,
                "user_id": self._user.id
            }
            new_analyze = FacesFromUser(**data)
            self._session.add(new_analyze)
            await self._session.flush()
            
            # user_cameras = await self.get_cameras_for_user()
            
            # for camera in user_cameras:
            #     connector = FacesFromUserCameraConnector(
            #         faces_from_user_id=new_analyze.id,
            #         camera_id=camera.id
            #     )
            #     self._session.add(connector)
            
            await self._session.commit()
            return True
            
        except Exception as e:
            await self._session.rollback()
            print(str(e) + '================')
            return False