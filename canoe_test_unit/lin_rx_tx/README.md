# CANoe/vTESTstudio LIN TX/RX Python Test Unit

이 폴더는 CANoe/vTESTstudio Test Unit에서 Python 테스트 케이스를 호출하는 최소 샘플입니다.

## 파일

- `lin_rx_tx_test.py`: Python 테스트 케이스 본문
- `lin_rx_tx.vtestunit.yaml`: Test Unit 설명 파일
- `lin_rx_tx.vtesttree.yaml`: 실행할 테스트 케이스 순서

## 실행 흐름

1. Python Test Unit이 `LinTxRx_SmokeTest`를 실행합니다.
2. 테스트가 CANoe system variable `LinTest::Tx*`에 LIN TX 요청을 씁니다.
3. CANoe simulation node, CAPL helper, 또는 기존 테스트 환경이 이 요청을 실제 LIN 송신으로 변환합니다.
4. LIN RX monitor 쪽이 수신 프레임을 `LinTest::Rx*` system variable에 업데이트합니다.
5. Python Test Unit이 TX 완료와 RX 데이터 일치를 판정합니다.

## 필요한 CANoe system variables

아래 namespace와 변수들을 CANoe configuration에 만들어 주세요.

Namespace: `LinTest`

| Variable | Type 예시 | Direction | 의미 |
| --- | --- | --- | --- |
| `TxId` | Integer | Python to CANoe | 송신할 LIN frame ID |
| `TxDlc` | Integer | Python to CANoe | 송신 payload 길이 |
| `TxData0` ... `TxData7` | Integer | Python to CANoe | 송신 payload byte |
| `TxRequestCounter` | Integer | Python to CANoe | 값이 증가하면 CANoe 쪽 bridge가 송신 수행 |
| `TxDoneCounter` | Integer | CANoe to Python | 송신 완료 시 증가 |
| `TxStatus` | Integer | CANoe to Python | `0`이면 정상, 그 외는 실패 |
| `RxCounter` | Integer | CANoe to Python | LIN frame 수신 시 증가 |
| `RxId` | Integer | CANoe to Python | 마지막 수신 LIN frame ID |
| `RxDlc` | Integer | CANoe to Python | 마지막 수신 payload 길이 |
| `RxData0` ... `RxData7` | Integer | CANoe to Python | 마지막 수신 payload byte |

## CANoe 쪽 bridge가 해야 할 일

CANoe/CAPL/simulation node 쪽에는 다음 로직이 필요합니다.

```text
on LinTest::TxRequestCounter changed:
  read LinTest::TxId, TxDlc, TxData0..TxData7
  send LIN frame on the configured LIN channel
  set LinTest::TxStatus = 0 on success, non-zero on failure
  increment LinTest::TxDoneCounter

on LIN frame received:
  write received ID to LinTest::RxId
  write received DLC to LinTest::RxDlc
  write received payload to LinTest::RxData0..RxData7
  increment LinTest::RxCounter
```

이 bridge는 프로젝트에 이미 있는 CAPL 노드, LIN simulation node, 또는 VT System 테스트 setup에서 구현하면 됩니다. 중요한 점은 Python이 VN16xx 채널을 직접 열지 않고, CANoe가 소유한 LIN/VT 환경을 system variable 계약으로 제어한다는 것입니다.

## 샘플 값 변경 위치

`lin_rx_tx_test.py` 상단의 값을 프로젝트에 맞게 수정합니다.

```python
TX_FRAME_ID = 0x12
TX_FRAME_DATA = (0x10, 0x22, 0x33, 0x44)

EXPECTED_RX_FRAME_ID = 0x22
EXPECTED_RX_FRAME_DATA = (0x55, 0xAA, 0x12, 0x34)
```

## CANoe/vTESTstudio에 넣는 방법

1. CANoe Test Configuration에서 Test Unit을 추가합니다.
2. `lin_rx_tx.vtestunit.yaml`을 선택합니다.
3. VS Code에서 Vector Test Unit 확장으로 열어 Python test case가 export되는지 확인합니다.
4. CANoe measurement를 시작하고 Test Configuration에서 Test Unit을 실행합니다.
5. 실패하면 먼저 `LinTest` system variable 값들이 증가/갱신되는지 확인합니다.

## pywin32 관련 메모

샘플의 `SystemVariables` 클래스는 CANoe COM API를 통해 system variable을 읽고 씁니다. CANoe Python 런타임에 `pywin32`가 없으면 import 단계에서 실패할 수 있습니다.

장기적으로는 CANoe가 생성하는 Python type library 또는 설치된 Vector Python API 방식으로 `SystemVariables.read()` / `SystemVariables.write()` 내부만 교체하는 것이 좋습니다. 테스트 케이스의 나머지 구조는 그대로 유지할 수 있습니다.

