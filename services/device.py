from typing import Set
import datetime

from sqlalchemy import select, insert
from sqlalchemy.ext.asyncio import AsyncSession

from models.user import User
from schemas.user import BaseUniqueUser
from models.device import Camera, CameraGroupConnector
from models.user import User, Group, UserGroupConnector
from models.video import Video


class DeviceService:
    def __init__(self, session: AsyncSession, current_camera: Camera|None = None):
        self._session = session
        self._camera = current_camera

    async def register_device(self, request_user: BaseUniqueUser) -> bool:
        try:
            print('-------------------------------')
            user = await User.get_user_by_email_or_username(
                session=self._session, 
                email=request_user.email
            )
            print(user)
            if not user:
                return False
            
            related_users = await self._get_related_users(user.id)
            print(related_users)
            existing_group = await self._get_camera_group(self._camera.id)
            print(existing_group)
            if existing_group:
                target_group = existing_group
            else:
                group_name = f"Kamera: {datetime.datetime.now().strftime('%d.%m.%Y')}"
                print(group_name)
                # if not group_name:
                    # group_name = f"Kamera {self._camera.device_name}"
                target_group = await self._create_group(group_name)
                print(target_group)
                if not target_group:
                    return False
                print(target_group)
                await self._create_camera_group_connector(self._camera.id, target_group.id)
            print(111)
            await self._add_users_to_group_if_not_exists(target_group.id, related_users)
            print(222)
            await self._propagate_all_cameras_between_users(related_users)
            print(333)
            await self._session.commit()
            print(444)
            return True
            
        except Exception as e:
            await self._session.rollback()
            return False


    async def _get_camera_group(self, camera_id: int) -> Group | None:
        stmt = (
            select(Group)
            .join(CameraGroupConnector, CameraGroupConnector.group_id == Group.id)
            .where(CameraGroupConnector.camera_id == camera_id)
        )

        result = await self._session.execute(stmt)
        group = result.scalar_one_or_none()
        return group


    async def _add_users_to_group_if_not_exists(
        self,
        group_id: int,
        user_ids: Set[int]
    ) -> None:
        existing_users_stmt = (
            select(UserGroupConnector.user_id)
            .where(UserGroupConnector.group_id == group_id)
        )
        result = await self._session.execute(existing_users_stmt)
        existing_user_ids = {row[0] for row in result.all()}
        users_to_add = user_ids - existing_user_ids
        
        if not users_to_add:
            return
        connectors_data = [
            {
                'user_id': user_id,
                'group_id': group_id
            }
            for user_id in users_to_add
        ]
        
        stmt = insert(UserGroupConnector).values(connectors_data)
        await self._session.execute(stmt)
        
    async def _propagate_all_cameras_between_users(self, user_ids: Set[int]) -> None:
        if len(user_ids) <= 1:
            return
        
        all_user_groups = {}
        
        for user_id in user_ids:
            user_groups_stmt = (
                select(UserGroupConnector.group_id)
                .where(UserGroupConnector.user_id == user_id)
                .distinct()
            )
            result = await self._session.execute(user_groups_stmt)
            all_user_groups[user_id] = {row[0] for row in result.all()}
        
        all_groups = set()
        for groups in all_user_groups.values():
            all_groups.update(groups)
        
        if not all_groups:
            return
        
        existing_connectors_stmt = (
            select(
                UserGroupConnector.user_id,
                UserGroupConnector.group_id
            )
            .where(UserGroupConnector.group_id.in_(all_groups))
        )
        result = await self._session.execute(existing_connectors_stmt)
        existing_connectors = {(row[0], row[1]) for row in result.all()}
        
        connectors_to_create = []
        
        for user_id in user_ids:
            for group_id in all_groups:
                if (user_id, group_id) not in existing_connectors:
                    connectors_to_create.append({
                        'user_id': user_id,
                        'group_id': group_id
                    })
        
        if not connectors_to_create:
            return
        
        stmt = insert(UserGroupConnector).values(connectors_to_create)
        await self._session.execute(stmt)
        
            
    async def _get_related_users(self, user_id: int) -> Set[int]:
        user_groups_stmt = (
            select(UserGroupConnector.group_id)
            .where(UserGroupConnector.user_id == user_id)
            .distinct()
        )
        result = await self._session.execute(user_groups_stmt)
        user_group_ids = [row[0] for row in result.all()]
        
        if not user_group_ids:
            return {user_id}
        
        related_users_stmt = (
            select(UserGroupConnector.user_id)
            .where(UserGroupConnector.group_id.in_(user_group_ids))
            .distinct()
        )
        result = await self._session.execute(related_users_stmt)
        related_user_ids = {row[0] for row in result.all()}
        related_user_ids.add(user_id)
        
        return related_user_ids

    async def _create_group(self, group_name: str) -> Group | None:
        try:
            group_stmt = (
                insert(Group)
                .values(name=group_name)
                .returning(Group)
            )
            result = await self._session.execute(group_stmt)
            group = result.scalar_one()
            return group
        except Exception as e:
            return None

    async def _create_camera_group_connector(self, camera_id: int, group_id: int) -> None:
        print(camera_id, group_id)
        stmt = insert(CameraGroupConnector).values(
            camera_id=camera_id,
            group_id=group_id
        )
        await self._session.execute(stmt)
