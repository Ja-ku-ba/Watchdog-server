import datetime
from dateutil import parser

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from sqlalchemy.orm import selectinload, joinedload

from models.user import User
from models.device import Camera, CameraGroupConnector
from models.user import User, Group, UserGroupConnector, UserNotifications
from models.video import Video
from services.notifier import NotifierService


class VideoService:
    def __init__(self, session: AsyncSession, current_user: User|None = None, current_camera: Camera|None = None):
        self._session = session
        self._user = current_user
        self._camera = current_camera

    async def get_videos_for_user(self):
        stmt_cameras = (
            select(Camera)
            .join(CameraGroupConnector, Camera.id == CameraGroupConnector.camera_id)
            .join(Group, CameraGroupConnector.group_id == Group.id)
            .join(UserGroupConnector, Group.id == UserGroupConnector.group_id)
            .join(User, UserGroupConnector.user_id == User.id)
            .filter(User.id == self._user.id)
        )
        result = await self._session.execute(stmt_cameras)
        cameras = result.scalars().all()

        stmt_videos = (
            select(Video)
            .filter(Video.camera_id.in_([camera.id for camera in cameras]))
            .options(selectinload(Video.camera))
            .order_by(Video.recorded_at.desc())
        )

        result = await self._session.execute(stmt_videos)
        videos_for_user = result.scalars().all()
        result = {
            'configured_devices': [
                {
                    'device_ip': camera.device_ip,
                    'device_name': camera.device_name
                # } for camera in [cameras[0]]],
                } for camera in cameras],
            'videos': [
                {
                    'url': f'rtsp://{video.camera.device_ip}:8554/vod/{video.file_path}',
                    'hash': video.hash,
                    'camera': video.camera.device_name,
                    'type': video.type_display,
                    # 'importance_level': video.importance_level,
                    'importance_level': 1,
                    'recorded_at': video.recorded_at.isoformat(),
                    'record_length': f'{video.record_length.total_seconds()}'
                } for video in videos_for_user
            ]
        }

        # result = {
            # 'configured_devices': [],
            # 'videos': []
        # }

        return result

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
            await self.trigger_notification_new_video()
            return True
        except Exception as e:
            print(e)
            return False

    async def trigger_notification_new_video(self):
        stmt_cameras = (
            select(User, UserNotifications)
            .join(UserGroupConnector, User.id == UserGroupConnector.user_id)
            .join(Group, UserGroupConnector.group_id == Group.id)
            .join(CameraGroupConnector, Group.id == CameraGroupConnector.group_id)
            .join(Camera, CameraGroupConnector.camera_id == Camera.id)
            .outerjoin(UserNotifications, UserNotifications.user_id == User.id)
            .where(Camera.id == self._camera.id)
            .distinct()
        )
        
        result = await self._session.execute(stmt_cameras)
        users_with_notifications = result.all()
        
        for user, user_not_stngs in users_with_notifications:
            user_notification_token = user.notification_token
            if user_notification_token:
                if user_not_stngs and user_not_stngs.notification_new_video:
                    NotifierService().send_notification(user_notification_token, "Powiadomienie o detekcji", "Nowe nagranie")
