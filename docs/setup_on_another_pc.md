# 다른 PC에서 CANoe/vTESTstudio Bus Test Framework 적용하기

이 문서는 `canoe_test_unit/bus_framework`를 다른 로컬 PC의 CANoe/vTESTstudio 환경에 적용하는 절차입니다.

## 1. 준비물

대상 PC에 아래 항목이 필요합니다.

- Vector CANoe 또는 vTESTstudio
- 사용할 Vector hardware driver
- CAN/LIN channel이 설정된 CANoe configuration
- CAN DBC, LIN LDF
- VS Code
- Vector Test Unit VS Code extension
- Python extension for VS Code
- pywin32 또는 Vector-generated Python type library 사용 환경
- TRACE32 연동을 쓸 경우 TRACE32 PowerView와 `lauterbach-trace32-rcl` Python package

## 2. 파일 복사

이 저장소에서 아래 폴더를 대상 PC의 CANoe/vTESTstudio 프로젝트 근처로 복사합니다.

```text
canoe_test_unit/bus_framework/
```

권장 위치 예시:

```text
MyCanoeProject/
  Config/
  Database/
  TestUnits/
    bus_framework/
```

## 3. CANoe configuration 먼저 확인

Test Unit을 붙이기 전에 CANoe에서 먼저 확인합니다.

1. CAN channel이 VN/VX hardware에 매핑되어 있는지 확인합니다.
2. LIN channel이 VN16xx 또는 사용 hardware에 매핑되어 있는지 확인합니다.
3. DBC/LDF가 CANoe configuration에 연결되어 있는지 확인합니다.
4. CANoe Trace 창에서 CAN/LIN frame이 실제로 보이는지 확인합니다.
5. VT System을 쓰는 경우 VT System configuration과 stimulation/measurement path가 정상인지 확인합니다.

이 단계가 안 되면 Python Test Unit도 정상 동작하지 않습니다.

## 4. CAPL bridge 구현

`bus_bridge_contract.can`은 Python이 호출할 함수 이름과 인자 계약입니다. 처음에는 stub이라서 `9001`을 반환합니다.

프로젝트에 맞게 아래 함수들을 구현합니다.

구현 알고리즘은 `docs/capl_bridge_implementation_guide.md`를 같이 참고하세요.

CAN 쪽:

- `BusBridge_SendCan`
- `BusBridge_WaitCan`
- `BusBridge_StartCanPeriodic`
- `BusBridge_CheckCanPeriod`

LIN 쪽:

- `BusBridge_SendLin`
- `BusBridge_RequestLinHeader`
- `BusBridge_WaitLin`
- `BusBridge_StartLinPeriodic`
- `BusBridge_CheckLinPeriod`

공통:

- `BusBridge_StopPeriodic`
- `BusBridge_GetLastRx*`
- `BusBridge_GetPeriod*`

중요한 원칙은 CAPL이 bus event를 즉시 받아 내부 queue나 통계 변수에 저장하고, Python은 함수 호출로 결과만 가져가는 것입니다.

## 5. Test Unit 추가

CANoe Test Configuration에서:

1. Test Configuration 창을 엽니다.
2. Test Unit 추가를 선택합니다.
3. `bus_framework.vtestunit.yaml`을 선택합니다.
4. `Open Test Design`으로 VS Code를 엽니다.
5. Vector Test Unit extension이 active test unit으로 인식하는지 확인합니다.

vTESTstudio에서:

1. workspace에 `bus_framework.vtestunit.yaml`을 추가합니다.
2. `bus_test_cases.py`, `bus_test_lib.py`, `bus_test_config.py`, `bus_bridge_contract.can`, `bus_framework.vtesttree.yaml`이 함께 포함되는지 확인합니다.
3. Test tree에 CAN/LIN 그룹과 TC들이 보이는지 확인합니다.

## 6. 테스트 값 수정

`bus_test_config.py`를 수정합니다.

CAN 예시:

```python
"can": {
    "channel": 1,
    "tx_once": {
        "id": "0x123",
        "extended": False,
        "data": ["0x10", "0x22", "0x33", "0x44"],
    },
}
```

LIN 예시:

```python
"lin": {
    "channel": 1,
    "rx_expected": {
        "id": "0x22",
        "data": ["0x55", "0xAA", "0x12", "0x34"],
        "request_header_before_wait": True,
    },
}
```

## 7. Python 호출 방식 선택

초기 bring-up:

- `bus_test_lib.py`의 `CanoeComCaplBridge`를 그대로 사용합니다.
- 대상 Python runtime에 pywin32가 필요합니다.
- 설치 예시는 다음과 같습니다.

```powershell
py -m pip install pywin32
```

장기 운용:

- Vector Test Unit extension에서 Python type libraries를 생성합니다.
- 생성된 API로 CAPL exported function을 직접 호출하도록 `CanoeComCaplBridge` 내부를 교체합니다.
- 테스트 케이스 함수와 config 구조는 유지합니다.

## 8. 실행 순서

1. CANoe configuration compile
2. Test Unit compile 또는 build
3. CANoe measurement start
4. 먼저 `TC_CAN_TxOnce` 또는 `TC_LIN_TxOnce` 같은 단순 TC 실행
5. Trace 창에서 실제 TX 확인
6. RX TC 실행
7. 마지막으로 periodic TX / period check TC 실행

주기 송신은 두 방식이 있습니다.

- `TC_CAN_PeriodicTx` / `TC_LIN_PeriodicTx`: `duration_ms` 동안 여러 번 송신하고 자동 정지
- `TC_CAN_PeriodicTx_Start` / `TC_LIN_PeriodicTx_Start`: 주기 송신을 켜 둔 뒤 다른 TC 실행, 마지막에 Stop TC로 정지

## 9. 권장 bring-up 순서

1. CAN TX 한 개
2. CAN RX 한 개
3. CAN 주기 체크
4. CAN 주기 송신
5. LIN header request
6. LIN RX 한 개
7. LIN 주기 체크
8. LIN 주기 송신

LIN은 master/slave 역할, LDF schedule table, header 송신 주체가 맞아야 하므로 CAN보다 늦게 붙이는 편이 좋습니다.

## 10. 문제 해결

`BusBridge_GetLastError=9001`

CAPL bridge 함수가 아직 stub입니다. `bus_bridge_contract.can` 내부 TODO를 구현해야 합니다.

`pywin32 is not available`

현재 Python runtime에 pywin32가 없습니다. pywin32를 설치하거나 generated type library 방식으로 adapter를 교체합니다.

RX timeout

CANoe Trace에서 해당 ID가 실제로 들어오는지 확인합니다. 들어오는데도 timeout이면 CAPL filtering/channel/extended flag를 확인합니다.

Period check 실패

수신 frame이 일정하지 않거나 tolerance가 너무 작을 수 있습니다. Trace timestamp로 실제 min/max interval을 먼저 확인합니다.

LIN 응답 없음

LDF, schedule table, master/slave 역할, checksum type, frame ID, header 송신 주체를 확인합니다.

TRACE32 연결 실패

TRACE32 PowerView Remote API port가 열려 있는지, `trace32_config.py`의 node/port/protocol이 맞는지 확인합니다. 자세한 내용은 `docs/trace32_integration_guide.md`를 참고하세요.

TRACE32 변수 write 실패

먼저 TRACE32 PowerView에서 같은 변수에 대해 수동 `Var.Set`이 되는지 확인합니다. symbol이 로드되어 있는지, 변수가 최적화로 제거되지 않았는지, target 실행 중 write가 허용되는 메모리인지 확인하세요.
