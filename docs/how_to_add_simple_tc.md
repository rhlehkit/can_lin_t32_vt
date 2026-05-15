# 간단 TC 추가 방법

이 문서는 `canoe_test_unit/bus_framework/simple_user_tc.py`를 기준으로 CANoe/vTESTstudio Python TC를 추가하는 방법입니다.

## 1. 기본 구조

TC 하나는 보통 아래 모양입니다.

```python
@vector.canoe.tfs.export
@vector.canoe.tfs.test_case
def TC_MY_CAN_Test():
    tx_frame = frame_from_config(CONFIG["can"]["tx_once"])
    bridge().send_can(1, tx_frame)
```

필수 요소는 두 가지입니다.

- `@vector.canoe.tfs.export`
- `@vector.canoe.tfs.test_case`

이 두 decorator가 있어야 Vector Test Unit이 Python 함수를 테스트 케이스로 인식합니다.

## 2. 예제 TC 위치

예제 파일:

```text
canoe_test_unit/bus_framework/simple_user_tc.py
```

포함된 TC:

- `TC_EXAMPLE_CAN_SendAndExpectResponse`
- `TC_EXAMPLE_LIN_RequestAndExpectResponse`
- `TC_EXAMPLE_CAN_PeriodicWhileCheckingResponse`

## 3. 값 수정

먼저 `bus_test_config.py`에서 ID, data, channel을 바꿉니다.

CAN 송신/수신 예:

```python
"can": {
    "channel": 1,
    "tx_once": {
        "id": "0x123",
        "extended": False,
        "data": ["0x10", "0x22", "0x33", "0x44"],
    },
    "rx_expected": {
        "id": "0x321",
        "extended": False,
        "data": ["0x01", "0x02", "0x03", "0x04"],
        "check_data": True,
        "timeout_ms": 1000,
    },
}
```

LIN 수신 예:

```python
"lin": {
    "channel": 1,
    "rx_expected": {
        "id": "0x22",
        "data": ["0x55", "0xAA", "0x12", "0x34"],
        "request_header_before_wait": True,
        "check_data": True,
        "timeout_ms": 1000,
    },
}
```

## 4. Test Tree에 등록

`simple_user_tc.py`에 새 함수를 추가했다면 `bus_framework.vtesttree.yaml`에도 등록합니다.

```yaml
test-tree:
  - group: Simple Examples
    elements:
      - python-test-case: TC_MY_CAN_Test
        title: My CAN Test
```

`bus_framework.vtestunit.yaml`에는 `simple_user_tc.py`가 이미 포함되어 있습니다.

## 5. 적용 순서

1. `bus_test_config.py`에서 메시지 ID/data/channel 수정
2. `bus_bridge_contract.can`에서 필요한 CAPL bridge 함수 구현
3. `simple_user_tc.py`에 새 TC 작성 또는 기존 예제 TC 사용
4. `bus_framework.vtesttree.yaml`에 TC 등록
5. CANoe/vTESTstudio에서 `bus_framework.vtestunit.yaml` 추가
6. Test Unit build
7. CANoe measurement start
8. TC 실행

## 6. 제일 단순한 CAN TC

```python
@vector.canoe.tfs.export
@vector.canoe.tfs.test_case
def TC_MY_CAN_TxOnly():
    frame = frame_from_config(CONFIG["can"]["tx_once"])
    bridge().send_can(config_int(CONFIG["can"], "channel", 1), frame)
    step("CAN TX", frame.format())
```

## 7. 제일 단순한 LIN TC

```python
@vector.canoe.tfs.export
@vector.canoe.tfs.test_case
def TC_MY_LIN_RxOnly():
    channel = config_int(CONFIG["lin"], "channel", 1)
    expected = frame_from_config(CONFIG["lin"]["rx_expected"])
    bridge().request_lin_header(channel, expected.frame_id)
    actual = bridge().wait_lin(channel, expected, 1000, check_data=True)
    step("LIN RX", actual.format())
```

## 8. 주기 송신을 켜 둔 상태에서 테스트

```python
@vector.canoe.tfs.export
@vector.canoe.tfs.test_case
def TC_MY_CAN_Periodic_With_Check():
    channel = config_int(CONFIG["can"], "channel", 1)
    periodic = CONFIG["can"]["periodic_tx"]
    task_id = config_int(periodic, "task_id")
    frame = frame_from_config(periodic)

    bridge().start_can_periodic(task_id, channel, frame, config_int(periodic, "period_ms"))
    try:
        expected = frame_from_config(CONFIG["can"]["rx_expected"])
        bridge().wait_can(channel, expected, 1000, check_data=True)
    finally:
        bridge().stop_periodic(task_id)
```

`finally`를 쓰면 중간에 RX 확인이 실패해도 주기 송신을 멈출 수 있어서 안전합니다.

