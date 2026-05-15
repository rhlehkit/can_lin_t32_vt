# CANoe/vTESTstudio CAN/LIN/TRACE32 Handoff Summary

이 패키지는 다른 PC의 CANoe/vTESTstudio 환경에서 CAN/LIN Test Unit과 TRACE32 변수 snapshot을 적용하기 위한 파일 모음입니다.

압축을 푼 즉시 모든 TC가 바로 pass되는 완제품은 아닙니다. CANoe configuration, DBC/LDF, LIN schedule, CAPL bridge, TRACE32 symbol/port 설정은 대상 프로젝트에 맞게 채워야 합니다. 자세한 구분은 `docs/what_is_ready_and_what_to_customize.md`를 먼저 보세요.

## 메인 폴더

```text
canoe_test_unit/bus_framework/
```

이 폴더를 우선 사용하면 됩니다.

주요 파일:

| File | 역할 |
| --- | --- |
| `bus_framework.vtestunit.yaml` | CANoe/vTESTstudio에 추가할 Test Unit 파일 |
| `bus_framework.vtesttree.yaml` | Test tree와 TC 실행 목록 |
| `bus_test_cases.py` | 공통 CAN/LIN TC |
| `simple_user_tc.py` | 사용자가 복사해서 수정하기 쉬운 간단 TC 예제 |
| `runtime_info_tc.py` | CANoe/vTESTstudio가 실제로 쓰는 Python runtime 확인 TC |
| `trace32_test_cases.py` | TRACE32 변수/레지스터 snapshot TC |
| `bus_test_config.py` | CAN/LIN channel, ID, data, period, tolerance 설정 |
| `trace32_config.py` | TRACE32 node, port, 변수, register 설정 |
| `bus_bridge_contract.can` | Python이 호출할 CAPL bridge 함수 계약 |

## 제공 TC

간단 예제:

- `TC_PYTHON_RuntimeInfo`
- `TC_EXAMPLE_CAN_SendAndExpectResponse`
- `TC_EXAMPLE_LIN_RequestAndExpectResponse`
- `TC_EXAMPLE_CAN_PeriodicWhileCheckingResponse`

CAN:

- `TC_CAN_TxOnce`
- `TC_CAN_RxExpect`
- `TC_CAN_PeriodicTx`
- `TC_CAN_PeriodicTx_Start`
- `TC_CAN_PeriodicTx_Stop`
- `TC_CAN_PeriodCheck`

LIN:

- `TC_LIN_TxOnce`
- `TC_LIN_RxExpect`
- `TC_LIN_PeriodicTx`
- `TC_LIN_PeriodicTx_Start`
- `TC_LIN_PeriodicTx_Stop`
- `TC_LIN_PeriodCheck`

TRACE32:

- `TC_TRACE32_ConnectAndSnapshot`
- `TC_TRACE32_AssertVariables`
- `TC_TRACE32_WriteVariables`
- `TC_CAN_TxThenTrace32Snapshot`
- `TC_CAN_RxThenTrace32Snapshot`
- `TC_TRACE32_WriteThenCanTx`
- `TC_LIN_RxThenTrace32Snapshot`

## 다른 PC 적용 순서

1. 대상 PC에 CANoe/vTESTstudio, Vector driver, VS Code, Vector Test Unit extension을 준비합니다.
2. `canoe_test_unit/bus_framework` 폴더를 CANoe 프로젝트 근처로 복사합니다.
3. CANoe configuration에서 CAN/LIN channel, DBC/LDF, VN/VT System 연결이 먼저 정상인지 확인합니다.
4. CANoe Test Configuration 또는 vTESTstudio workspace에 `bus_framework.vtestunit.yaml`을 추가합니다.
5. `bus_test_config.py`에서 channel, ID, data, period, tolerance를 프로젝트에 맞게 수정합니다.
6. `bus_bridge_contract.can`의 stub 함수를 실제 CANoe/CAPL 구현으로 채웁니다.
7. 먼저 `TC_PYTHON_RuntimeInfo`를 실행해서 실제 Python runtime을 확인합니다.
8. TRACE32를 쓸 경우 `trace32_config.py`를 수정하고 TRACE32 Remote API port를 엽니다.
9. 필요한 Python package를 실제 runtime에 설치합니다.
10. CANoe measurement를 시작하고 단순 TC부터 실행합니다.

## TRACE32 패키지 설치

`TC_PYTHON_RuntimeInfo`의 Test Report에서 `Python executable` 값을 확인한 뒤:

```powershell
&"C:\Path\To\Python\python.exe" -m pip install "lauterbach-trace32-rcl~=1.1.0"
```

자세한 내용은 `docs/python_runtime_package_install_guide.md`를 보세요.

## 상세 문서

| Document | 내용 |
| --- | --- |
| `docs/setup_on_another_pc.md` | 다른 PC 적용 절차 |
| `docs/how_to_add_simple_tc.md` | 간단 TC 추가 방법 |
| `docs/capl_bridge_implementation_guide.md` | CAPL bridge 구현 가이드 |
| `docs/trace32_integration_guide.md` | TRACE32 연동 가이드 |
| `docs/python_runtime_package_install_guide.md` | CANoe/vTESTstudio Python runtime package 설치 방법 |
| `docs/vt_system_python_integration.md` | VT System/Python 연동 메모 |
| `docs/what_is_ready_and_what_to_customize.md` | 바로 쓸 수 있는 부분과 현장 맞춤이 필요한 부분 |

## 주의사항

- `bus_bridge_contract.can`은 현재 계약/stub 파일입니다. 실제 송수신은 대상 CANoe 프로젝트에 맞게 CAPL 내부를 구현해야 합니다.
- CANoe가 VN/VX 하드웨어를 사용 중일 때, 별도 Python XL Driver 코드가 같은 channel을 직접 열면 충돌할 수 있습니다.
- TRACE32 snapshot에서 target halt를 켜면 CAN/LIN 주기 테스트에 영향을 줄 수 있습니다.
- TRACE32 변수 write는 ECU 상태를 바꿀 수 있으므로 테스트 전용 변수부터 확인하세요.
- 먼저 CAN TX/RX 단순 TC를 성공시킨 뒤 LIN, 주기 체크, TRACE32 snapshot 순서로 붙이는 것이 좋습니다.
