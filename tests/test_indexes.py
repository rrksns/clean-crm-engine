"""
MongoDB 인덱스 생성 검증 테스트

인덱스는 앱 시작 시 Beanie가 자동으로 생성합니다.
이 테스트는 인덱스가 올바르게 생성되었는지 확인합니다.
"""
import pytest
from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings
from app.infrastructure.db.connection import connect_to_mongo


@pytest.mark.asyncio
async def test_campaign_indexes_created():
    """CampaignDocument 인덱스가 생성되었는지 확인"""
    await connect_to_mongo()

    client = AsyncIOMotorClient(settings.DATABASE_URL)
    db = client[settings.DATABASE_NAME]

    # Motor에서는 list_indexes() 사용
    cursor = db["campaigns"].list_indexes()
    indexes_list = await cursor.to_list(length=None)

    # 인덱스 이름 목록
    index_names = [idx["name"] for idx in indexes_list]

    # 기본 _id 인덱스는 항상 존재
    assert "_id_" in index_names

    # status + _id 복합 인덱스 확인
    has_compound_index = any(
        "status" in idx["name"] and "_id" in idx["name"]
        for idx in indexes_list
    )

    assert has_compound_index, "status + _id 복합 인덱스가 생성되지 않았습니다"

    client.close()


@pytest.mark.asyncio
async def test_user_event_indexes_created():
    """UserEventDocument 인덱스가 생성되었는지 확인"""
    await connect_to_mongo()

    client = AsyncIOMotorClient(settings.DATABASE_URL)
    db = client[settings.DATABASE_NAME]

    # Motor에서는 list_indexes() 사용
    cursor = db["user_events"].list_indexes()
    indexes_list = await cursor.to_list(length=None)

    # 인덱스 이름 목록
    index_names = [idx["name"] for idx in indexes_list]

    # user_id, event_type, occurred_at 인덱스 확인
    assert any("user_id" in name for name in index_names), "user_id 인덱스 없음"
    assert any("event_type" in name for name in index_names), "event_type 인덱스 없음"
    assert any("occurred_at" in name for name in index_names), "occurred_at 인덱스 없음"

    client.close()


@pytest.mark.asyncio
async def test_crm_message_indexes_created():
    """CrmMessageDocument 인덱스가 생성되었는지 확인"""
    await connect_to_mongo()

    client = AsyncIOMotorClient(settings.DATABASE_URL)
    db = client[settings.DATABASE_NAME]

    # Motor에서는 list_indexes() 사용
    cursor = db["crm_messages"].list_indexes()
    indexes_list = await cursor.to_list(length=None)

    # 인덱스 이름 목록
    index_names = [idx["name"] for idx in indexes_list]

    # user_id, campaign_id, sent_at 인덱스 확인
    assert any("user_id" in name for name in index_names), "user_id 인덱스 없음"
    assert any("campaign_id" in name for name in index_names), "campaign_id 인덱스 없음"
    assert any("sent_at" in name for name in index_names), "sent_at 인덱스 없음"

    client.close()
