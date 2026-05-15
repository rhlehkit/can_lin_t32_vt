# LIN TX/RX Without System Variables

이 샘플은 CANoe namespace system variables를 프레임 전달 경로로 쓰지 않고, Python Test Unit이 CAPL bridge 함수를 호출하는 구조입니다.

## 왜 이 방식이 더 나은가

System variable 방식은 smoke test에는 쉽지만, LIN RX가 빠르게 여러 개 들어오거나 TX 요청이 연속으로 들어오면 변수 덮어쓰기, 순서 보존, overflow 처리 때문에 구조가 금방 커집니다.

CAPL bridge 방식은 저수준 LIN 처리를 CANoe 안에 그대로 두는 구조라서 더 자연스럽습니다.

- LIN frame 송신은 CAPL에서 `output()`, schedule table, LDF frame object로 처리
- LIN frame 수신은 CAPL `on linFrame ...` 또는 Test Feature Set wait 함수로 처리
- RX queue, timeout, timestamp, filtering은 CAPL 내부 메모리로 처리
- Python은 `send`, `wait`, `get byte`, `assert` 같은 테스트 레벨 로직만 담당

## 파일

- `lin_capl_bridge_test.py`: Python Test Unit 테스트 케이스
- `lin_bridge.can`: Python이 호출할 CAPL exported function 계약/템플릿
- `lin_capl_bridge.vtestunit.yaml`: Test Unit 설명 파일
- `lin_capl_bridge.vtesttree.yaml`: Test tree

## Python이 기대하는 CAPL 함수

`lin_capl_bridge_test.py`는 아래 CAPL 함수들이 있다고 가정합니다.

```capl
export long LinBridge_Reset();
export long LinBridge_SendFrame(long frameId, long dlc, long b0, long b1, long b2, long b3, long b4, long b5, long b6, long b7);
export long LinBridge_RequestSlaveResponse(long frameId);
export long LinBridge_WaitForFrame(long frameId, long timeoutMs);
export long LinBridge_GetLastRxId();
export long LinBridge_GetLastRxDlc();
export long LinBridge_GetLastRxByte(long index);
```

반환값은 `0 = OK`, `0이 아닌 값 = 실패`로 두면 Python 쪽에서 단순하게 판정할 수 있습니다.

## 실제 프로젝트에서 수정할 부분

`lin_bridge.can`은 프로젝트 템플릿입니다. 아래 부분은 실제 CANoe/LDF 구성에 맞춰 바꿔야 합니다.

- `LIN_CHANNEL`
- `linmessage` 대신 LDF 기반 named `linFrame` object 사용 여부
- master request인지, slave response header 요청인지
- `LinBridge_WaitForFrame()` 내부의 RX 데이터 저장 방식
- 여러 RX를 보존해야 하면 CAPL 내부 ring buffer 추가

특히 RX는 system variable보다 CAPL 내부 queue가 더 좋습니다. Python이 매 polling마다 값을 읽는 방식이 아니라, CAPL이 bus event를 즉시 받아 queue에 넣고 Python은 함수 호출로 꺼내 가는 구조가 됩니다.

## Generated type library 권장

현재 Python 샘플의 `CaplBridge` 클래스는 빠른 bring-up을 위해 CANoe COM의 `CAPL.GetFunction(...).Call(...)`을 사용합니다.

CANoe/vTESTstudio Test Unit에서 장기적으로 쓰려면 Vector Test Unit 확장의 `Generate Python type libraries` 기능으로 CAPL exported function을 Python에서 직접 호출하는 방식이 더 좋습니다. 그 경우 `CaplBridge` 클래스 내부만 생성된 API 호출로 바꾸면 테스트 케이스 본문은 그대로 유지할 수 있습니다.

## CANoe에 넣는 방법

1. `lin_bridge.can`을 프로젝트 LIN 설정에 맞게 완성합니다.
2. CANoe Test Configuration에서 `lin_capl_bridge.vtestunit.yaml`을 추가합니다.
3. VS Code의 Vector Test Unit 확장에서 active test unit을 선택합니다.
4. 필요하면 `Generate Python type libraries`를 실행합니다.
5. Test Configuration에서 `LinTxRx_CaplBridgeTest`를 실행합니다.

