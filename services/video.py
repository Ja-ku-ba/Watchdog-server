import datetime
from dateutil import parser

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload, joinedload

from models.user import User
from models.device import Camera, CameraGroupConnector
from models.user import User, Group, UserGroupConnector
from models.video import Video


class VideoStramingService:
    def __init__(self, session: AsyncSession):
        self.session = session


class VideoService:
    def __init__(self, session: AsyncSession, current_user: User|None = None, current_camera: Camera|None = None):
        self._session = session
        self._user = current_user
        self._camera = current_camera

    async def get_video_hashes_for_user(self, offset: int = 0, limit: int = 15) -> list[str]:
        stmt = (
            select(
                Video.hash
            )
            .join(Camera, Video.camera_id == Camera.id)
            .join(CameraGroupConnector, Camera.id == CameraGroupConnector.camera_id)
            .join(Group, CameraGroupConnector.group_id == Group.id)
            .join(UserGroupConnector, Group.id == UserGroupConnector.group_id)
            .join(User, UserGroupConnector.user_id == User.id)
            .filter(User.id == self._user.id)
            # .options(selectinload(Video.camera))
            .order_by(Video.recorded_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self._session.execute(stmt)
        return result.scalars().all()

    async def get_videos_for_user(self):
        stmt = (
            select(
                Video
            )
            .join(Camera, Video.camera_id == Camera.id)
            .join(CameraGroupConnector, Camera.id == CameraGroupConnector.camera_id)
            .join(Group, CameraGroupConnector.group_id == Group.id)
            .join(UserGroupConnector, Group.id == UserGroupConnector.group_id)
            .join(User, UserGroupConnector.user_id == User.id)
            .filter(User.id == self._user.id)
            .options(selectinload(Video.camera))  # Optional: preload camera data
        )

        result = await self._session.execute(stmt)
        videos_for_user = result.scalars().all()
        result = []
        for video in videos_for_user:
            result.append({
                'url': f'rtsp://{video.camera.device_ip}:8554/vod/{video.file_path}',
                'hash': video.hash,
                'camera': video.camera.device_name,
                'type': video.type_display,
                # 'importance_level': video.importance_level,
                'importance_level': 1,
                'recorded_at': video.recorded_at.isoformat(),
                'record_length': f'{video.record_length.total_seconds()}'
            })
        return result

    async def get_video_path_for_user(self, hash: str):
        stmt = (
            select(
                Video.file_path,
                Video.thumbnial_file_path,
            )
            .join(Camera, Video.camera_id == Camera.id)
            .join(CameraGroupConnector, Camera.id == CameraGroupConnector.camera_id)
            .join(Group, CameraGroupConnector.group_id == Group.id)
            .join(UserGroupConnector, Group.id == UserGroupConnector.group_id)
            .join(User, UserGroupConnector.user_id == User.id)
            .filter(and_(User.id == self._user.id, Video.hash == hash))
        )
        result = await self._session.execute(stmt)
        file_path = result.one_or_none()
        if file_path:
            video_file_path, thumbnial_file_path = file_path
            return {
                "video": video_file_path,
                "thumbnail": thumbnial_file_path
            }
        else:
            return None

    async def save_info_about_video(self, video_schema):
        try:
            video_schema = video_schema.dict()
            video_schema['record_length'] = datetime.timedelta(seconds=int(video_schema["record_length"]))
            video_schema['camera_id'] = self._camera.id
            video_schema['recorded_at'] = parser.isoparse(video_schema['recorded_at'])
            new_video = Video(**video_schema)
            await new_video.generate_hash(self._session)
            
            new_video.saved_on_server_at = datetime.datetime.now()
            
            self._session.add(new_video)
            await self._session.commit()
            return True
        except Exception as e:
            print(e)
            return False
