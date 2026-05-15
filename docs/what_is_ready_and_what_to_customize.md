# 바로 쓸 수 있는 부분과 현장 맞춤이 필요한 부분

이 패키지는 CANoe/vTESTstudio 프로젝트에 바로 추가할 수 있는 **테스트 프레임워크/템플릿**입니다.

하지만 대상 PC에서 압축을 풀자마자 모든 TC가 바로 pass되는 완제품은 아닙니다. CANoe configuration, DBC/LDF, LIN schedule, TRACE32 target symbol은 프로젝트마다 다르기 때문입니다.

## 바로 쓸 수 있는 부분

아래 파일과 구조는 그대로 사용할 수 있습니다.

```text
canoe_test_unit/bus_framework/
  bus_framework.vtestunit.yaml
  bus_framework.vtesttree.yaml
  bus_test_cases.py
  simple_user_tc.py
  runtime_info_tc.py
  trace32_test_cases.py
  bus_test_lib.py
  trace32_client.py
```

제공되는 Python TC 구조:

- CAN TX/RX
- LIN TX/RX
- 주기 메시지 송신
- 주기 메시지 수신 체크
- TRACE32 변수/레지스터 읽기
- TRACE32 변수 값 변경
- Python runtime 진단

## 반드시 수정해야 하는 부분

### 1. CAN/LIN 설정

수정 파일:

```text
canoe_test_unit/bus_framework/bus_test_config.py
```

수정할 값:

- CAN channel
- LIN channel
- CAN ID
- LIN frame ID
- payload
- expected response
- expected period
- tolerance
- timeout

### 2. CAPL bridge 구현

수정 파일:

```text
canoe_test_unit/bus_framework/bus_bridge_contract.can
```

현재 이 파일은 Python이 호출할 exported function 계약을 정의한 stub입니다. 실제 CAN/LIN 송수신을 하려면 아래 함수를 프로젝트에 맞게 구현해야 합니다.

- `BusBridge_SendCan`
- `BusBridge_WaitCan`
- `BusBridge_StartCanPeriodic`
- `BusBridge_CheckCanPeriod`
- `BusBridge_SendLin`
- `BusBridge_RequestLinHeader`
- `BusBridge_WaitLin`
- `BusBridge_StartLinPeriodic`
- `BusBridge_CheckLinPeriod`
- `BusBridge_StopPeriodic`

구현하지 않은 함수는 `9001`을 반환합니다.

### 3. TRACE32 설정

수정 파일:

```text
canoe_test_unit/bus_framework/trace32_config.py
```

수정할 값:

- TRACE32 node
- TRACE32 Remote API port
- 읽을 변수 이름
- 쓸 변수 이름과 값
- assert할 변수와 기대값
- register 이름
- target halt 여부

### 4. Python runtime package 설치

TRACE32 연동을 쓰려면 CANoe/vTESTstudio가 실제로 사용하는 Python runtime에 아래 package를 설치해야 합니다.

```powershell
lauterbach-trace32-rcl~=1.1.0
```

먼저 `TC_PYTHON_RuntimeInfo`를 실행해서 실제 `python.exe` 경로를 확인하세요.

## 적용 전 체크리스트

대상 PC에서 아래 순서로 확인하면 좋습니다.

1. CANoe configuration이 정상 compile 되는가?
2. CANoe Trace에서 CAN frame이 보이는가?
3. CANoe Trace에서 LIN frame이 보이는가?
4. DBC/LDF가 연결되어 있는가?
5. VN/VX/VT System hardware mapping이 정상인가?
6. `bus_framework.vtestunit.yaml`이 Test Configuration에 추가되는가?
7. `TC_PYTHON_RuntimeInfo`가 실행되는가?
8. `BusBridge_GetLastError=9001`이 나오면 CAPL stub을 구현했는가?
9. TRACE32 PowerView Remote API port가 열려 있는가?
10. TRACE32에 symbol file이 로드되어 있는가?

## 권장 bring-up 순서

처음부터 모든 TC를 돌리지 말고 아래 순서로 붙이는 것을 권장합니다.

1. `TC_PYTHON_RuntimeInfo`
2. `TC_CAN_TxOnce`
3. `TC_CAN_RxExpect`
4. `TC_CAN_PeriodCheck`
5. `TC_CAN_PeriodicTx`
6. `TC_LIN_TxOnce`
7. `TC_LIN_RxExpect`
8. `TC_LIN_PeriodCheck`
9. `TC_TRACE32_ConnectAndSnapshot`
10. `TC_TRACE32_WriteVariables`
11. `TC_CAN_TxThenTrace32Snapshot`
12. `TC_TRACE32_WriteThenCanTx`
13. `TC_LIN_RxThenTrace32Snapshot`

## 한 줄 요약

이 패키지는 **CANoe/vTESTstudio 자동화 구조와 TC 골격은 완성되어 있지만, 실제 버스 동작과 디버깅 변수는 대상 프로젝트 정보로 채워야 하는 프레임워크**입니다.
