from typing import Dict, List, Optional, Any
import logging
import time
from functools import wraps
from app.exception.global_handler import AppException

# 로깅 설정
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

"""
✅ 서비스 레이어 구현
- Spring의 @Service와 대응되는 개념
- 비즈니스 로직을 담당하는 계층
- 트랜잭션 처리, 데이터 처리 등 핵심 로직 수행

🔍 주요 특징:
- Spring의 @Transactional과 유사한 트랜잭션 데코레이터 구현
- AOP 개념을 데코레이터로 구현 (로깅, 캐싱, 재시도 등)
- 예외 처리 및 변환 담당 (도메인 예외 → HTTP 예외)
"""

# 트랜잭션 데코레이터 (Spring의 @Transactional과 유사)
def transactional(func):
    """
    서비스 메서드에 트랜잭션 기능을 추가하는 데코레이터
    - Spring의 @Transactional과 유사한 역할
    - 함수 실행 전 트랜잭션 시작, 완료 후 커밋, 예외 발생 시 롤백
    
    🔍 현재 구현:
    - 실제 DB 연결 없이 트랜잭션 흐름만 로깅
    - SQLAlchemy 등 ORM 사용 시 실제 트랜잭션 구현 가능
    """
    @wraps(func)
    async def wrapper(*args, **kwargs):
        # 트랜잭션 시작
        logger.info(f"[Transaction] ▶️ 트랜잭션 시작: {func.__name__}")
        start_time = time.time()
        
        try:
            # 함수 실행
            result = await func(*args, **kwargs)
            
            # 트랜잭션 커밋
            execution_time = time.time() - start_time
            logger.info(f"[Transaction] ✅ 트랜잭션 커밋: {func.__name__} - {execution_time:.4f}초")
            return result
            
        except Exception as e:
            # 트랜잭션 롤백
            execution_time = time.time() - start_time
            logger.error(f"[Transaction] ❌ 트랜잭션 롤백: {func.__name__} - {str(e)} - {execution_time:.4f}초")
            raise
    
    return wrapper


# 캐싱 데코레이터 (Spring의 @Cacheable과 유사)
def cacheable(key_prefix: str, ttl_seconds: int = 3600):
    """
    서비스 메서드 결과를 캐싱하는 데코레이터
    - Spring의 @Cacheable과 유사한 역할
    - 동일한 파라미터로 호출 시 캐시된 결과 반환
    
    🔍 현재 구현:
    - 메모리 기반 간단한 캐시 (실제로는 Redis 등 사용 권장)
    - 키 접두사와 함수 인자를 조합하여 캐시 키 생성
    """
    cache = {}
    
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 캐시 키 생성 (접두사 + 인자 해시)
            cache_key = f"{key_prefix}:{hash(str(args) + str(kwargs))}"
            
            # 캐시에 있으면 캐시된 결과 반환
            if cache_key in cache:
                # 캐시 TTL 검사
                entry = cache[cache_key]
                now = time.time()
                if now - entry["timestamp"] < ttl_seconds:
                    logger.info(f"[Cache] 캐시 히트: {cache_key}")
                    return entry["value"]
                else:
                    # TTL 만료된 항목 제거
                    logger.info(f"[Cache] 캐시 만료: {cache_key}")
                    del cache[cache_key]
            
            # 캐시 미스: 원본 함수 실행
            logger.info(f"[Cache] 캐시 미스: {cache_key}")
            result = await func(*args, **kwargs)
            
            # 결과 캐싱
            cache[cache_key] = {
                "value": result,
                "timestamp": time.time()
            }
            logger.info(f"[Cache] 결과 캐싱: {cache_key}")
            
            # 캐시 정리 (실제로는 별도 스케줄러 등 사용)
            now = time.time()
            expired_keys = [k for k, v in cache.items() if now - v["timestamp"] > ttl_seconds]
            for key in expired_keys:
                del cache[key]
            
            return result
        
        return wrapper
    
    return decorator


# 재시도 데코레이터 (Spring Retry와 유사)
def retry(max_attempts: int = 3, delay_seconds: float = 1.0, backoff_factor: float = 2.0):
    """
    실패 시 재시도하는 데코레이터
    - Spring Retry와 유사한 역할
    - 일시적 오류 발생 시 지정된 횟수만큼 재시도
    - 지수 백오프로 재시도 간격 증가 가능
    """
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            attempts = 0
            current_delay = delay_seconds
            
            while attempts < max_attempts:
                try:
                    # 함수 실행
                    return await func(*args, **kwargs)
                    
                except Exception as e:
                    attempts += 1
                    
                    # 마지막 시도까지 실패하면 예외 발생
                    if attempts >= max_attempts:
                        logger.error(f"[Retry] ❌ 최대 재시도 횟수 초과 ({max_attempts}회): {str(e)}")
                        raise
                    
                    # 재시도 로깅
                    logger.warning(f"[Retry] ⚠️ 실패 {attempts}/{max_attempts}, {current_delay:.2f}초 후 재시도: {str(e)}")
                    
                    # 지연 후 재시도
                    await asyncio.sleep(current_delay)
                    
                    # 지수 백오프 (다음 지연 시간 증가)
                    current_delay *= backoff_factor
        
        return wrapper
    
    return decorator


class ExampleService:
    """
    예제 서비스 클래스
    - Spring의 @Service 컴포넌트와 유사
    - 비즈니스 로직 및 트랜잭션 처리 담당
    
    🔍 주요 특징:
    - 데코레이터를 활용한 공통 관심사 분리 (@transactional, @cacheable 등)
    - 비즈니스 예외 처리 및 변환
    - 도메인 로직 캡슐화
    """
    
    def __init__(self):
        """
        서비스 초기화
        - DB 연결, 외부 서비스 클라이언트 등 의존성 주입 가능
        """
        # 가상의 데이터 저장소 (실제로는 DB 연결)
        self._items = {
            "1": {"id": "1", "name": "Product 1", "price": 100},
            "2": {"id": "2", "name": "Product 2", "price": 200},
            "3": {"id": "3", "name": "Product 3", "price": 300},
        }
        logger.info("[ExampleService] 서비스 초기화 완료")
    
    @cacheable(key_prefix="items", ttl_seconds=60)
    async def get_all_items(self) -> List[Dict[str, Any]]:
        """
        모든 아이템 조회 (캐싱 적용)
        - @cacheable 데코레이터로 결과 캐싱 (60초)
        """
        logger.info("[ExampleService] 모든 아이템 조회")
        # DB 조회 시뮬레이션 (지연 추가)
        await asyncio.sleep(0.5)
        return list(self._items.values())
    
    async def get_item_by_id(self, item_id: str) -> Dict[str, Any]:
        """
        ID로 아이템 조회
        - 존재하지 않는 아이템 조회 시 예외 발생
        """
        logger.info(f"[ExampleService] 아이템 조회: id={item_id}")
        
        # 아이템 존재 여부 확인
        if item_id not in self._items:
            logger.warning(f"[ExampleService] 아이템을 찾을 수 없음: id={item_id}")
            raise AppException(
                status_code=404,
                message=f"아이템을 찾을 수 없습니다: {item_id}",
                error_code="ITEM_NOT_FOUND",
                details={"item_id": item_id}
            )
        
        return self._items[item_id]
    
    @transactional
    async def create_item(self, item_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        새 아이템 생성 (트랜잭션 적용)
        - @transactional 데코레이터로 트랜잭션 처리
        - 유효성 검사 및 ID 생성
        """
        logger.info(f"[ExampleService] 아이템 생성: {item_data}")
        
        # 필수 필드 검증
        if "name" not in item_data or "price" not in item_data:
            raise AppException(
                status_code=400,
                message="필수 필드가 누락되었습니다: name, price",
                error_code="INVALID_ITEM_DATA"
            )
        
        # 가격 유효성 검사
        price = item_data.get("price")
        if not isinstance(price, (int, float)) or price <= 0:
            raise AppException(
                status_code=400,
                message="가격은 0보다 커야 합니다",
                error_code="INVALID_PRICE",
                details={"price": price}
            )
        
        # ID 생성 (실제로는 DB의 자동 증가 또는 UUID 사용)
        new_id = str(len(self._items) + 1)
        
        # 아이템 생성
        new_item = {
            "id": new_id,
            "name": item_data["name"],
            "price": price,
            "created_at": time.time()
        }
        
        # DB 저장 시뮬레이션
        await asyncio.sleep(0.3)
        self._items[new_id] = new_item
        
        return new_item
    
    @transactional
    async def update_item(self, item_id: str, item_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        아이템 업데이트 (트랜잭션 적용)
        - 기존 아이템 조회 후 데이터 업데이트
        - 존재하지 않는 아이템 업데이트 시도 시 예외 발생
        """
        logger.info(f"[ExampleService] 아이템 업데이트: id={item_id}, 데이터={item_data}")
        
        # 기존 아이템 조회
        existing_item = await self.get_item_by_id(item_id)
        
        # 업데이트할 필드 적용
        for key, value in item_data.items():
            if key != "id":  # ID는 변경 불가
                existing_item[key] = value
        
        # 업데이트 시간 추가
        existing_item["updated_at"] = time.time()
        
        # DB 업데이트 시뮬레이션
        await asyncio.sleep(0.3)
        self._items[item_id] = existing_item
        
        return existing_item
    
    @transactional
    async def delete_item(self, item_id: str, force: bool = False) -> Dict[str, Any]:
        """
        아이템 삭제 (트랜잭션 적용)
        - force=True 옵션으로 강제 삭제 가능
        - 존재하지 않는 아이템 삭제 시도 시 예외 발생
        """
        logger.info(f"[ExampleService] 아이템 삭제: id={item_id}, force={force}")
        
        # 기존 아이템 조회
        existing_item = await self.get_item_by_id(item_id)
        
        # 추가 삭제 조건 검사 (예: 특정 상태인 경우만 삭제 가능)
        if not force and existing_item.get("special_flag") == True:
            raise AppException(
                status_code=403,
                message="특수 플래그가 설정된 아이템은 강제 삭제만 가능합니다",
                error_code="SPECIAL_ITEM_DELETION",
                details={"item_id": item_id}
            )
        
        # DB 삭제 시뮬레이션
        await asyncio.sleep(0.3)
        deleted_item = self._items.pop(item_id)
        
        return {
            "success": True,
            "deleted_item": deleted_item
        }
    
    @transactional
    async def process_transaction(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """
        복잡한 트랜잭션 처리 예시
        - 여러 단계로 구성된 비즈니스 로직
        - 중간에 예외 발생 시 전체 트랜잭션 롤백
        
        Spring에서 다음과 동등:
        @Transactional
        public TransactionResult processTransaction(TransactionData data) {
            // 복잡한 트랜잭션 로직
        }
        """
        logger.info(f"[ExampleService] 트랜잭션 처리 시작: {data}")
        
        # 1단계: 데이터 검증
        if not data or "operation" not in data:
            raise AppException(
                status_code=400,
                message="잘못된 트랜잭션 데이터: operation 필드가 필요합니다",
                error_code="INVALID_TRANSACTION"
            )
        
        operation = data["operation"]
        result = {"status": "completed", "steps": []}
        
        # 2단계: 첫 번째 작업 수행
        logger.info(f"[ExampleService] 트랜잭션 1단계: 작업={operation}")
        await asyncio.sleep(0.2)
        result["steps"].append("step1")
        
        # 3단계: 두 번째 작업 수행 (의도적 실패 가능)
        if data.get("fail_step2"):
            logger.warning("[ExampleService] 트랜잭션 2단계: 의도적 실패")
            raise AppException(
                status_code=500,
                message="트랜잭션 2단계 실패 (의도적)",
                error_code="TRANSACTION_STEP2_FAILURE"
            )
        
        logger.info("[ExampleService] 트랜잭션 2단계 완료")
        await asyncio.sleep(0.2)
        result["steps"].append("step2")
        
        # 4단계: 최종 작업 수행
        logger.info("[ExampleService] 트랜잭션 최종 단계 완료")
        await asyncio.sleep(0.2)
        result["steps"].append("final")
        result["timestamp"] = time.time()
        
        return result

"""
🔍 추가 활용 옵션:

1. 트랜잭션 전파 속성 구현 (Spring의 @Transactional(propagation=...) 처럼):

def transactional(propagation="REQUIRED"):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 현재 트랜잭션 상태 확인 (스레드 로컬 또는 컨텍스트 활용)
            has_active_tx = is_transaction_active()
            
            # 전파 속성에 따른 처리
            if propagation == "REQUIRED":
                # 있으면 참여, 없으면 생성
                if not has_active_tx:
                    return await start_new_transaction(func, *args, **kwargs)
                else:
                    return await func(*args, **kwargs)
                    
            elif propagation == "REQUIRES_NEW":
                # 항상 새 트랜잭션 (기존 일시 중단)
                if has_active_tx:
                    return await suspend_and_create_new_transaction(func, *args, **kwargs)
                else:
                    return await start_new_transaction(func, *args, **kwargs)
                    
            elif propagation == "NESTED":
                # 중첩 트랜잭션 (부분 롤백 가능)
                if has_active_tx:
                    return await create_nested_transaction(func, *args, **kwargs)
                else:
                    return await start_new_transaction(func, *args, **kwargs)
            
            # 기타 전파 속성 (SUPPORTS, NOT_SUPPORTED, NEVER, MANDATORY 등)
            # ...
        
        return wrapper
    return decorator

2. 격리 레벨 설정 (Spring의 @Transactional(isolation=...) 처럼):

def transactional(isolation="DEFAULT"):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # 격리 레벨에 따른 설정
            if isolation == "READ_UNCOMMITTED":
                # 설정: 더티 리드 허용
                pass
            elif isolation == "READ_COMMITTED":
                # 설정: 커밋된 데이터만 읽음
                pass
            elif isolation == "REPEATABLE_READ":
                # 설정: 같은 트랜잭션 내에서 일관된 읽기
                pass
            elif isolation == "SERIALIZABLE":
                # 설정: 최고 격리 수준
                pass
            
            # 함수 실행
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator

3. 읽기 전용 트랜잭션 (Spring의 @Transactional(readOnly=true) 처럼):

def transactional(read_only=False):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            if read_only:
                # 읽기 전용 설정 (DB에 따라 다름)
                logger.info(f"[Transaction] 읽기 전용 트랜잭션 시작: {func.__name__}")
                # 예: conn.execute("SET TRANSACTION READ ONLY")
            else:
                logger.info(f"[Transaction] 읽기-쓰기 트랜잭션 시작: {func.__name__}")
            
            # 함수 실행
            return await func(*args, **kwargs)
        
        return wrapper
    return decorator

4. 이벤트 발행 (Spring의 이벤트 발행과 유사):

class EventPublisher:
    _subscribers = {}
    
    @classmethod
    def subscribe(cls, event_type, handler):
        if event_type not in cls._subscribers:
            cls._subscribers[event_type] = []
        cls._subscribers[event_type].append(handler)
    
    @classmethod
    async def publish(cls, event_type, event_data):
        logger.info(f"[Event] 이벤트 발행: {event_type}")
        if event_type in cls._subscribers:
            for handler in cls._subscribers[event_type]:
                try:
                    await handler(event_data)
                except Exception as e:
                    logger.error(f"[Event] 이벤트 처리 중 오류: {str(e)}")

# 사용 예시:
async def handle_item_created(item_data):
    logger.info(f"[EventHandler] 아이템 생성됨: {item_data['id']}")

EventPublisher.subscribe("item.created", handle_item_created)

# 서비스 내에서:
await EventPublisher.publish("item.created", new_item)

🔧 흐름 테스트 방법:

1. 트랜잭션 흐름 및 롤백 테스트:
- 정상 케이스: 모든 단계 성공 시 커밋
- 실패 케이스: 중간에 예외 발생 시 롤백
- process_transaction({"operation": "test", "fail_step2": True}) 호출로 롤백 테스트

2. 캐싱 동작 확인:
- 동일 파라미터로 연속 호출 시 두 번째부터는 캐시 히트
- TTL 만료 후 호출 시 캐시 미스 확인
- get_all_items() 연속 호출로 캐싱 테스트

3. 비즈니스 규칙 및 예외 처리 테스트:
- 유효하지 않은 데이터 입력 시 적절한 예외 발생 확인
- 존재하지 않는 리소스 요청 시 404 오류 확인
- update_item("999", {...}) 호출로 없는 아이템 업데이트 테스트
"""