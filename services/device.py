from typing import Set
import datetime

from sqlalchemy import select, insert
from sqlalchemy.ext.asyncio import AsyncSession

from models.user import User
from schemas.device import RegisterDevice
from models.device import Camera, CameraGroupConnector
from models.user import User, Group, UserGroupConnector


class DeviceService:
    def __init__(self, session: AsyncSession, current_camera: Camera|None = None):
        self._session = session
        self._camera = current_camera

    async def register_device(self, request_device: RegisterDevice) -> bool:
        try:
            user = await User.get_user_by_email_or_username(
                session=self._session, 
                email=request_device.email
            )
            if not user:
                return False
            
            related_users = await self._get_related_users(user.id)
            existing_group = await self._get_camera_group(self._camera.id)
            if existing_group:
                target_group = existing_group
            else:
                target_group = await self._create_group(request_device.device_name)
                if not target_group:
                    return False
                await self._create_camera_group_connector(self._camera.id, target_group.id)
            await self._add_users_to_group_if_not_exists(target_group.id, related_users)
            await self._propagate_all_cameras_between_users(related_users)
            await self._update_group_cameras_names(target_group, request_device.device_name)
            await self._session.commit()
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
        
    async def _update_group_cameras_names(self, group: Group, device_name: str) -> None:
        stmt = select(CameraGroupConnector).where(
            CameraGroupConnector.group_id == group.id
        )
        result = await self._session.execute(stmt)
        connectors = result.scalars().all()
        
        for connector in connectors:
            camera_stmt = select(Camera).where(Camera.id == connector.camera_id)
            camera_result = await self._session.execute(camera_stmt)
            camera = camera_result.scalar_one_or_none()
            
            if camera:
                camera.name = f'Kamera {device_name}'
                if not camera.activated_at:
                    camera.activated_at = datetime.datetime.now()
        group.name = device_name

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
