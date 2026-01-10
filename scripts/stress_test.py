# scripts/stress_test.py
import asyncio
import httpx
import time
import random

# 테스트 설정
API_URL = "http://localhost:8000/api/v1/events"
BATCH_SIZE = 1000

def generate_fake_event(i):
    return {
        "user_id": f"user_{i}",
        "event_type": "add_to_cart",
        "metadata": {"price": random.randint(10000, 100000)}
    }

async def test_single_requests():
    """방식 1: 하나씩 1000번 요청 (기존 방식)"""
    print(f"🐢 [Single] {BATCH_SIZE}건 전송 시작...")
    start_time = time.time()

    async with httpx.AsyncClient() as client:
        for i in range(BATCH_SIZE):
            await client.post(API_URL, json=generate_fake_event(i))

    elapsed = time.time() - start_time
    print(f"   -> 소요 시간: {elapsed:.2f}초")

async def test_batch_request():
    """방식 2: 한 번에 1000개 요청 (Batch 방식)"""
    print(f"🚀 [Batch] {BATCH_SIZE}건 묶음 전송 시작...")
    events = [generate_fake_event(i) for i in range(BATCH_SIZE)]
    start_time = time.time()

    async with httpx.AsyncClient() as client:
        # /batch 엔드포인트 호출
        await client.post(f"{API_URL}/batch", json=events)

    elapsed = time.time() - start_time
    print(f"   -> 소요 시간: {elapsed:.2f}초")

async def main():
    # 서버가 떠있는지 확인
    try:
        async with httpx.AsyncClient() as client:
            await client.get("http://localhost:8000/")
    except:
        print("❌ 서버가 실행되지 않았습니다. Docker나 uvicorn을 먼저 실행해주세요!")
        return

    print("=== 성능 비교 테스트 시작 ===")
    await test_single_requests()
    print("-" * 30)
    await test_batch_request()
    print("===========================")

if __name__ == "__main__":
    asyncio.run(main())