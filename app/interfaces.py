# 기존 코드 아래에 메서드 추가
@abstractmethod
async def add_all(self, campaigns: List[Campaign]) -> bool:
    pass